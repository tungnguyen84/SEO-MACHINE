import uuid
import json
import threading
import time
from typing import Dict, Any, Optional, Callable
from core.database import get_connection

class BackgroundJobManager:
    """
    Module hàng đợi xử lý tác vụ nền (Asynchronous Background Job Worker):
    - Nhận lệnh sinh bài viết hoặc cào dữ liệu, cấp ngay Job ID trong 0.1s
    - Chạy tác vụ ngầm trong luồng độc lập, người dùng có thể tắt trình duyệt
    - Cập nhật tiến trình thời gian thực: queued -> running (10% - 90%) -> completed / failed
    """
    @staticmethod
    def create_job(workspace_id: int, task_type: str) -> str:
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO jobs (id, workspace_id, task_type, status, progress)
        VALUES (?, ?, ?, 'queued', 0)
        """, (job_id, workspace_id, task_type))
        conn.commit()
        conn.close()
        return job_id

    @staticmethod
    def update_job_progress(job_id: str, progress: int, status: str = "running", result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        conn = get_connection()
        cursor = conn.cursor()
        res_json = json.dumps(result) if result else None
        cursor.execute("""
        UPDATE jobs
        SET progress = ?, status = ?, result_json = COALESCE(?, result_json), error_msg = ?,
            completed_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END
        WHERE id = ?
        """, (progress, status, res_json, error, status, job_id))
        conn.commit()
        conn.close()

    @staticmethod
    def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        data = dict(row)
        if data.get("result_json"):
            data["result"] = json.loads(data["result_json"])
        return data

    @staticmethod
    def list_jobs(workspace_id: int = 1, limit: int = 15) -> list[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE workspace_id = ? ORDER BY created_at DESC LIMIT ?", (workspace_id, limit))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @classmethod
    def dispatch_job(cls, job_id: str, task_fn: Callable, *args, **kwargs):
        """Khởi động luồng chạy ngầm không chặn HTTP request."""
        def runner():
            try:
                cls.update_job_progress(job_id, progress=15, status="running")
                result = task_fn(job_id, *args, **kwargs)
                cls.update_job_progress(job_id, progress=100, status="completed", result=result)
            except Exception as e:
                cls.update_job_progress(job_id, progress=100, status="failed", error=str(e))

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
