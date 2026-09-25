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
    def _ensure_schema(cursor):
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS click_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            slug TEXT,
            ip_hash TEXT,
            referer TEXT,
            user_agent TEXT,
            gsc_query TEXT,
            landing_page_url TEXT,
            entity_id TEXT,
            merchant_name TEXT,
            revenue_amount REAL DEFAULT 0.0,
            conversion_status TEXT DEFAULT 'pending',
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(link_id) REFERENCES cloaked_links(id) ON DELETE CASCADE
        )
        """)
        # Kiểm tra và thêm cột còn thiếu nếu table cũ đã tồn tại
        cursor.execute("PRAGMA table_info(click_logs)")
        existing_cols = {col["name"] for col in cursor.fetchall()}
        new_cols = [
            ("gsc_query", "TEXT"),
            ("landing_page_url", "TEXT"),
            ("entity_id", "TEXT"),
            ("merchant_name", "TEXT"),
            ("revenue_amount", "REAL DEFAULT 0.0"),
            ("conversion_status", "TEXT DEFAULT 'pending'")
        ]
        for col_name, col_type in new_cols:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE click_logs ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

    @staticmethod
    def resolve_and_record_click(
        slug: str,
        client_ip: Optional[str] = None,
        referer: Optional[str] = None,
        user_agent: Optional[str] = None,
        gsc_query: Optional[str] = None,
        landing_page_url: Optional[str] = None,
        entity_id: Optional[str] = None,
        merchant_name: Optional[str] = None
    ) -> Optional[str]:
        """Tìm URL đích, tăng biến đếm tổng click và ghi log attribution chi tiết."""
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
            LinkCloaker._ensure_schema(cursor)
            cursor.execute("""
            INSERT INTO click_logs (link_id, slug, ip_hash, referer, user_agent, gsc_query, landing_page_url, entity_id, merchant_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                link_id, 
                slug, 
                ip_hash, 
                (referer or "")[:250], 
                (user_agent or "")[:250],
                (gsc_query or "")[:250],
                (landing_page_url or referer or "")[:250],
                (entity_id or "")[:100],
                (merchant_name or "amazon")[:50]
            ))
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
        """Tổng hợp toàn bộ chỉ số Analytics lượt click và doanh thu dự kiến với nhãn MODELLED chuẩn xác."""
        conn = get_connection()
        cursor = conn.cursor()

        LinkCloaker._ensure_schema(cursor)

        # 1. Tổng lượt click và tổng số links
        cursor.execute("SELECT COUNT(*) as total_links, SUM(click_count) as total_clicks FROM cloaked_links WHERE workspace_id = ?", (workspace_id,))
        stat_row = cursor.fetchone()
        total_links = stat_row["total_links"] if stat_row else 0
        total_clicks = stat_row["total_clicks"] if (stat_row and stat_row["total_clicks"]) else 0

        # Ước tính doanh thu dự phóng (MODELLED: EPC 0.133$ = 3.8% CR * 3.5$ avg commission)
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

        # 4. 15 lượt click chi tiết mới nhất kèm attribution data
        cursor.execute("""
        SELECT c.slug, l.title, c.referer, c.user_agent, c.gsc_query, c.landing_page_url, c.entity_id, c.merchant_name, c.clicked_at 
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
            "est_commission_modelled": est_commission,
            "revenue_provenance": "MODELLED",
            "provenance_badge": "MODELLED",
            "attribution_pipeline": "GSC Query -> Landing Page -> Entity -> Cloaked Link -> Merchant -> Revenue",
            "assumptions": {
                "cr_rate": "3.8% [MODELLED]",
                "avg_commission": "$3.50 [ESTIMATED]",
                "epc": "$0.133 [MODELLED]",
                "description": "Ước tính doanh thu theo mô hình toán học (MODELLED), không phải số liệu đối soát doanh thu kế toán thực tế (REAL)."
            },
            "top_links": top_links,
            "daily_trend": daily_trend,
            "recent_clicks": recent_clicks
        }
