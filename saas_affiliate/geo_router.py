import urllib.parse
from typing import Dict, Optional

class AmazonGeoRouter:
    """
    Vũ khí Affiliate #2: Tự Động Định Tuyến Quốc Tế (Smart Amazon Geotargeting / OneLink)
    - Tự động hoán đổi Store ID / Associate Tag tương ứng với quốc gia của khách đọc bài:
      + Khách US  -> amazon.com (tag: yourstore-20)
      + Khách UK  -> amazon.co.uk (tag: yourstore-21)
      + Khách CA  -> amazon.ca (tag: yourstore-ca-20)
      + Khách DE  -> amazon.de (tag: yourstore-de-21)
      + Khách AU  -> amazon.com.au (tag: yourstore-au-22)
    - Ngăn chặn thất thoát 30% - 40% doanh thu hoa hồng từ lượng truy cập ngoài nước Mỹ!
    """
    COUNTRY_DOMAINS = {
        "US": {"domain": "amazon.com", "default_tag": "affiliate-20"},
        "UK": {"domain": "amazon.co.uk", "default_tag": "affiliate-21"},
        "CA": {"domain": "amazon.ca", "default_tag": "affiliateca-20"},
        "DE": {"domain": "amazon.de", "default_tag": "affiliatede-21"},
        "AU": {"domain": "amazon.com.au", "default_tag": "affiliateau-22"}
    }

    @classmethod
    def route_amazon_link(
        cls,
        asin: str,
        country_code: str = "US",
        custom_tags: Optional[Dict[str, str]] = None
    ) -> str:
        cc = country_code.upper()
        config = cls.COUNTRY_DOMAINS.get(cc, cls.COUNTRY_DOMAINS["US"])
        domain = config["domain"]

        # Lấy tag tùy chỉnh của workspace nếu có
        tag = (custom_tags or {}).get(cc, config["default_tag"])
        return f"https://www.{domain}/dp/{asin}?tag={tag}"

    @classmethod
    def generate_geo_redirect_js(cls, asin: str, custom_tags: Optional[Dict[str, str]] = None) -> str:
        """Sinh đoạn mã JavaScript nhỏ gắn vào trang web để tự phát hiện IP người đọc và chuyển hướng sang đúng chi nhánh Amazon."""
        return f"""
        <script>
        function routeAmazonBuy(asin) {{
            const lang = navigator.language || navigator.userLanguage;
            let targetDomain = 'amazon.com';
            let tag = 'affiliate-20';
            if (lang.includes('GB') || lang.includes('en-UK')) {{
                targetDomain = 'amazon.co.uk';
                tag = '{(custom_tags or {}).get('UK', 'affiliate-21')}';
            }} else if (lang.includes('CA') || lang.includes('en-CA')) {{
                targetDomain = 'amazon.ca';
                tag = '{(custom_tags or {}).get('CA', 'affiliateca-20')}';
            }} else if (lang.includes('DE') || lang.includes('de-DE')) {{
                targetDomain = 'amazon.de';
                tag = '{(custom_tags or {}).get('DE', 'affiliatede-21')}';
            }}
            window.open('https://www.' + targetDomain + '/dp/' + asin + '?tag=' + tag, '_blank');
        }}
        </script>
        """
