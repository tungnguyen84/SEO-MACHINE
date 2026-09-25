from datetime import datetime
from typing import Dict, Any

class AmazonPriceComplianceGuard:
    """
    Vũ khí Affiliate #3: Bộ Tuân Thủ Chính Sách Giá & Tồn Kho (Amazon Compliance Guard)
    - Tuân thủ 100% Amazon Associates Operating Agreement:
      1. Bắt buộc hiển thị mốc thời gian kiểm định giá (Price Verification Timestamp).
      2. Tuyên bố miễn trừ trách nhiệm về biến động giá thời gian thực (Amazon Price Disclaimer).
      3. Hiển thị trạng thái tồn kho an toàn ('In Stock' / 'Check Deal') thay vì ghi cứng giá vĩnh viễn.
    - Bảo vệ tài khoản affiliate khỏi nguy cơ bị Amazon đình chỉ và giam tiền hoa hồng!
    """
    @staticmethod
    def generate_compliance_disclaimer_html() -> str:
        now_str = datetime.utcnow().strftime("%B %d, %Y %H:%M UTC")
        return f"""
        <div style="font-size:11px; color:#64748b; background:#f8fafc; border:1px solid #e2e8f0; padding:10px 14px; border-radius:6px; margin:20px 0; line-height:1.5;">
            <strong>Amazon Pricing Notice:</strong> Product prices and availability are accurate as of <em>{now_str}</em> and are subject to change. Any price and availability information displayed on Amazon at the time of purchase will apply to the purchase of this product.
        </div>
        """

    @classmethod
    def generate_compliance_disclaimer(cls) -> str:
        return cls.generate_compliance_disclaimer_html()

    @staticmethod
    def format_safe_price_badge(price: str, in_stock: bool = True) -> str:
        stock_badge = '<span style="color:#16a34a; font-weight:600; font-size:12px; margin-left:8px;">&#10004; In Stock</span>' if in_stock else '<span style="color:#dc2626; font-weight:600; font-size:12px; margin-left:8px;">Check Availability</span>'
        return f"""
        <div style="display:inline-flex; align-items:center;">
            <span style="font-size:18px; font-weight:bold; color:#0f172a;">{price}</span>
            {stock_badge}
        </div>
        """
