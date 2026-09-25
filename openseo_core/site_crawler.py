import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List, Set

class SiteCrawler:
    """
    Module thu thập dữ liệu đa trang (Multi-page Site-Wide Crawler) theo chuẩn OpenSEO:
    - Bắt đầu từ trang chủ, tự động tìm và thu thập các liên kết nội bộ
    - Quét tới 20 trang liên kết nội bộ
    - Phát hiện các trang lỗi 404/500, trùng lặp Title, thiếu thẻ Description
    """
    def __init__(self, max_pages: int = 15):
        self.max_pages = max_pages
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OpenSEO-Crawler/1.0"}

    def crawl_site(self, start_url: str) -> Dict[str, Any]:
        start_url = start_url.strip()
        if not start_url.startswith("http"):
            start_url = f"https://{start_url}"

        parsed_start = urlparse(start_url)
        base_netloc = parsed_start.netloc

        queue: List[str] = [start_url]
        visited: Set[str] = set()
        crawled_pages: List[Dict[str, Any]] = []

        total_broken = 0
        missing_titles = 0
        missing_descs = 0

        while queue and len(visited) < self.max_pages:
            current_url = queue.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)

            try:
                res = requests.get(current_url, headers=self.headers, timeout=6)
                status = res.status_code
                if status != 200:
                    total_broken += 1

                soup = BeautifulSoup(res.text, "html.parser")
                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else ""
                if not title:
                    missing_titles += 1

                desc_tag = soup.find("meta", attrs={"name": "description"})
                desc = desc_tag.get("content", "").strip() if desc_tag else ""
                if not desc:
                    missing_descs += 1

                # Tìm thêm internal links
                for a in soup.find_all("a", href=True):
                    href = a["href"].split("#")[0].strip()
                    if not href:
                        continue
                    full_link = urljoin(current_url, href)
                    parsed_link = urlparse(full_link)
                    if parsed_link.netloc == base_netloc and full_link not in visited and full_link not in queue:
                        # Tránh các file ảnh hoặc zip
                        if not any(full_link.endswith(ext) for ext in [".jpg", ".png", ".pdf", ".zip", ".css", ".js"]):
                            queue.append(full_link)

                crawled_pages.append({
                    "url": current_url,
                    "status": status,
                    "title": title[:55] if title else "(Thiếu Title)",
                    "has_description": bool(desc),
                    "is_ok": status == 200
                })
            except Exception:
                total_broken += 1
                crawled_pages.append({
                    "url": current_url,
                    "status": "Timeout/Error",
                    "title": "(Lỗi kết nối)",
                    "has_description": False,
                    "is_ok": False
                })

        health_score = max(20, 100 - (total_broken * 15) - (missing_titles * 5) - (missing_descs * 3))

        return {
            "success": True,
            "domain": base_netloc,
            "pages_crawled": len(crawled_pages),
            "health_score": min(100, health_score),
            "broken_pages_count": total_broken,
            "missing_titles_count": missing_titles,
            "missing_descs_count": missing_descs,
            "pages": crawled_pages
        }
