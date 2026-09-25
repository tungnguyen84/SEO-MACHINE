import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from connectors.amazon import AmazonConnector, AmazonProduct
from connectors.dataforseo import DataForSEOClient
from research.longtail import LongtailKeywordFinder

@dataclass
class KeywordOpportunity:
    keyword: str
    search_volume: str
    competition: str  # LOW, MEDIUM, HIGH
    competition_score: int # 0 - 100
    intent: str
    opportunity_score: int # 0 - 100 (Điểm cơ hội để rank nhanh và ra đơn)
    article_type: str # "Single Product Review", "Comparison (VS)", "Roundup / Best For"
    recommendation_note: str

class ProductKeywordAdvisor:
    """
    Module phân tích ngược từ link Amazon:
    1. Trích xuất thương hiệu, model và tính năng từ sản phẩm Amazon.
    2. Tự động sinh danh sách từ khóa chính + từ khóa đuôi dài (Long-tail).
    3. Ước tính / lấy chính xác Lượng tìm kiếm (Search Volume) và Độ cạnh tranh (Competition).
    4. Chấm điểm cơ hội (Opportunity Score) và đưa ra gợi ý: Nên viết bài với từ khóa nào để dễ rank nhất và ra đơn nhanh nhất!
    """
    def __init__(self):
        self.amazon = AmazonConnector()
        self.longtail = LongtailKeywordFinder()
        self.dataforseo = DataForSEOClient()
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

    def _clean_product_name(self, raw_title: str) -> Dict[str, str]:
        """Lọc bỏ các từ rác trong tên sản phẩm Amazon để lấy Model cốt lõi."""
        # Tách các từ trước dấu phẩy, gạch nối hoặc ngoặc đơn
        parts = re.split(r'[,|\-\(\)]', raw_title)
        first_segment = parts[0].strip() if parts else raw_title
        words = first_segment.split()
        
        # Lấy 2 đến 4 từ đầu tiên thường là Brand + Model
        core_name = " ".join(words[:4]) if len(words) >= 4 else first_segment
        
        # Đoán danh mục sản phẩm từ tiêu đề
        category = "product"
        cat_matches = ["chair", "desk", "headphones", "vacuum", "purifier", "monitor", "keyboard", "mouse", "camera", "pillow", "mattress", "speaker", "blender", "coffee maker"]
        for c in cat_matches:
            if c in raw_title.lower():
                category = c
                break

        return {"core_name": core_name, "category": category}

    def _estimate_google_serp_competition(self, keyword: str) -> Dict[str, Any]:
        """
        Phân tích độ cạnh tranh trên Google SERP (khi không dùng API DataForSEO):
        - Quét trang 1 Google tìm dấu hiệu cạnh tranh yếu (diễn đàn Reddit, Quora, forum, video).
        - Khi Reddit/Quora nằm ở top đầu, đó là dấu hiệu vàng cho thấy website mới RẤT DỄ LÊN TOP!
        """
        encoded_kw = urllib.parse.quote_plus(keyword)
        search_url = f"https://www.google.com/search?q={encoded_kw}&hl=en"
        
        has_forum_in_top = False
        est_volume = "500 - 2,500/tháng"
        comp_level = "MEDIUM"
        comp_score = 45

        # Đánh giá theo độ dài từ khóa
        word_count = len(keyword.split())
        if word_count >= 5:
            comp_level = "LOW"
            comp_score = 25
            est_volume = "150 - 800/tháng"
        elif word_count <= 2:
            comp_level = "HIGH"
            comp_score = 80
            est_volume = "5,000 - 25,000+/tháng"

        try:
            res = requests.get(search_url, headers=self.headers, timeout=5)
            if res.status_code == 200:
                text_lower = res.text.lower()
                # Phát hiện Reddit, Quora hoặc forum ở trang 1
                if "reddit.com" in text_lower or "quora.com" in text_lower:
                    has_forum_in_top = True
                    comp_level = "LOW (Dễ rank)"
                    comp_score = max(15, comp_score - 25)
        except Exception:
            pass

        return {
            "search_volume": est_volume,
            "competition": comp_level,
            "competition_score": comp_score,
            "has_forum": has_forum_in_top
        }

    def analyze_product_url(self, url_or_asin: str) -> Dict[str, Any]:
        """
        Phân tích toàn diện 1 URL/ASIN Amazon và đưa ra gợi ý từ khóa tối ưu.
        """
        print(f"📦 Đang cào thông tin chi tiết sản phẩm từ Amazon: {url_or_asin}...")
        product = self.amazon.get_product_details(url_or_asin)
        if not product:
            return {"success": False, "error": "Không thể lấy thông tin từ URL Amazon này."}

        parsed = self._clean_product_name(product.title)
        core_name = parsed["core_name"]
        category = parsed["category"]

        print(f"   ✓ Tên Model nhận diện: '{core_name}' (Ngách: {category})")

        # 1. Sinh danh sách từ khóa hạt nhân và từ khóa đuôi dài tiềm năng
        candidates = [
            # Dạng 1: Đánh giá trực tiếp sản phẩm (Single Product Review - Buyer Intent cực cao)
            {"kw": f"{core_name.lower()} review", "type": "Single Product Review", "intent": "High Buyer Intent"},
            {"kw": f"is {core_name.lower()} worth it", "type": "Single Product Review", "intent": "Decision Making"},
            {"kw": f"{core_name.lower()} pros and cons", "type": "Single Product Review", "intent": "Comparison"},
            
            # Dạng 2: Long-tail theo trường hợp sử dụng / đối tượng (Long-tail Use-case)
            {"kw": f"best {category} for back pain", "type": "Roundup / Best For", "intent": "Problem Solving"},
            {"kw": f"best {category} for home office", "type": "Roundup / Best For", "intent": "Commercial Intent"},
            {"kw": f"best budget {category}", "type": "Roundup / Best For", "intent": "Price Sensitive"},
            {"kw": f"best ergonomic {category} 2026", "type": "Roundup / Best For", "intent": "Trending Buyer"},
            
            # Dạng 3: So sánh đối đầu (Comparison VS)
            {"kw": f"{core_name.lower()} alternatives", "type": "Comparison (VS)", "intent": "Alternative Search"}
        ]

        # Lấy thêm từ khóa suggest thực tế từ Google & Amazon
        extra_suggests = self.longtail.find_buyer_keywords(core_name, max_results=5)
        for s in extra_suggests:
            candidates.append({
                "kw": s.keyword,
                "type": s.intent,
                "intent": "High Intent Long-tail"
            })

        print(f"\n📊 Đang phân tích Search Volume & Độ cạnh tranh cho {len(candidates)} từ khóa...")

        # 2. Lấy dữ liệu Metrics (DataForSEO hoặc SERP Heuristic)
        kw_list = [c["kw"] for c in candidates]
        metrics_from_api = {}
        if self.dataforseo.is_configured:
            print("   🔌 Đang truy xuất số liệu chính xác từ DataForSEO API...")
            metrics_from_api = self.dataforseo.get_keywords_metrics(kw_list)

        opportunities: List[KeywordOpportunity] = []

        for c in candidates:
            kw = c["kw"]
            article_type = c["type"]
            intent_label = c["intent"]

            if kw in metrics_from_api:
                api_data = metrics_from_api[kw]
                volume_str = f"{api_data['search_volume']:,}/tháng"
                comp_score = int(api_data["competition_index"])
                comp_str = api_data["competition"]
            else:
                serp_data = self._estimate_google_serp_competition(kw)
                volume_str = serp_data["search_volume"]
                comp_str = serp_data["competition"]
                comp_score = serp_data["competition_score"]

            # 3. Tính điểm cơ hội (Opportunity Score 0 - 100):
            # Điểm cao nhất khi: Cạnh tranh Thấp (dễ rank) + Intent mua hàng cao (dễ ra hoa hồng)
            intent_points = 45 if "Review" in article_type or "Decision" in intent_label else 35
            low_comp_points = max(0, 100 - comp_score) * 0.40 # Cạnh tranh càng thấp điểm càng cao
            vol_points = 15

            opp_score = int(intent_points + low_comp_points + vol_points)
            opp_score = min(98, max(40, opp_score))

            note = ""
            if opp_score >= 80:
                note = "⭐ ĐỀ XUẤT HÀNG ĐẦU: Rất dễ rank lên Top Google, người đọc đang chuẩn bị mua hàng!"
            elif opp_score >= 65:
                note = "Tiềm năng tốt, cạnh tranh trung bình, lượng traffic ổn định."
            else:
                note = "Cạnh tranh khá cao hoặc từ khóa quá rộng, cần nhiều backlink."

            opportunities.append(KeywordOpportunity(
                keyword=kw,
                search_volume=volume_str,
                competition=comp_str,
                competition_score=comp_score,
                intent=intent_label,
                opportunity_score=opp_score,
                article_type=article_type,
                recommendation_note=note
            ))

        # Sắp xếp theo Opportunity Score giảm dần
        opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)
        winner = opportunities[0]

        return {
            "success": True,
            "product": product,
            "core_name": core_name,
            "category": category,
            "opportunities": opportunities,
            "recommended_keyword": winner.keyword,
            "recommended_type": winner.article_type,
            "recommendation_reason": (
                f"Nên viết bài dạng '{winner.article_type}' cho từ khóa '{winner.keyword}'. "
                f"Lý do: Điểm cơ hội đạt {winner.opportunity_score}/100, độ cạnh tranh {winner.competition}, "
                f"lượng tìm kiếm {winner.search_volume}. Khi người dùng gõ từ khóa này, họ đã có sẵn nhu cầu "
                f"mua sản phẩm '{core_name}', tỷ lệ click vào link affiliate và chuyển đổi mua hàng trên Amazon là cao nhất!"
            )
        }
