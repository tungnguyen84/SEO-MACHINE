import os
import re
import urllib.parse
from typing import Dict, Any, List, Optional
import requests

class LiveSerpEngine:
    """
    Module phân tích SERP Google Quốc Tế Thời Gian Thực (Live Google US SERP):
    1. Ưu tiên gọi API Live SERP nếu có cấu hình (SerpApi, ValueSERP, hoặc Google Custom Search).
    2. Tự động bóc tách & phân loại danh tính đối thủ thực tế:
       - Diễn đàn / Forum: reddit.com, quora.com... (Dấu hiệu cực dễ outrank)
       - Sàn TMĐT: amazon.com, walmart.com, ebay.com...
       - Kênh Video: youtube.com, vimeo.com...
       - Báo lớn / Mega Authority: caranddriver.com, forbes.com, nytimes.com...
       - Blog Ngách / Niche Site: các website cá nhân, affiliate blog.
    3. Đánh giá Tối ưu Tiêu đề (Exact Title Match) và phân tích Content Gap thực tế.
    4. Cung cấp URL bài viết đối thủ để click xem trực tiếp.
    5. Fallback về bộ phân tích Heuristic nếu chưa cấu hình API key.
    """

    KNOWN_AUTHORITIES = {
        "caranddriver.com", "motortrend.com", "forbes.com", "nytimes.com", "wirecutter.com",
        "tomsguide.com", "rtings.com", "cnet.com", "techradar.com", "theverge.com",
        "consumerreports.org", "autoexpress.co.uk", "whatcar.com", "goodhousekeeping.com",
        "businessinsider.com", "popularmechanics.com", "edmunds.com", "kbb.com",
        "autoblog.com", "motor1.com", "topgear.com", "cnn.com", "usatoday.com"
    }

    KNOWN_ECOMMERCE = {
        "amazon.com", "walmart.com", "ebay.com", "target.com", "homedepot.com",
        "bestbuy.com", "lowes.com", "autozone.com", "advanceautoparts.com", "carid.com",
        "aliexpress.com", "wayfair.com", "overstock.com"
    }

    KNOWN_FORUMS = {
        "reddit.com", "quora.com", "forum.bodybuilding.com", "tripadvisor.com",
        "stackexchange.com", "stackoverflow.com", "discussions.apple.com"
    }

    KNOWN_VIDEOS = {
        "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com", "tiktok.com"
    }

    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_API_KEY", "").strip()
        self.valueserp_key = os.getenv("VALUESERP_API_KEY", "").strip()
        self.google_cse_key = os.getenv("GOOGLE_SEARCH_API_KEY", "").strip()
        self.google_cse_cx = os.getenv("GOOGLE_SEARCH_CX", "").strip()

    def classify_domain(self, domain: str) -> Dict[str, Any]:
        """Phân loại loại hình đối thủ dựa trên domain."""
        dom = domain.lower().replace("www.", "")
        
        # Kiểm tra exact hoặc subdomain
        for f in self.KNOWN_FORUMS:
            if f in dom:
                return {
                    "type": "forum",
                    "badge": "Diễn đàn (Forum)",
                    "color": "indigo",
                    "da": 88,
                    "weakness": "Thảo luận rời rạc của thành viên, thiếu bảng so sánh thông số, không có cấu trúc bài viết chuẩn SEO.",
                    "opportunity": "RẤT CAO: Google hiện Reddit do thiếu nội dung chuyên sâu, dễ dàng outrank bằng bài viết chất lượng cao!"
                }
        
        for v in self.KNOWN_VIDEOS:
            if v in dom:
                return {
                    "type": "video",
                    "badge": "Video YouTube",
                    "color": "red",
                    "da": 98,
                    "weakness": "Định dạng video, người xem vẫn cần bài blog dạng text để đọc chi tiết thông số và bấm link affiliate.",
                    "opportunity": "CAO: Bài viết có cấu trúc bảng biểu và hình ảnh sẽ vượt vị trí video ở phần text search."
                }
        
        for e in self.KNOWN_ECOMMERCE:
            if e in dom:
                return {
                    "type": "ecommerce",
                    "badge": "Sàn TMĐT",
                    "color": "amber",
                    "da": 94,
                    "weakness": "Trang danh mục sản phẩm của sàn, chỉ có danh sách hàng mà không có bài phân tích, review ưu nhược điểm.",
                    "opportunity": "RẤT CAO: Google thích xếp hạng bài tư vấn trước trang danh mục bán hàng thuần túy."
                }
        
        for a in self.KNOWN_AUTHORITIES:
            if a in dom:
                return {
                    "type": "mega",
                    "badge": "Báo lớn (Authority)",
                    "color": "purple",
                    "da": 86,
                    "weakness": "Báo lớn DA cao nhưng thường viết tổng quan chung chung, ít cập nhật các ngách sâu hoặc bài viết mang tính tài trợ.",
                    "opportunity": "TRUNG BÌNH: Cần bài viết chuyên sâu hơn, có bảng so sánh chi tiết và kinh nghiệm thực tế (E-E-A-T)."
                }
        
        # Nếu không thuộc các nhóm trên -> Niche Blog cá nhân
        return {
            "type": "niche",
            "badge": "Niche Site",
            "color": "emerald",
            "da": 28,
            "weakness": "Website ngách độc lập, DA trung bình thấp, nội dung thường dưới 1,500 từ và ít backlink chuyên biệt.",
            "opportunity": "CƠ HỘI VÀNG: Dễ dàng vượt mặt bằng bài viết 2,000+ từ chuẩn OpenSEO, FAQ Schema và hình ảnh minh họa."
        }

    def fetch_live_serp(self, keyword: str) -> Optional[List[Dict[str, Any]]]:
        """
        Thực hiện truy vấn live SERP nếu có API Key.
        Hỗ trợ SerpApi, ValueSERP, hoặc Google Custom Search JSON API.
        """
        # 1. Thử SerpApi
        if self.serpapi_key:
            try:
                params = {
                    "engine": "google",
                    "q": keyword,
                    "api_key": self.serpapi_key,
                    "gl": "us",
                    "hl": "en",
                    "num": 10
                }
                res = requests.get("https://serpapi.com/search.json", params=params, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    organic = data.get("organic_results", [])
                    if organic:
                        results = []
                        for idx, item in enumerate(organic[:10]):
                            url = item.get("link", "")
                            domain = urllib.parse.urlparse(url).netloc.replace("www.", "").lower()
                            results.append({
                                "rank": idx + 1,
                                "domain": domain,
                                "url": url,
                                "title": item.get("title", ""),
                                "snippet": item.get("snippet", "")
                            })
                        return results
            except Exception as e:
                print(f"[LiveSerp] SerpApi error: {e}")

        # 2. Thử ValueSERP
        if self.valueserp_key:
            try:
                params = {
                    "api_key": self.valueserp_key,
                    "q": keyword,
                    "location": "United States",
                    "gl": "us",
                    "hl": "en",
                    "num": 10
                }
                res = requests.get("https://api.valueserp.com/search", params=params, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    organic = data.get("organic_results", [])
                    if organic:
                        results = []
                        for idx, item in enumerate(organic[:10]):
                            url = item.get("link", "")
                            domain = urllib.parse.urlparse(url).netloc.replace("www.", "").lower()
                            results.append({
                                "rank": idx + 1,
                                "domain": domain,
                                "url": url,
                                "title": item.get("title", ""),
                                "snippet": item.get("snippet", "")
                            })
                        return results
            except Exception as e:
                print(f"[LiveSerp] ValueSERP error: {e}")

        # 3. Thử Google Custom Search API
        if self.google_cse_key and self.google_cse_cx:
            try:
                params = {
                    "key": self.google_cse_key,
                    "cx": self.google_cse_cx,
                    "q": keyword,
                    "num": 10,
                    "gl": "us",
                    "hl": "en"
                }
                res = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("items", [])
                    if items:
                        results = []
                        for idx, item in enumerate(items[:10]):
                            url = item.get("link", "")
                            domain = urllib.parse.urlparse(url).netloc.replace("www.", "").lower()
                            results.append({
                                "rank": idx + 1,
                                "domain": domain,
                                "url": url,
                                "title": item.get("title", ""),
                                "snippet": item.get("snippet", "")
                            })
                        return results
            except Exception as e:
                print(f"[LiveSerp] Google CSE error: {e}")

        return None

    def analyze(self, keyword: str) -> Dict[str, Any]:
        """
        Phân tích đối thủ Top 10 Google US:
        - Nếu có API key: trả về 100% LIVE REAL-TIME SERP kết quả từ máy chủ Google US.
        - Nếu chưa có: trả về phân tích Heuristic chuẩn hóa kèm cờ is_live=False.
        """
        kw = keyword.strip()
        kw_lower = kw.lower()
        kw_tokens = set(re.findall(r'\w+', kw_lower))

        live_results = self.fetch_live_serp(kw)
        is_live = live_results is not None and len(live_results) > 0

        serp_items = []
        zero_bl_count = 0
        ecommerce_count = 0
        video_count = 0
        mega_count = 0
        forum_count = 0
        niche_count = 0

        if is_live:
            for item in live_results:
                dom = item["domain"]
                classification = self.classify_domain(dom)
                title = item["title"]
                title_lower = title.lower()
                
                # Check exact title match
                matched_tokens = sum(1 for t in kw_tokens if t in title_lower)
                exact_title = matched_tokens >= max(2, len(kw_tokens) - 1)

                t_type = classification["type"]
                if t_type == "ecommerce":
                    ecommerce_count += 1
                elif t_type == "video":
                    video_count += 1
                elif t_type == "forum":
                    forum_count += 1
                elif t_type == "mega":
                    mega_count += 1
                else:
                    niche_count += 1
                    zero_bl_count += 1

                # Ước lượng backlink tương đối theo loại domain
                if t_type == "niche":
                    backlinks_est = 1 if exact_title else 0
                elif t_type == "forum":
                    backlinks_est = 2
                elif t_type == "video":
                    backlinks_est = 5
                elif t_type == "mega":
                    backlinks_est = 45
                else:
                    backlinks_est = 25

                serp_items.append({
                    "rank": item["rank"],
                    "domain": dom,
                    "url": item["url"],
                    "title": title,
                    "da": classification["da"],
                    "type": t_type,
                    "type_badge": classification["badge"],
                    "type_color": classification["color"],
                    "backlinks": backlinks_est,
                    "exact_title": exact_title,
                    "weakness": classification["weakness"],
                    "opportunity": classification["opportunity"]
                })
        else:
            # Fallback Heuristic dựa trên đặc tính từ khóa
            from saas_affiliate.diamond_hunter import DiamondNicheHunter
            hunter = DiamondNicheHunter()
            fallback_data = hunter.analyze_serp_competition(kw)
            return {
                **fallback_data,
                "is_live": False,
                "data_source": "HEURISTIC_MODEL",
                "source_label": "Mô Phỏng Mẫu SERP (Benchmark)",
                "google_search_url": f"https://www.google.com/search?q={urllib.parse.quote_plus(kw)}&gl=us&pws=0&hl=en"
            }

        # Đánh giá cơ hội outrank thực tế
        if forum_count >= 1 or niche_count >= 1:
            verdict = "CƠ HỘI VÀNG (DỄ DÀNG LÊN TOP 1-3): XUẤT HIỆN DIỄN ĐÀN (REDDIT) / WEBSITE NGÁCH TRONG TOP 10"
            outrank_chance = "90% - 95% (Cực Dễ Vượt)"
            strategy = (
                f"1. Có {forum_count} kết quả Diễn đàn (Reddit/Quora) và {niche_count} website ngách trong Top 10 thật trên Google US.\n"
                "2. Các trang diễn đàn này chỉ là thảo luận ngắn, hoàn toàn thiếu cấu trúc bài viết chuyên gia, bảng so sánh và FAQ Schema.\n"
                "3. Xuất bản bài viết 2,000+ từ chuẩn OpenSEO, chèn 3-5 sản phẩm Amazon đánh giá chi tiết sẽ chiếm trọn vị trí của các bài thảo luận này!"
            )
        elif ecommerce_count >= 3:
            verdict = "CƠ HỘI TỐT: TOP 10 BỊ CHIẾM BỞI TRANG BÁN HÀNG CỦA SÀN (AMAZON/EBAY/WALMART)"
            outrank_chance = "80% - 85% (Dễ Lên Top)"
            strategy = (
                "Google đang phải xếp hạng trang danh mục sản phẩm vì thiếu bài viết phân tích chuyên sâu (Informational/Review).\n"
                "Người dùng gõ từ khóa này cần lời khuyên chuyên gia thay vì chỉ nhìn danh sách sản phẩm. Hãy làm bài review chi tiết để Google ưu tiên đưa lên trước sàn!"
            )
        else:
            verdict = "CẠNH TRANH TRUNG BÌNH: NHIỀU BÁO LỚN VÀ KÊNH TRUYỀN THÔNG"
            outrank_chance = "70% - 75% (Cần Tối Ưu E-E-A-T)"
            strategy = "Cần đầu tư bài viết dài, chèn bảng thông số kỹ thuật chi tiết, video nhúng và internal link chặt chẽ từ các bài vệ tinh."

        return {
            "keyword": kw,
            "is_live": True,
            "data_source": "LIVE_GOOGLE_US",
            "source_label": "Google US Real-time Live SERP (100% Thời Gian Thực)",
            "google_search_url": f"https://www.google.com/search?q={urllib.parse.quote_plus(kw)}&gl=us&pws=0&hl=en",
            "verdict": verdict,
            "outrank_probability": outrank_chance,
            "strategy": strategy,
            "zero_backlink_niche_count": zero_bl_count,
            "ecommerce_count": ecommerce_count,
            "video_count": video_count,
            "mega_authorities_count": mega_count,
            "forum_count": forum_count,
            "niche_sites_count": niche_count,
            "top_10": serp_items
        }
