import time
from typing import List, Dict, Any, Optional
from core.config import settings
from connectors.amazon import AmazonConnector, AmazonProduct
from connectors.wordpress import WordPressClient
from seomachine.writer import AffiliateContentWriter
from claude_seo.schema_generator import SchemaGenerator
from claude_seo.eeat_checker import EEATAuditor

class AffiliatePipelineOrchestrator:
    """
    Bộ điều phối toàn diện (Full-Loop Orchestrator) kết hợp:
    OpenSEO (Từ khóa & Dữ liệu) -> SEOMachine (Sản xuất nội dung) -> Claude-SEO (Audit & Schema) -> WordPress (Xuất bản)
    """
    def __init__(self):
        self.amazon = AmazonConnector()
        self.writer = AffiliateContentWriter()
        self.wp = WordPressClient()

    def run_roundup_pipeline(
        self,
        keyword: str,
        product_asins_or_urls: List[str],
        category_name: str = "Buying Guides",
        publish_immediately: bool = False,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Thực hiện một chu trình hoàn chỉnh từ ASIN -> Sinh bài -> Audit -> Đăng lên WordPress.
        """
        print(f"\n=======================================================")
        print(f"🚀 [BƯỚC 1/4] Khởi động Pipeline cho từ khóa: '{keyword}'")
        print(f"=======================================================")

        # 1. Trích xuất thông tin sản phẩm và gắn link Affiliate
        print(f"📦 Đang thu thập dữ liệu {len(product_asins_or_urls)} sản phẩm từ Amazon...")
        products: List[AmazonProduct] = []
        for item in product_asins_or_urls:
            p = self.amazon.get_product_details(item)
            if p:
                products.append(p)
                print(f"   ✓ Đã xử lý: {p.title[:50]}... | Giá: {p.price}")
                time.sleep(0.5)

        if not products:
            return {"success": False, "error": "Không lấy được dữ liệu sản phẩm nào."}

        # 2. Sinh bài viết chuẩn CRO qua SEOMachine
        print(f"\n✍️ [BƯỚC 2/4] SEOMachine đang viết bài review & so sánh chuyên sâu...")
        article_data = self.writer.generate_roundup_article(keyword, products)
        print(f"   ✓ Đã tạo bài: '{article_data['title']}'")

        # 3. Kiểm định chất lượng E-E-A-T & Sinh Schema Rich Snippets qua Claude-SEO
        print(f"\n🛡️ [BƯỚC 3/4] Claude-SEO đang kiểm định E-E-A-T và sinh Schema JSON-LD...")
        audit_result = EEATAuditor.audit_content(article_data["content"])
        print(f"   📊 Điểm chất lượng E-E-A-T: {audit_result['score']}/100")
        for passed in audit_result["passed"]:
            print(f"      ✓ {passed}")
        for issue in audit_result["issues"]:
            print(f"      ⚠️ {issue}")

        # Sinh mã Schema ItemList cho sản phẩm
        schema_json_ld = SchemaGenerator.generate_item_list_schema(keyword, products)
        
        # Nhúng Schema vào cuối nội dung bài viết
        final_html_content = f"{article_data['content']}\n\n{schema_json_ld}"

        # 4. Xuất bản hoặc lưu cục bộ (Dry Run)
        if dry_run:
            from pathlib import Path
            out_dir = Path("output")
            out_dir.mkdir(exist_ok=True)
            out_file = out_dir / f"{article_data['slug']}.html"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(final_html_content)

            # Lưu vào Database SQLite
            from core.database import save_article_record
            save_article_record(
                title=article_data["title"],
                slug=article_data["slug"],
                keyword=keyword,
                asins=[p.asin for p in products],
                status="dry_run",
                eeat_score=audit_result.get("score", 0),
                file_path=str(out_file)
            )

            print(f"\n🎉 HOÀN THÀNH (DRY RUN)!")
            print(f"   💾 File HTML đã được lưu tại: {out_file.resolve()}")
            print(f"   📄 Bạn có thể mở trực tiếp file này trên trình duyệt để kiểm tra giao diện.")
            return {
                "success": True,
                "dry_run": True,
                "file_path": str(out_file),
                "audit": audit_result
            }

        print(f"\n🌐 [BƯỚC 4/4] Đang đăng bài lên WordPress...")
        cat_id = self.wp.get_or_create_category(category_name)
        
        # Thử tải ảnh sản phẩm đầu tiên làm Featured Image
        featured_media_id = None
        if products and products[0].image_url:
            print(f"   🖼️ Đang tải ảnh đại diện lên thư viện WordPress...")
            featured_media_id = self.wp.upload_media_from_url(
                products[0].image_url,
                alt_text=f"Best {keyword} in 2026",
                filename=f"best-{keyword.replace(' ', '-')}.jpg"
            )

        status = "publish" if publish_immediately else settings.WP_POST_STATUS
        wp_res = self.wp.create_post(
            title=article_data["title"],
            content=final_html_content,
            slug=article_data["slug"],
            status=status,
            categories=[cat_id] if cat_id else None,
            featured_media_id=featured_media_id,
            seo_meta={
                "meta_desc": article_data["meta_desc"],
                "focus_kw": article_data["focus_kw"]
            }
        )

        if wp_res.get("success"):
            print(f"\n🎉 HOÀN THÀNH XUẤT BẢN THÀNH CÔNG!")
            print(f"   🔗 Link bài viết: {wp_res.get('link')}")
            print(f"   📌 Trạng thái: {wp_res.get('status')}")
            print(f"   🆔 Post ID: {wp_res.get('post_id')}")

            # Lưu vào Database SQLite
            from core.database import save_article_record
            save_article_record(
                title=article_data["title"],
                slug=article_data["slug"],
                keyword=keyword,
                asins=[p.asin for p in products],
                status=wp_res.get("status", "draft"),
                wp_post_id=wp_res.get("post_id"),
                wp_link=wp_res.get("link"),
                eeat_score=audit_result.get("score", 0)
            )
        else:
            print(f"\n⚠️ Kết quả WordPress: {wp_res}")

        return {
            "success": wp_res.get("success", False),
            "wp_result": wp_res,
            "audit": audit_result,
            "article": {
                "title": article_data["title"],
                "slug": article_data["slug"],
                "products_count": len(products)
            }
        }
