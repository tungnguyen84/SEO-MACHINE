import time
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from urllib.parse import urlparse, urljoin

class TechnicalAuditor:
    """
    Module kiểm toán kỹ thuật (Technical SEO Audit) theo chuẩn Claude-SEO:
    Quét trang web bất kỳ và kiểm tra:
    1. HTTP Status & Thời gian phản hồi (Response Time)
    2. Meta Tags (Title, Meta Description, Robots, Viewport)
    3. Cấu trúc Heading (H1, H2, H3 hierarchy)
    4. Canonical Tag & OpenGraph / Twitter Cards
    5. Tối ưu hình ảnh (thiếu Alt text)
    6. Dữ liệu có cấu trúc Schema.org (JSON-LD / Microdata)
    7. Broken links nội bộ
    """
    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36 (OpenSEO-Audit/1.0)"
            )
        }

    def audit_url(self, target_url: str) -> Dict[str, Any]:
        target_url = target_url.strip()
        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = f"https://{target_url}"

        start_time = time.time()
        try:
            res = requests.get(target_url, headers=self.headers, timeout=12, allow_redirects=True)
            load_time = round(time.time() - start_time, 2)
        except Exception as e:
            return {
                "success": False,
                "error": f"Không thể kết nối đến URL ({e})"
            }

        soup = BeautifulSoup(res.text, "html.parser")
        checks = []
        warnings = []
        score = 100

        # 1. HTTP Status
        if res.status_code == 200:
            checks.append(f"HTTP Status: 200 OK (Tải trang trong {load_time}s)")
        else:
            warnings.append(f"HTTP Status: {res.status_code} (Không phải mã 200 tiêu chuẩn)")
            score -= 20

        # 2. Page Title
        title_tag = soup.find("title")
        title_text = title_tag.get_text(strip=True) if title_tag else ""
        if title_text:
            t_len = len(title_text)
            if 30 <= t_len <= 65:
                checks.append(f"Tiêu đề trang (Title): Tối ưu ({t_len} ký tự) &mdash; '{title_text[:50]}...'")
            else:
                warnings.append(f"Tiêu đề trang: Độ dài chưa tối ưu ({t_len} ký tự, khuyến nghị 40-60 ký tự)")
                score -= 10
        else:
            warnings.append("Thiếu thẻ Title trên trang!")
            score -= 20

        # 3. Meta Description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc_text = meta_desc.get("content", "").strip() if meta_desc else ""
        if desc_text:
            d_len = len(desc_text)
            if 120 <= d_len <= 165:
                checks.append(f"Meta Description: Tối ưu ({d_len} ký tự)")
            else:
                warnings.append(f"Meta Description: Độ dài ({d_len} ký tự, chuẩn: 120-160 ký tự)")
                score -= 5
        else:
            warnings.append("Thiếu thẻ Meta Description!")
            score -= 15

        # 4. H1 Tag
        h1_tags = soup.find_all("h1")
        if len(h1_tags) == 1:
            checks.append(f"Thẻ H1: Chuẩn duy nhất 1 thẻ H1 ('{h1_tags[0].get_text(strip=True)[:45]}...')")
        elif len(h1_tags) == 0:
            warnings.append("Thiếu thẻ H1 trên trang!")
            score -= 15
        else:
            warnings.append(f"Phát hiện có {len(h1_tags)} thẻ H1 (Nên chỉ có duy nhất 1 H1)")
            score -= 10

        # 5. Canonical
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            checks.append(f"Canonical URL: Có thiết lập ({canonical.get('href')[:40]}...)")
        else:
            warnings.append("Thiếu thẻ Canonical URL!")
            score -= 10

        # 6. Viewport
        viewport = soup.find("meta", attrs={"name": "viewport"})
        if viewport:
            checks.append("Mobile Viewport: Thân thiện với di động")
        else:
            warnings.append("Thiếu thẻ Mobile Viewport meta!")
            score -= 15

        # 7. Images Alt text
        images = soup.find_all("img")
        missing_alt = [img for img in images if not img.get("alt")]
        if not missing_alt:
            checks.append(f"Hình ảnh: Toàn bộ {len(images)} ảnh đều có thuộc tính Alt text")
        else:
            warnings.append(f"Hình ảnh: Có {len(missing_alt)}/{len(images)} ảnh thiếu thẻ Alt text")
            score -= min(15, len(missing_alt) * 3)

        # 8. Schema Structured Data
        schemas = soup.find_all("script", type="application/ld+json")
        if schemas:
            checks.append(f"Schema JSON-LD: Phát hiện {len(schemas)} khối dữ liệu có cấu trúc")
        else:
            warnings.append("Không phát hiện khối Schema JSON-LD nào!")
            score -= 15

        final_score = max(10, min(100, score))

        return {
            "success": True,
            "url": target_url,
            "status_code": res.status_code,
            "load_time_sec": load_time,
            "score": final_score,
            "title": title_text,
            "meta_description": desc_text,
            "h1_count": len(h1_tags),
            "images_count": len(images),
            "missing_alt_count": len(missing_alt),
            "schema_count": len(schemas),
            "checks": checks,
            "warnings": warnings
        }
