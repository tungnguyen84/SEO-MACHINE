from typing import List, Dict, Any, Optional
from core.database import get_connection
from connectors.wordpress import WordPressClient

class ConnectedSiteManager:
    """
    Module quản lý đa website WordPress (Multi-Site Manager):
    - Cho phép 1 tài khoản kết nối 5 - 10 website WordPress khác nhau
    - Khi viết bài, chỉ cần chọn dropdown site muốn đăng
    """
    @staticmethod
    def add_site(workspace_id: int, site_name: str, site_url: str, username: str, app_password: str) -> Dict[str, Any]:
        # Test connection first
        client = WordPressClient(url=site_url, username=username, password=app_password)
        test_res = client.test_connection()
        if not test_res.get("success"):
            return {"success": False, "error": f"Không thể kết nối đến website WordPress này ({test_res.get('error')})"}

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO connected_sites (workspace_id, site_name, site_url, username, app_password, status)
        VALUES (?, ?, ?, ?, ?, 'active')
        """, (workspace_id, site_name.strip(), site_url.strip(), username.strip(), app_password.strip()))
        site_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {"success": True, "site_id": site_id, "user": test_res.get("user")}

    @staticmethod
    def list_sites(workspace_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        if workspace_id:
            cursor.execute("""
            SELECT s.*, w.name as workspace_name 
            FROM connected_sites s 
            LEFT JOIN workspaces w ON s.workspace_id = w.id 
            WHERE s.workspace_id = ? 
            ORDER BY s.id DESC
            """, (workspace_id,))
        else:
            cursor.execute("""
            SELECT s.*, w.name as workspace_name 
            FROM connected_sites s 
            LEFT JOIN workspaces w ON s.workspace_id = w.id 
            ORDER BY s.id DESC
            """)
        rows = []
        for r in cursor.fetchall():
            d = dict(r)
            if "app_password" in d and d["app_password"]:
                d["app_password"] = "••••••••••••"
            rows.append(d)
        conn.close()
        return rows

    @staticmethod
    def get_site(site_id: int) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM connected_sites WHERE id = ?", (site_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def delete_site(site_id: int, workspace_id: int = 1) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM connected_sites WHERE id = ? AND workspace_id = ?", (site_id, workspace_id))
        conn.commit()
        conn.close()
        return True
