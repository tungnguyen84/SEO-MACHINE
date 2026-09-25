import os
import json
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

class SearchEngineFastIndexer:
    """
    Module Đẩy Tốc Độ Index Bài Viết Siêu Tốc (Fast Indexing Engine)
    - Tích hợp giao thức IndexNow (Bing, Yandex, Seznam, Naver) để ép Bot vào cào bài viết trong vòng vài giờ.
    - Tích hợp Google Sitemap & Indexing Ping API.
    - Theo dõi trạng thái đã ping hay chưa.
    """
    INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"

    @classmethod
    def ping_indexnow(cls, url: str, key: str = "openseo2026fastindexkey") -> Dict[str, Any]:
        """Gửi URL đến giao thức IndexNow của Bing / Yandex."""
        try:
            parsed = urlparse(url)
            host = parsed.netloc
            if not host:
                return {"success": False, "error": "Invalid URL format"}

            payload = {
                "host": host,
                "key": key,
                "keyLocation": f"https://{host}/{key}.txt",
                "urlList": [url]
            }

            res = requests.post(
                cls.INDEXNOW_ENDPOINT,
                headers={"Content-Type": "application/json; charset=utf-8"},
                json=payload,
                timeout=10
            )

            # 200 hoặc 202 là thành công
            if res.status_code in [200, 202]:
                return {
                    "success": True,
                    "service": "IndexNow (Bing/Yandex)",
                    "status_code": res.status_code,
                    "message": "Đã gửi thành công URL lên hệ thống IndexNow!"
                }
            else:
                return {
                    "success": False,
                    "service": "IndexNow",
                    "status_code": res.status_code,
                    "message": f"IndexNow phản hồi mã {res.status_code}"
                }
        except Exception as e:
            return {"success": False, "service": "IndexNow", "error": str(e)}

    @classmethod
    def ping_google_sitemap(cls, site_url: str) -> Dict[str, Any]:
        """Ping Google Bot cập nhật Sitemap mới nhất."""
        try:
            clean_url = site_url.rstrip("/")
            sitemap_url = f"{clean_url}/sitemap_index.xml"
            ping_url = f"https://www.google.com/ping?sitemap={sitemap_url}"
            res = requests.get(ping_url, timeout=10)
            return {
                "success": res.status_code == 200,
                "service": "Google Ping",
                "status_code": res.status_code,
                "message": "Đã gửi thông báo ping tới Googlebot!"
            }
        except Exception as e:
            return {"success": False, "service": "Google Ping", "error": str(e)}

    @classmethod
    def ping_all(cls, article_url: str) -> Dict[str, Any]:
        """Thực hiện đẩy ping đồng thời cả IndexNow và Googlebot."""
        res_indexnow = cls.ping_indexnow(article_url)
        res_google = cls.ping_google_sitemap(article_url)

        return {
            "success": res_indexnow.get("success") or res_google.get("success"),
            "url": article_url,
            "indexnow": res_indexnow,
            "google": res_google,
            "summary": "🚀 Đã kích hoạt ép Index thành công qua IndexNow & Googlebot!"
        }
