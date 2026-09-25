import re
import urllib.parse
from typing import Optional
from dataclasses import dataclass
from core.config import settings

@dataclass
class EbayProduct:
    item_id: str
    title: str
    price: str = "View on eBay"
    image_url: str = ""
    affiliate_url: str = ""

class EbayConnector:
    """
    Module xử lý thông tin sản phẩm và tạo link eBay Partner Network (EPN).
    """
    def __init__(self, campaign_id: Optional[str] = None):
        self.campaign_id = campaign_id or settings.EBAY_CAMPAIGN_ID

    def build_affiliate_url(self, direct_ebay_url: str) -> str:
        """
        Bọc link eBay gốc thành link affiliate theo định dạng EPN Rover / Campaign.
        """
        if not self.campaign_id:
            return direct_ebay_url
        
        encoded_url = urllib.parse.quote_plus(direct_ebay_url)
        # Định dạng chuẩn rover của eBay Partner Network
        epn_url = (
            f"https://rover.ebay.com/rover/1/711-53200-19255-0/1"
            f"?campid={self.campaign_id}&toolid=10001&mpre={encoded_url}"
        )
        return epn_url
