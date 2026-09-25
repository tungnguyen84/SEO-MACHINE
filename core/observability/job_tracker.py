"""
Job Tracker & Observability Module
Priority 11 Implementation
Logs every background pipeline job with structured inputs, outputs, errors,
and status transitions: QUEUED, RUNNING, SUCCESS, FAILED, REVIEW_REQUIRED.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
import uuid
from core.database import get_connection

class JobTracker:
    """Tracks background execution jobs for full system observability."""

    @classmethod
    def create_job(
        cls,
        job_type: str,
        project_id: Optional[str] = None,
        workspace_id: int = 1,
        input_summary: Optional[str] = None
    ) -> str:
        """Initializes a new job in QUEUED status."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO jobs (
            id, workspace_id, project_id, job_type, task_type, status,
            progress, retry_count, input_summary, created_at
        ) VALUES (?, ?, ?, ?, ?, 'QUEUED', 0, 0, ?, CURRENT_TIMESTAMP)
        """, (job_id, workspace_id, project_id, job_type, job_type, input_summary))
        conn.commit()
        conn.close()
        return job_id

    @classmethod
    def start_job(cls, job_id: str) -> None:
        """Marks a job as RUNNING and logs started_at."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE jobs SET
            status = 'RUNNING',
            started_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (job_id,))
        conn.commit()
        conn.close()

    @classmethod
    def complete_job(cls, job_id: str, output_summary: str, result_data: Optional[Dict[str, Any]] = None) -> None:
        """Marks a job as SUCCESS and logs finished_at and result json."""
        conn = get_connection()
        cursor = conn.cursor()
        result_json = json.dumps(result_data or {})
        cursor.execute("""
        UPDATE jobs SET
            status = 'SUCCESS',
            progress = 100,
            output_summary = ?,
            result_json = ?,
            finished_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (output_summary, result_json, job_id))
        conn.commit()
        conn.close()

    @classmethod
    def fail_job(cls, job_id: str, error_msg: str, requires_review: bool = False) -> None:
        """Marks a job as FAILED or REVIEW_REQUIRED with error details."""
        status = "REVIEW_REQUIRED" if requires_review else "FAILED"
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE jobs SET
            status = ?,
            error_msg = ?,
            finished_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (status, error_msg, job_id))
        conn.commit()
        conn.close()

    @classmethod
    def get_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
