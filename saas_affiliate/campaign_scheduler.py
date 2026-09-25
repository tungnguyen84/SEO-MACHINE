import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.config import settings
from core.database import (
    create_campaign_plan, save_scheduled_posts, get_campaign_plan,
    update_scheduled_post_status, deduct_credit
)
from saas_core.site_manager import ConnectedSiteManager
from connectors.wordpress import WordPressClient
from connectors.amazon import AmazonConnector
from pipeline.orchestrator import AffiliatePipelineOrchestrator
from seomachine.writer import AffiliateContentWriter
from saas_affiliate.sentiment_miner import AmazonReviewSentimentMiner

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

class CampaignScheduler:
    """
    Module quản lý và thực thi Kế hoạch Xuất bản Tự động 30 Ngày (Autopilot Content Campaign):
    - Đặt lịch đăng trước (Schedule Future Posts) đồng bộ vào WordPress REST API.
    - Xử lý ngầm từng bài viết theo các thể loại (Roundup, Single Review, VS, How-To).
    - Cập nhật tiến độ % và lưu trữ bản xem trước cho toàn bộ 30 ngày.
    """
    def __init__(self):
        self.writer = AffiliateContentWriter()
        self.amz = AmazonConnector()

    def persist_plan(self, plan_data: Dict[str, Any], site_id: Optional[int] = None, workspace_id: int = 1) -> int:
        """Lưu toàn bộ bản thiết kế 30 ngày vào SQLite Database."""
        cat_name = plan_data.get("category_name", "Niche Campaign")
        cat_url = plan_data.get("original_input", "")
        summary = {
            "total_keywords_found": plan_data.get("total_keywords_found", 0),
            "top_diamonds": plan_data.get("top_diamonds", [])[:10]
        }
        
        plan_id = create_campaign_plan(
            category_name=cat_name,
            category_url=cat_url,
            total_items=len(plan_data.get("schedule", [])),
            summary=summary,
            workspace_id=workspace_id
        )

        # Lưu danh sách 30 bài
        posts_to_save = []
        for item in plan_data.get("schedule", []):
            posts_to_save.append({
                "site_id": site_id,
                "day_number": item["day_number"],
                "publish_date": item["publish_date"],
                "article_type": item["article_type"],
                "keyword": item["keyword"],
                "title": item["title"],
                "asins": item.get("asins", []),
                "status": "pending"
            })

        save_scheduled_posts(plan_id, posts_to_save, workspace_id=workspace_id)
        return plan_id

    def execute_single_post(self, post: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """Tạo nội dung và đăng/lên lịch 1 bài viết cụ thể."""
        art_type = post["article_type"]
        site_id = post.get("site_id")
        pub_date = post.get("publish_date")
        kw = post["keyword"]
        asins = post.get("asins", [])

        # Xác định client WordPress nếu có site_id
        wp_client = None
        if site_id:
            site = ConnectedSiteManager.get_site(site_id)
            if site:
                wp_client = WordPressClient(url=site["site_url"], username=site["username"], password=site["app_password"])
        if not wp_client:
            wp_client = WordPressClient()

        file_name = ""
        wp_res = {}
        status = "dry_run" if dry_run else "scheduled"

        # Tự động truy vấn các bài viết liên quan trong cùng kế hoạch để đan chéo liên kết nội bộ (Auto Internal Linking)
        plan_id = post.get("plan_id")
        roundup_links = []
        info_links = []
        if plan_id:
            try:
                from core.database import get_connection
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT title, wp_link, article_type, keyword FROM scheduled_posts WHERE plan_id = ?", (plan_id,))
                for r in cursor.fetchall():
                    item_url = r["wp_link"] or f"/{r['keyword'].replace(' ', '-')}"
                    if r["article_type"] == "roundup":
                        roundup_links.append({"title": r["title"], "url": item_url})
                    else:
                        info_links.append({"title": r["title"], "url": item_url})
                conn.close()
            except Exception:
                pass

        try:
            if art_type == "roundup":
                orchestrator = AffiliatePipelineOrchestrator()
                orchestrator.wp = wp_client
                res = orchestrator.run_roundup_pipeline(
                    keyword=kw,
                    product_asins_or_urls=asins if asins else ["B08N5WRWNW", "B07J281VDD"],
                    category_name=kw,
                    publish_immediately=False,
                    dry_run=dry_run
                )
                if dry_run and res.get("file_path"):
                    file_name = Path(res["file_path"]).name
                if not dry_run and res.get("success"):
                    # Đăng lên WP với ngày hẹn giờ
                    content_html = res.get("article", {}).get("content", "")
                    content_html = self.writer.inject_internal_links(content_html, info_links, is_how_to=False)
                    slug = res.get("article", {}).get("slug", "")
                    
                    # Tải ảnh sản phẩm đầu tiên lên WP Media Library làm Featured Image
                    feat_id = None
                    prods = res.get("products") or res.get("article", {}).get("products") or []
                    if prods and hasattr(prods[0], "image_url") and prods[0].image_url:
                        feat_id = wp_client.upload_media_from_url(prods[0].image_url, alt_text=post["title"], filename=f"feat_{slug}.jpg")
                    elif prods and isinstance(prods[0], dict) and prods[0].get("image_url"):
                        feat_id = wp_client.upload_media_from_url(prods[0]["image_url"], alt_text=post["title"], filename=f"feat_{slug}.jpg")

                    wp_res = wp_client.create_post(
                        title=post["title"],
                        content=content_html,
                        slug=slug,
                        featured_media_id=feat_id,
                        publish_date=pub_date
                    )

            elif art_type == "single":
                asin = asins[0] if asins else "B08N5WRWNW"
                prod = self.amz.get_product_details(asin)
                art = self.writer.generate_single_product_review(prod)
                art["content"] = self.writer.inject_internal_links(art["content"], roundup_links, is_how_to=True)
                file_name = f"{art['slug']}.html"
                out_path = OUTPUT_DIR / file_name
                out_path.write_text(art["content"], encoding="utf-8")
                
                if not dry_run:
                    feat_id = None
                    if prod and prod.get("image_url"):
                        feat_id = wp_client.upload_media_from_url(prod["image_url"], alt_text=art["title"], filename=f"feat_{art['slug']}.jpg")

                    wp_res = wp_client.create_post(
                        title=art["title"],
                        content=art["content"],
                        slug=art["slug"],
                        featured_media_id=feat_id,
                        publish_date=pub_date
                    )

            elif art_type == "vs":
                asin_a = asins[0] if len(asins) > 0 else "B08N5WRWNW"
                asin_b = asins[1] if len(asins) > 1 else "B07J281VDD"
                prod_a = self.amz.get_product_details(asin_a)
                prod_b = self.amz.get_product_details(asin_b)
                art = self.writer.generate_comparison_article(prod_a, prod_b)
                art["content"] = self.writer.inject_internal_links(art["content"], roundup_links, is_how_to=True)
                file_name = f"{art['slug']}.html"
                out_path = OUTPUT_DIR / file_name
                out_path.write_text(art["content"], encoding="utf-8")
                
                if not dry_run:
                    feat_id = None
                    if prod_a and prod_a.get("image_url"):
                        feat_id = wp_client.upload_media_from_url(prod_a["image_url"], alt_text=art["title"], filename=f"feat_{art['slug']}.jpg")

                    wp_res = wp_client.create_post(
                        title=art["title"],
                        content=art["content"],
                        slug=art["slug"],
                        featured_media_id=feat_id,
                        publish_date=pub_date
                    )

            elif art_type == "how_to":
                asin = asins[0] if asins else None
                prod = self.amz.get_product_details(asin) if asin else None
                art = self.writer.generate_informational_article(kw, "how_to", prod)
                art["content"] = self.writer.inject_internal_links(art["content"], roundup_links, is_how_to=True)
                file_name = f"{art['slug']}.html"
                out_path = OUTPUT_DIR / file_name
                out_path.write_text(art["content"], encoding="utf-8")
                
                if not dry_run:
                    feat_id = None
                    if prod and prod.get("image_url"):
                        feat_id = wp_client.upload_media_from_url(prod["image_url"], alt_text=art["title"], filename=f"feat_{art['slug']}.jpg")

                    wp_res = wp_client.create_post(
                        title=art["title"],
                        content=art["content"],
                        slug=art["slug"],
                        featured_media_id=feat_id,
                        publish_date=pub_date
                    )

            post_id = post.get("id")
            if post_id:
                wp_post_id = wp_res.get("post_id")
                wp_link = wp_res.get("link")
                update_scheduled_post_status(post_id, status, wp_post_id, wp_link, file_name)

            return {
                "success": True,
                "file_name": file_name,
                "status": status,
                "wp_res": wp_res
            }

        except Exception as e:
            print(f"[CampaignScheduler] Lỗi khi tạo bài '{post['title']}': {e}")
            if post.get("id"):
                update_scheduled_post_status(post["id"], "failed")
            return {"success": False, "error": str(e)}
