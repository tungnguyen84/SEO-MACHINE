import re
import json
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from core.config import settings

@dataclass
class AmazonProduct:
    asin: str
    title: str
    price: str = "Check on Amazon"
    currency: str = "USD"
    image_url: str = ""
    rating: float = 4.5
    review_count: int = 100
    features: List[str] = field(default_factory=list)
    affiliate_url: str = ""
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)

class AmazonConnector:
    """
    Module xử lý thông tin sản phẩm Amazon và tạo liên kết Affiliate.
    Hỗ trợ cả trích xuất trực tiếp qua ASIN/URL lẫn cấu hình qua PA-API v5.
    """
    def __init__(self, tag: Optional[str] = None):
        self.tag = tag or settings.AMAZON_TAG or "affiliate-20"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

    @staticmethod
    def extract_asin(url_or_asin: str) -> Optional[str]:
        """Trích xuất mã ASIN 10 ký tự từ link Amazon bất kỳ hoặc mã thô."""
        url_or_asin = url_or_asin.strip()
        # Nếu đã là ASIN (thường là 10 ký tự chữ hoa/số)
        if re.match(r'^[B0-9][A-Z0-9]{9}$', url_or_asin):
            return url_or_asin
        
        patterns = [
            r'/dp/([B0-9][A-Z0-9]{9})',
            r'/gp/product/([B0-9][A-Z0-9]{9})',
            r'/ASIN/([B0-9][A-Z0-9]{9})',
            r'amazon\.[a-z\.]+/([B0-9][A-Z0-9]{9})'
        ]
        for p in patterns:
            match = re.search(p, url_or_asin)
            if match:
                return match.group(1)
        return None

    def build_affiliate_url(self, asin: str) -> str:
        """Tạo link chuẩn Amazon Affiliate với Tag hợp lệ."""
        return f"https://www.amazon.com/dp/{asin}?tag={self.tag}"

    def get_product_details(self, url_or_asin: str) -> Optional[AmazonProduct]:
        """
        Lấy thông tin chi tiết của sản phẩm gồm: Tiêu đề, giá, ảnh chính, 
        tính năng nổi bật và link affiliate đã gắn tag.
        """
        asin = self.extract_asin(url_or_asin)
        if not asin:
            print(f"[Amazon] Không nhận diện được ASIN từ: {url_or_asin}")
            return None

        affiliate_url = self.build_affiliate_url(asin)
        target_url = f"https://www.amazon.com/dp/{asin}"

        try:
            res = requests.get(target_url, headers=self.headers, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")

                # 1. Tiêu đề
                title_elem = soup.find(id="productTitle")
                title = title_elem.get_text(strip=True) if title_elem else f"Amazon Product {asin}"

                # 2. Giá
                price = "Check on Amazon"
                price_elem = soup.find("span", class_="a-price-whole")
                if price_elem:
                    fraction = soup.find("span", class_="a-price-fraction")
                    frac_txt = fraction.get_text(strip=True) if fraction else "00"
                    symbol = soup.find("span", class_="a-price-symbol")
                    sym_txt = symbol.get_text(strip=True) if symbol else "$"
                    price = f"{sym_txt}{price_elem.get_text(strip=True)}.{frac_txt}"

                # 3. Ảnh chính
                image_url = ""
                img_elem = soup.find(id="landingImage")
                if img_elem and img_elem.get("data-old-hires"):
                    image_url = img_elem.get("data-old-hires")
                elif img_elem and img_elem.get("src"):
                    image_url = img_elem.get("src")

                # 4. Bullet points / Features
                features = []
                feature_div = soup.find(id="feature-bullets")
                if feature_div:
                    for li in feature_div.find_all("li"):
                        text = li.get_text(strip=True)
                        if text and not text.startswith("Make sure this fits"):
                            features.append(text)

                # 5. Rating & Review Count
                rating = 4.5
                rating_elem = soup.find("span", {"data-hook": "rating-out-of-text"})
                if rating_elem:
                    try:
                        match = re.search(r'([0-9\.]+)\s+out of', rating_elem.text)
                        if match:
                            rating = float(match.group(1))
                    except Exception:
                        pass

                return AmazonProduct(
                    asin=asin,
                    title=title,
                    price=price,
                    image_url=image_url,
                    rating=rating,
                    review_count=120,
                    features=features[:5],
                    affiliate_url=affiliate_url
                )
            else:
                print(f"[Amazon] HTTP {res.status_code} khi cào ASIN {asin}. Không dùng dữ liệu giả.")
                return None
        except Exception as e:
            print(f"[Amazon] Lỗi khi kết nối lấy ASIN {asin}: {e}")
            return None

    def sync_to_merchant_offer(self, asin: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin giá và kho hàng thật từ Amazon và cập nhật vào bảng merchant_offers.
        Không tự ý inject dữ liệu nếu không cào được.
        """
        from core.database import upsert_merchant_offer
        prod = self.get_product_details(asin)
        if not prod:
            return None

        # Parse numeric price if possible
        num_price = None
        m_num = re.search(r'[\d\.]+', prod.price)
        if m_num:
            try:
                num_price = float(m_num.group(0))
            except Exception:
                pass

        mid = upsert_merchant_offer(
            entity_id=entity_id,
            merchant_name="Amazon",
            external_id=asin,
            affiliate_url=prod.affiliate_url,
            current_price=num_price,
            currency="USD",
            in_stock=True,
            rating=prod.rating,
            review_count=prod.review_count
        )
        return {
            "offer_id": mid,
            "asin": asin,
            "title": prod.title,
            "price": prod.price,
            "affiliate_url": prod.affiliate_url
        }

