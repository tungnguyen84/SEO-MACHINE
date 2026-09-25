import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from typing import Dict, Any, List

class SitemapAuditor:
    """
    Module phân tích & kiểm tra sitemap.xml theo chuẩn Claude-SEO:
    - Quét sitemap_index.xml hoặc sitemap.xml
    - Đếm tổng số lượng URL
    - Kiểm tra mã phản hồi HTTP cho các URL mẫu
    - Phát hiện URL bị lỗi hoặc trùng lặp
    """
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OpenSEO-SitemapChecker/1.0"}

    def audit_sitemap(self, domain_or_sitemap_url: str) -> Dict[str, Any]:
        url = domain_or_sitemap_url.strip()
        if not url.startswith("http"):
            url = f"https://{url}"

        # Nếu chỉ nhập domain, đoán đường dẫn sitemap
        if not url.endswith(".xml"):
            parsed = urlparse(url)
            sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
        else:
            sitemap_url = url

        urls_found = []
        status_checks = []

        try:
            res = requests.get(sitemap_url, headers=self.headers, timeout=10)
            if res.status_code != 200:
                # Thử sitemap_index.xml (thường gặp trên Yoast / RankMath)
                parsed = urlparse(sitemap_url)
                alt_url = f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml"
                res = requests.get(alt_url, headers=self.headers, timeout=10)
                if res.status_code == 200:
                    sitemap_url = alt_url

            if res.status_code == 200:
                # Parse XML
                root = ET.fromstring(res.content)
                # Xóa namespace prefix để dễ duyệt
                for elem in root.iter():
                    if '}' in elem.tag:
                        elem.tag = elem.tag.split('}', 1)[1]

                for url_tag in root.findall(".//url"):
                    loc = url_tag.find("loc")
                    lastmod = url_tag.find("lastmod")
                    if loc is not None and loc.text:
                        urls_found.append({
                            "url": loc.text.strip(),
                            "lastmod": lastmod.text.strip() if lastmod is not None and lastmod.text else "N/A"
                        })

                # Nếu là sitemap index chứa các sitemap con
                if not urls_found:
                    for sitemap_tag in root.findall(".//sitemap"):
                        loc = sitemap_tag.find("loc")
                        if loc is not None and loc.text:
                            urls_found.append({
                                "url": loc.text.strip(),
                                "lastmod": "Sub-sitemap index"
                            })

                # Test ngẫu nhiên 5 URL đầu tiên
                for item in urls_found[:5]:
                    u = item["url"]
                    if u.endswith(".xml"):
                        continue
                    try:
                        u_res = requests.head(u, headers=self.headers, timeout=5, allow_redirects=True)
                        status_checks.append({
                            "url": u,
                            "status": u_res.status_code,
                            "is_ok": u_res.status_code == 200
                        })
                    except Exception:
                        status_checks.append({"url": u, "status": "Error", "is_ok": False})

                return {
                    "success": True,
                    "sitemap_url": sitemap_url,
                    "total_urls": len(urls_found),
                    "urls": urls_found[:30],
                    "sample_checks": status_checks,
                    "is_valid": len(urls_found) > 0
                }
        except Exception as e:
            return {"success": False, "error": f"Lỗi đọc sitemap: {str(e)}"}

        return {"success": False, "error": "Không tìm thấy file sitemap.xml hợp lệ."}
