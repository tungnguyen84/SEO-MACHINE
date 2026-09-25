import base64
import requests
from typing import List, Dict, Any, Optional
from core.config import settings

class DataForSEOClient:
    """
    Client kết nối DataForSEO API để lấy chính xác Lượng tìm kiếm (Search Volume),
    Độ cạnh tranh (Competition) và Giá thầu (CPC) từ Google Ads / DataForSEO Labs.
    """
    def __init__(self, login: Optional[str] = None, password: Optional[str] = None):
        self.login = login or settings.DATAFORSEO_LOGIN
        self.password = password or settings.DATAFORSEO_PASSWORD
        self.base_url = "https://api.dataforseo.com/v3"

    @property
    def is_configured(self) -> bool:
        return bool(self.login and self.password)

    def _get_headers(self) -> Dict[str, str]:
        creds = f"{self.login}:{self.password}"
        encoded = base64.b64encode(creds.encode()).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json"
        }

    def get_keywords_metrics(self, keywords: List[str], location_code: int = 2840) -> Dict[str, Dict[str, Any]]:
        """
        Lấy Search Volume & Competition cho danh sách từ khóa (mặc định location 2840 = US).
        """
        if not self.is_configured:
            return {}

        endpoint = f"{self.base_url}/keywords_data/google_ads/search_volume/live"
        payload = [{
            "keywords": keywords[:100],
            "location_code": location_code,
            "language_code": "en"
        }]

        try:
            res = requests.post(endpoint, headers=self._get_headers(), json=payload, timeout=20)
            if res.status_code == 200:
                data = res.json()
                results = {}
                tasks = data.get("tasks", [])
                if tasks and tasks[0].get("result"):
                    for item in tasks[0]["result"]:
                        kw = item.get("keyword")
                        results[kw] = {
                            "search_volume": item.get("search_volume", 0),
                            "cpc": item.get("cpc", 0.0),
                            "competition": item.get("competition", "LOW"),
                            "competition_index": item.get("competition_index", 0) # 0 - 100
                        }
                return results
        except Exception as e:
            print(f"[DataForSEO] Lỗi truy vấn metrics: {e}")
        return {}
