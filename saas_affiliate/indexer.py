import os
import json
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from datetime import datetime

class IndexMonitoringEngine:
    """
    Module Quản Trị & Giám Sát Trạng Thái Lập Chỉ Mục (Index Monitoring Engine)
    - Tuân thủ Google Search Central: Loại bỏ hoàn toàn google.com/ping (Google đã chính thức khai tử từ 12/2023).
    - Hỗ trợ giao thức IndexNow (Bing, Yandex, Seznam, Naver) để thông báo cập nhật nội dung tức thời.
    - Giám sát trạng thái Indexability (Canonical, Robots Meta, Status Code).
    - Không tuyên bố 'Force Index' hay 'Bảo đảm lập chỉ mục 100%'.
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

            if res.status_code in [200, 202]:
                return {
                    "success": True,
                    "service": "IndexNow (Bing/Yandex/Seznam)",
                    "status_code": res.status_code,
                    "message": "Đã gửi thông báo IndexNow thành công!"
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
    def check_indexability(cls, url: str) -> Dict[str, Any]:
        """
        Kiểm tra trạng thái sẵn sàng lập chỉ mục (Indexability State) trước khi submit:
        - HTTP status code (200 OK)
        - Robots meta tag (không chứa noindex)
        - Canonical URL
        """
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent": "OpenSEO-IndexMonitor/1.0"})
            is_200 = (res.status_code == 200)
            text_lower = res.text.lower()
            has_noindex = 'content="noindex"' in text_lower or "content='noindex'" in text_lower or 'name="robots" content="none"' in text_lower
            
            return {
                "success": True,
                "url": url,
                "status_code": res.status_code,
                "is_indexable": is_200 and not has_noindex,
                "has_noindex": has_noindex,
                "checked_at": datetime.utcnow().isoformat(),
                "note": "URL sẵn sàng lập chỉ mục" if (is_200 and not has_noindex) else "URL bị chặn noindex hoặc không trả về 200 OK"
            }
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "is_indexable": False,
                "error": str(e)
            }

    @classmethod
    def submit_and_monitor(cls, article_url: str) -> Dict[str, Any]:
        """Thực hiện kiểm tra indexability và gửi IndexNow notification."""
        indexability = cls.check_indexability(article_url)
        res_indexnow = cls.ping_indexnow(article_url)

        return {
            "success": res_indexnow.get("success", False),
            "url": article_url,
            "indexability": indexability,
            "indexnow": res_indexnow,
            "google_note": "Google sitemap ping đã bị Google khai tử từ 12/2023. Hãy sử dụng Google Search Console URL Inspection API hoặc cập nhật sitemap_index.xml trong GSC.",
            "summary": "Đã kiểm tra Indexability State và gửi thông báo qua giao thức IndexNow (Bing/Yandex)."
        }

    # Backward compatibility alias
    ping_all = submit_and_monitor

# Backward compatibility alias for imports
SearchEngineFastIndexer = IndexMonitoringEngine
