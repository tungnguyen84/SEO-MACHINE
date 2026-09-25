import base64
import os
import requests
from typing import Optional, Dict, Any, List
from core.config import settings
from core.database import get_connection

class WordPressClient:
    """
    Client tương tác với WordPress qua REST API tiêu chuẩn bằng Application Passwords.
    """
    def __init__(self, url: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        self.base_url = (url or settings.WP_URL).rstrip("/")
        self.api_url = f"{self.base_url}/wp-json/wp/v2"
        self.username = username or settings.WP_USERNAME
        # Application Password có thể có khoảng trắng, loại bỏ khoảng trắng khi mã hóa nếu cần
        raw_pw = password or settings.WP_APP_PASSWORD
        self.password = raw_pw.strip()
        
        credentials = f"{self.username}:{self.password}"
        encoded_creds = base64.b64encode(credentials.encode()).decode("utf-8")
        self.headers = {
            "Authorization": f"Basic {encoded_creds}",
            "User-Agent": "OpenSEO-Affiliate-Bot/1.0"
        }

    def test_connection(self) -> Dict[str, Any]:
        """Kiểm tra kết nối và thông tin người dùng quản trị."""
        try:
            res = requests.get(f"{self.api_url}/users/me", headers=self.headers, timeout=10)
            if res.status_code == 200:
                user_data = res.json()
                return {"success": True, "user": user_data.get("name"), "id": user_data.get("id")}
            return {"success": False, "status_code": res.status_code, "error": res.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_or_create_category(self, cat_name: str) -> Optional[int]:
        """Tìm hoặc tạo mới một Category."""
        if not cat_name:
            return None
        try:
            # Check existing
            res = requests.get(f"{self.api_url}/categories", headers=self.headers, params={"search": cat_name}, timeout=10)
            if res.status_code == 200:
                cats = res.json()
                for c in cats:
                    if c["name"].lower() == cat_name.lower():
                        return c["id"]
            
            # Create new
            res = requests.post(f"{self.api_url}/categories", headers=self.headers, json={"name": cat_name}, timeout=10)
            if res.status_code in [200, 201]:
                return res.json().get("id")
        except Exception as e:
            print(f"[WordPress] Lỗi get/create category: {e}")
        return None

    def upload_media_from_url(self, image_url: str, alt_text: str = "", filename: str = "featured.jpg") -> Optional[int]:
        """Tải ảnh từ URL bên ngoài và upload trực tiếp vào WP Media Library."""
        if not image_url:
            return None
        try:
            img_res = requests.get(image_url, timeout=15)
            if img_res.status_code != 200:
                return None
            
            content_type = img_res.headers.get("Content-Type", "image/jpeg")
            upload_headers = {
                **self.headers,
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
            
            res = requests.post(
                f"{self.api_url}/media",
                headers=upload_headers,
                data=img_res.content,
                timeout=20
            )
            if res.status_code in [200, 201]:
                media_id = res.json().get("id")
                # Cập nhật alt text
                if alt_text and media_id:
                    requests.post(
                        f"{self.api_url}/media/{media_id}",
                        headers=self.headers,
                        json={"alt_text": alt_text},
                        timeout=10
                    )
                return media_id
        except Exception as e:
            print(f"[WordPress] Lỗi upload media: {e}")
        return None

    def create_post(
        self,
        title: str,
        content: str,
        slug: Optional[str] = None,
        status: Optional[str] = None,
        categories: Optional[List[int]] = None,
        tags: Optional[List[int]] = None,
        featured_media_id: Optional[int] = None,
        seo_meta: Optional[Dict[str, str]] = None,
        publish_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Đăng bài viết mới lên WordPress kèm theo Schema JSON-LD và SEO metadata (Yoast / RankMath).
        Hỗ trợ đặt lịch hẹn giờ tự động đăng (Scheduled Future Post) qua REST API chuẩn WordPress.
        """
        # Safe Publish Gate: Unless AUTO_PUBLISH is explicitly True, post_status must ALWAYS be 'draft'
        if publish_date:
            post_status = "future"
        elif not settings.AUTO_PUBLISH:
            post_status = "draft"
        else:
            post_status = status or "draft"

        payload = {
            "title": title,
            "content": content,
            "status": post_status,
            "author": settings.WP_DEFAULT_AUTHOR_ID
        }
        if publish_date:
            payload["date"] = publish_date
        if slug:
            payload["slug"] = slug
        if categories:
            payload["categories"] = categories
        if tags:
            payload["tags"] = tags
        if featured_media_id:
            payload["featured_media"] = featured_media_id
            
        # Thêm SEO Meta cho Yoast hoặc RankMath nếu có
        if seo_meta:
            meta_dict = {}
            if "meta_desc" in seo_meta:
                meta_dict["_yoast_wpseo_metadesc"] = seo_meta["meta_desc"]
                meta_dict["rank_math_description"] = seo_meta["meta_desc"]
            if "focus_kw" in seo_meta:
                meta_dict["_yoast_wpseo_focuskw"] = seo_meta["focus_kw"]
                meta_dict["rank_math_focus_keyword"] = seo_meta["focus_kw"]
            payload["meta"] = meta_dict

        try:
            res = requests.post(f"{self.api_url}/posts", headers=self.headers, json=payload, timeout=20)
            if res.status_code in [200, 201]:
                data = res.json()
                return {
                    "success": True,
                    "post_id": data.get("id"),
                    "link": data.get("link"),
                    "status": data.get("status")
                }
            return {"success": False, "status_code": res.status_code, "error": res.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def save_wordpress_metadata(
        cls,
        local_article_id: int,
        wordpress_post_id: int,
        wordpress_url: str,
        page_type: str = "review",
        primary_entity_id: Optional[str] = None,
        quality_score: Optional[float] = None,
        quality_decision: Optional[str] = None
    ) -> None:
        """
        Stores synchronization and verification mapping in articles table:
        local_article_id, wordpress_post_id, wordpress_url, page_type,
        primary_entity_id, quality_score, quality_decision, last_verified_at.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE articles SET
            wp_post_id = ?,
            wp_link = ?,
            page_type = ?,
            primary_entity_id = ?,
            quality_score = ?,
            quality_decision = ?,
            last_verified_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (
            wordpress_post_id,
            wordpress_url,
            page_type,
            primary_entity_id,
            quality_score,
            quality_decision,
            local_article_id
        ))
        conn.commit()
        conn.close()

    @staticmethod
    def generate_product_schema_jsonld(
        name: str,
        brand: str,
        image_url: Optional[str] = None,
        price: Optional[float] = None,
        currency: str = "USD",
        rating: float = 4.7,
        review_count: int = 150,
        sku: Optional[str] = None
    ) -> str:
        """
        Tạo Schema.org JSON-LD cho sản phẩm chuẩn Google Rich Results.
        """
        import json
        schema = {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": name,
            "brand": {
                "@type": "Brand",
                "name": brand
            }
        }
        if image_url:
            schema["image"] = [image_url]
        if sku:
            schema["sku"] = sku
        if rating:
            schema["aggregateRating"] = {
                "@type": "AggregateRating",
                "ratingValue": str(rating),
                "reviewCount": str(review_count)
            }
        if price:
            schema["offers"] = {
                "@type": "Offer",
                "priceCurrency": currency,
                "price": str(price),
                "availability": "https://schema.org/InStock"
            }
        return f'<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>'

