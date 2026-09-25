import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from core.database import get_connection

class LinkCloaker:
    """
    Vũ khí Affiliate #4: Quản Lý Link Bọc & Đo Lường Click (Link Cloaker & Click Analytics)
    - Tạo các đường dẫn sạch, chuyên nghiệp: /go/product-name
    - Chuyển hướng 301/307 tự động có gắn kèm nofollow và sponsored
    - Đo lường chính xác số lượt click chuột theo thời gian thực (Real-time CTR Tracking)
    - Phân tích xu hướng click 7 ngày, tỷ lệ chuyển đổi ước tính & doanh thu dự phóng
    """

    @staticmethod
    def create_cloaked_link(
        workspace_id: int,
        slug: str,
        title: str,
        destination_url: str,
        target_country: str = "ALL"
    ) -> Dict[str, Any]:
        slug = re.sub(r'[^a-zA-Z0-9\-_]', '', slug.strip().lower())
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT OR REPLACE INTO cloaked_links (workspace_id, slug, title, destination_url, target_country, click_count)
            VALUES (?, ?, ?, ?, ?, 0)
            """, (workspace_id, slug, title, destination_url, target_country))
            conn.commit()
            return {
                "success": True,
                "slug": slug,
                "cloaked_url": f"/go/{slug}",
                "destination_url": destination_url,
                "title": title
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    @staticmethod
    def resolve_and_record_click(
        slug: str,
        client_ip: Optional[str] = None,
        referer: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[str]:
        """Tìm URL đích, tăng biến đếm tổng click và ghi log chi tiết vào click_logs."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, destination_url FROM cloaked_links WHERE slug = ?", (slug,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        link_id = row["id"]
        dest_url = row["destination_url"]

        # Cập nhật click tổng
        cursor.execute("UPDATE cloaked_links SET click_count = click_count + 1 WHERE id = ?", (link_id,))

        # Ghi log chi tiết (IP được hash để bảo vệ quyền riêng tư)
        ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:12] if client_ip else "unknown"
        try:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS click_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id INTEGER NOT NULL,
                slug TEXT,
                ip_hash TEXT,
                referer TEXT,
                user_agent TEXT,
                clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(link_id) REFERENCES cloaked_links(id) ON DELETE CASCADE
            )
            """)
            cursor.execute("""
            INSERT INTO click_logs (link_id, slug, ip_hash, referer, user_agent)
            VALUES (?, ?, ?, ?, ?)
            """, (link_id, slug, ip_hash, (referer or "")[:250], (user_agent or "")[:250]))
        except Exception as e:
            print(f"[LinkCloaker] Lỗi ghi click_logs: {e}")

        conn.commit()
        conn.close()
        return dest_url

    @staticmethod
    def list_links(workspace_id: int = 1) -> List[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cloaked_links WHERE workspace_id = ? ORDER BY click_count DESC", (workspace_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_analytics(workspace_id: int = 1) -> Dict[str, Any]:
        """Tổng hợp toàn bộ chỉ số Analytics lượt click và doanh thu dự kiến."""
        conn = get_connection()
        cursor = conn.cursor()

        # Đảm bảo bảng click_logs đã tồn tại
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS click_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            slug TEXT,
            ip_hash TEXT,
            referer TEXT,
            user_agent TEXT,
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 1. Tổng lượt click và tổng số links
        cursor.execute("SELECT COUNT(*) as total_links, SUM(click_count) as total_clicks FROM cloaked_links WHERE workspace_id = ?", (workspace_id,))
        stat_row = cursor.fetchone()
        total_links = stat_row["total_links"] if stat_row else 0
        total_clicks = stat_row["total_clicks"] if (stat_row and stat_row["total_clicks"]) else 0

        # Ước tính doanh thu (EPC giả định: 3.8% CR * trung bình 3.5$ hoa hồng = ~0.133$ mỗi click)
        est_commission = round(total_clicks * 0.133, 2)

        # 2. Top 5 link được click nhiều nhất
        cursor.execute("""
        SELECT slug, title, destination_url, click_count 
        FROM cloaked_links 
        WHERE workspace_id = ? 
        ORDER BY click_count DESC LIMIT 5
        """, (workspace_id,))
        top_links = [dict(r) for r in cursor.fetchall()]

        # 3. Lịch sử click 7 ngày gần nhất
        cursor.execute("""
        SELECT date(clicked_at) as click_date, COUNT(*) as count 
        FROM click_logs 
        WHERE clicked_at >= datetime('now', '-7 days')
        GROUP BY date(clicked_at) 
        ORDER BY click_date ASC
        """)
        daily_clicks_raw = {r["click_date"]: r["count"] for r in cursor.fetchall()}

        # Điền đủ 7 ngày liên tục kể cả ngày có 0 click
        daily_trend = []
        for i in range(6, -1, -1):
            day_str = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_trend.append({
                "date": day_str,
                "label": (datetime.utcnow() - timedelta(days=i)).strftime("%d/%m"),
                "clicks": daily_clicks_raw.get(day_str, 0)
            })

        # 4. 15 lượt click chi tiết mới nhất
        cursor.execute("""
        SELECT c.slug, l.title, c.referer, c.user_agent, c.clicked_at 
        FROM click_logs c
        LEFT JOIN cloaked_links l ON c.link_id = l.id
        ORDER BY c.clicked_at DESC LIMIT 15
        """)
        recent_clicks = [dict(r) for r in cursor.fetchall()]

        conn.close()

        return {
            "total_links": total_links,
            "total_clicks": total_clicks,
            "est_commission": est_commission,
            "top_links": top_links,
            "daily_trend": daily_trend,
            "recent_clicks": recent_clicks
        }
