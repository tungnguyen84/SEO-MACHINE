from typing import Dict, Any, List
from core.database import get_connection

class SaaSBillingManager:
    """
    Module Quản Lý Gói Dịch Vụ SaaS & Nâng Cấp Bản Quyền (Billing & Subscription Engine)
    - Quản lý các tầng gói: Free Starter, Pro Affiliate, Agency Enterprise.
    - Cung cấp tính năng nạp credits & nâng cấp gói trực tiếp cho người dùng.
    """

    PLANS = {
        "starter": {
            "id": "starter",
            "name": "Khởi Nghiệp (Starter)",
            "price_monthly": 0,
            "credits_monthly": 25,
            "badge_color": "bg-gray-700 text-gray-200",
            "features": [
                "25 Credits tạo bài viết AI / tháng",
                "Tối đa 1 Website WordPress kết nối",
                "Quản lý & Bọc link Affiliate cơ bản",
                "Tìm kiếm từ khóa Buyer cơ bản",
                "Hỗ trợ cộng đồng"
            ]
        },
        "pro": {
            "id": "pro",
            "name": "Chuyên Nghiệp (Pro Affiliate)",
            "price_monthly": 29,
            "credits_monthly": 150,
            "badge_color": "bg-indigo-600 text-white font-bold",
            "popular": True,
            "features": [
                "150 Credits viết bài AI + Video Short / tháng",
                "Kết nối tới 5 Website WordPress",
                "Tạo Video Ngắn 9:16 (Reels/TikTok/Shorts) tự động",
                "Đẩy Index siêu tốc IndexNow & Google Ping",
                "Soi SERP Top 10 & Phân tích Backlink / RD đối thủ",
                "Internal Link chéo tự động thông minh",
                "Hỗ trợ qua Email & Ticket ưu tiên"
            ]
        },
        "agency": {
            "id": "agency",
            "name": "Doanh Nghiệp (Agency / Enterprise)",
            "price_monthly": 79,
            "credits_monthly": 9999,
            "badge_color": "bg-amber-500 text-slate-900 font-extrabold",
            "features": [
                "Credits không giới hạn (Unlimited AI Content & Shorts)",
                "Không giới hạn số lượng Website WordPress",
                "Tự động xuất bản theo lịch 30 ngày (Autopilot Cron)",
                "Webhook tự động bắn bài lên Mạng Xã Hội đa kênh",
                "Trình theo dõi click thời gian thực & Doanh thu",
                "IP Dedicated & Tốc độ sinh AI ưu tiên cao nhất",
                "Hỗ trợ 1-1 chuyên gia SEO & Affiliate qua Telegram/Zalo"
            ]
        }
    }

    @classmethod
    def get_plans_list(cls) -> List[Dict[str, Any]]:
        return list(cls.PLANS.values())

    @classmethod
    def get_user_subscription(cls, user_id: int = 1) -> Dict[str, Any]:
        """Lấy thông tin gói hiện tại và số dư credits của người dùng."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, full_name, plan_tier, credits_remaining FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            tier = "starter"
            credits = 25
            user_data = {"email": "guest@openseo.local", "full_name": "Khách"}
        else:
            tier = row["plan_tier"] or "starter"
            credits = row["credits_remaining"] if row["credits_remaining"] is not None else 25
            user_data = dict(row)

        plan_info = cls.PLANS.get(tier, cls.PLANS["starter"])

        return {
            "user_id": user_id,
            "email": user_data.get("email"),
            "full_name": user_data.get("full_name"),
            "current_plan": tier,
            "plan_name": plan_info["name"],
            "price_monthly": plan_info["price_monthly"],
            "credits_remaining": credits,
            "plan_details": plan_info,
            "all_plans": cls.get_plans_list()
        }

    @classmethod
    def upgrade_plan(cls, user_id: int, target_plan: str) -> Dict[str, Any]:
        """Nâng cấp gói dịch vụ cho user và cộng credits tương ứng."""
        if target_plan not in cls.PLANS:
            return {"success": False, "error": f"Gói '{target_plan}' không hợp lệ"}

        plan = cls.PLANS[target_plan]
        bonus_credits = plan["credits_monthly"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE users 
        SET plan_tier = ?, 
            credits_remaining = MAX(credits_remaining, 0) + ? 
        WHERE id = ?
        """, (target_plan, bonus_credits, user_id))
        conn.commit()
        conn.close()

        return {
            "success": True,
            "new_plan": target_plan,
            "plan_name": plan["name"],
            "credits_added": bonus_credits,
            "message": f"🎉 Chúc mừng! Bạn đã kích hoạt thành công gói {plan['name']} với {bonus_credits} credits."
        }
