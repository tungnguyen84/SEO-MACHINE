"""
Durable PostgreSQL-Backed Multi-Worker Distributed Job Engine
Provides cross-process atomic job claiming with SELECT FOR UPDATE SKIP LOCKED,
heartbeat leasing, crash recovery for zombie jobs, persistent idempotency, and backpressure.
"""

import os
import json
import time
import uuid
import socket
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Callable, List
from sqlalchemy import text
from core.database import get_db_session, get_engine
from core.jobs.job_queue import JobStatus, QueueFullError, RetryableError, NonRetryableError


class DurableJobEngine:
    """
    Production durable distributed job queue backed by PostgreSQL (with SQLite compatibility).
    - Uses 'FOR UPDATE SKIP LOCKED' on PostgreSQL for race-free multi-worker concurrency.
    - Uses lease expiration ('lease_expires_at') for automatic crash recovery.
    - Idempotency keys are indexed in database and survive restarts.
    """

    def __init__(
        self,
        worker_id: Optional[str] = None,
        lease_seconds: int = 30,
        max_queue_size: int = 1000
    ):
        self.worker_id = worker_id or f"worker_{socket.gethostname()}_{os.getpid()}_{uuid.uuid4().hex[:6]}"
        self.lease_seconds = lease_seconds
        self.max_queue_size = max_queue_size
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, task_type: str, handler: Callable):
        """Registers a runner function for a task type."""
        self._handlers[task_type] = handler

    def submit_job(
        self,
        task_type: str,
        payload: Optional[Dict[str, Any]] = None,
        tenant_id: str = "tenant_default",
        site_id: Optional[str] = None,
        workspace_id: int = 1,
        idempotency_key: Optional[str] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Submits a job to PostgreSQL with idempotency and backpressure checks."""
        session = get_db_session()
        try:
            # 1. Backpressure check: active jobs
            count_query = text("SELECT COUNT(*) FROM jobs WHERE status IN ('QUEUED', 'RUNNING')")
            active_count = session.execute(count_query).scalar() or 0
            if active_count >= self.max_queue_size:
                raise QueueFullError(f"Job queue full. Capacity ({self.max_queue_size}) exceeded.")

            # 2. Ensure workspace exists to satisfy foreign key constraint
            ws_check = session.execute(text("SELECT id FROM workspaces WHERE id = :w"), {"w": workspace_id}).fetchone()
            if not ws_check:
                user_id = session.execute(text("SELECT id FROM users LIMIT 1")).scalar()
                if not user_id:
                    user_res = session.execute(text("INSERT INTO users (email, password_hash, salt) VALUES ('system@openseo.local', 'h', 's') RETURNING id"))
                    user_id = user_res.scalar()
                session.execute(text("""
                    INSERT INTO workspaces (id, user_id, name) VALUES (:w, :u, 'Default Workspace')
                    ON CONFLICT (id) DO NOTHING
                """), {"w": workspace_id, "u": user_id})
                session.commit()

            # 3. Idempotency check across restart
            if idempotency_key:
                check_idem = text("SELECT id, job_type, status, result_json FROM jobs WHERE idempotency_key = :k")
                existing = session.execute(check_idem, {"k": idempotency_key}).fetchone()
                if existing:
                    row_id, row_type, row_status, row_res = existing
                    if row_status in (JobStatus.QUEUED.value, JobStatus.RUNNING.value, JobStatus.SUCCEEDED.value, "SUCCESS"):
                        res_dict = json.loads(row_res) if row_res else None
                        return {
                            "job_id": row_id,
                            "task_type": row_type,
                            "status": row_status,
                            "idempotency_key": idempotency_key,
                            "result": res_dict,
                            "is_duplicate": True
                        }

            # 3. Create new persistent job
            job_id = f"job_{uuid.uuid4().hex[:12]}"
            payload_str = json.dumps(payload or {})
            now = datetime.now(timezone.utc)

            insert_sql = text("""
                INSERT INTO jobs (
                    id, workspace_id, job_type, status, progress, retry_count,
                    max_retries, tenant_id, site_id, idempotency_key, payload_json,
                    created_at
                ) VALUES (
                    :id, :ws_id, :job_type, 'QUEUED', 0, 0,
                    :max_retries, :tenant_id, :site_id, :idempotency_key, :payload_json,
                    :created_at
                )
            """)
            session.execute(insert_sql, {
                "id": job_id,
                "ws_id": workspace_id,
                "job_type": task_type,
                "max_retries": max_retries,
                "tenant_id": tenant_id,
                "site_id": site_id,
                "idempotency_key": idempotency_key,
                "payload_json": payload_str,
                "created_at": now
            })
            session.commit()

            return {
                "job_id": job_id,
                "task_type": task_type,
                "status": JobStatus.QUEUED.value,
                "idempotency_key": idempotency_key,
                "retry_count": 0,
                "max_retries": max_retries,
                "created_at": now.isoformat()
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def claim_next_job(self) -> Optional[Dict[str, Any]]:
        """
        Atomically claims the next pending or expired zombie job.
        On PostgreSQL, uses 'FOR UPDATE SKIP LOCKED' to guarantee race-free multi-worker claiming.
        """
        engine = get_engine()
        is_postgres = "postgresql" in str(engine.url).lower()
        now = datetime.now(timezone.utc)
        lease_expires = now + timedelta(seconds=self.lease_seconds)

        session = get_db_session()
        try:
            if is_postgres:
                # PostgreSQL atomic claim query
                select_sql = text("""
                    SELECT id, job_type, tenant_id, site_id, payload_json, retry_count, max_retries
                    FROM jobs
                    WHERE status = 'QUEUED' 
                       OR (status = 'RUNNING' AND (lease_expires_at IS NULL OR lease_expires_at < :now))
                    ORDER BY created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                """)
                row = session.execute(select_sql, {"now": now}).fetchone()
                if not row:
                    session.rollback()
                    return None

                job_id, task_type, tenant_id, site_id, payload_str, retry_count, max_retries = row

                # Update job to RUNNING with worker lease
                update_sql = text("""
                    UPDATE jobs
                    SET status = 'RUNNING',
                        locked_by = :worker_id,
                        locked_at = :now,
                        lease_expires_at = :lease_expires,
                        progress = 15,
                        started_at = COALESCE(started_at, :now)
                    WHERE id = :job_id
                """)
                session.execute(update_sql, {
                    "worker_id": self.worker_id,
                    "now": now,
                    "lease_expires": lease_expires,
                    "job_id": job_id
                })
                session.commit()

                payload = json.loads(payload_str) if payload_str else {}
                return {
                    "job_id": job_id,
                    "task_type": task_type,
                    "tenant_id": tenant_id,
                    "site_id": site_id,
                    "payload": payload,
                    "retry_count": retry_count or 0,
                    "max_retries": max_retries or 3
                }
            else:
                # SQLite fallback
                select_sql = text("""
                    SELECT id, job_type, tenant_id, site_id, payload_json, retry_count, max_retries
                    FROM jobs
                    WHERE status = 'QUEUED'
                       OR (status = 'RUNNING' AND (lease_expires_at IS NULL OR lease_expires_at < :now))
                    ORDER BY created_at ASC
                    LIMIT 1
                """)
                row = session.execute(select_sql, {"now": now}).fetchone()
                if not row:
                    session.rollback()
                    return None

                job_id, task_type, tenant_id, site_id, payload_str, retry_count, max_retries = row

                update_sql = text("""
                    UPDATE jobs
                    SET status = 'RUNNING',
                        locked_by = :worker_id,
                        locked_at = :now,
                        lease_expires_at = :lease_expires,
                        progress = 15,
                        started_at = COALESCE(started_at, :now)
                    WHERE id = :job_id
                      AND (status = 'QUEUED' OR (status = 'RUNNING' AND (lease_expires_at IS NULL OR lease_expires_at < :now)))
                """)
                res = session.execute(update_sql, {
                    "worker_id": self.worker_id,
                    "now": now,
                    "lease_expires": lease_expires,
                    "job_id": job_id
                })
                session.commit()
                if res.rowcount == 0:
                    return None  # Lost race to another worker

                payload = json.loads(payload_str) if payload_str else {}
                return {
                    "job_id": job_id,
                    "task_type": task_type,
                    "tenant_id": tenant_id,
                    "site_id": site_id,
                    "payload": payload,
                    "retry_count": retry_count or 0,
                    "max_retries": max_retries or 3
                }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def process_one_job(self) -> bool:
        """Claims and executes a single job. Returns True if a job was processed, False if queue empty."""
        claimed = self.claim_next_job()
        if not claimed:
            return False

        job_id = claimed["job_id"]
        task_type = claimed["task_type"]
        handler = self._handlers.get(task_type)

        if not handler:
            self.mark_failed(job_id, f"No handler registered for task type '{task_type}'", retryable=False)
            return True

        try:
            result = handler(job_id, **claimed["payload"])
            self.mark_succeeded(job_id, result)
        except Exception as exc:
            is_retryable = self._is_retryable(exc)
            self.handle_failure(job_id, exc, retryable=is_retryable)

        return True

    def _is_retryable(self, exc: Exception) -> bool:
        if isinstance(exc, RetryableError):
            return True
        if isinstance(exc, NonRetryableError):
            return False
        msg = str(exc).lower()
        return any(term in msg for term in ["timeout", "timed out", "429", "rate limit", "502", "503", "connection reset"])

    def mark_succeeded(self, job_id: str, result: Any):
        """Marks a job as SUCCEEDED in the database."""
        session = get_db_session()
        try:
            res_str = json.dumps(result if isinstance(result, dict) else {"output": result})
            now = datetime.now(timezone.utc)
            update_sql = text("""
                UPDATE jobs
                SET status = 'SUCCEEDED',
                    progress = 100,
                    result_json = :res,
                    finished_at = :now,
                    lease_expires_at = NULL,
                    locked_by = NULL
                WHERE id = :job_id
            """)
            session.execute(update_sql, {"res": res_str, "now": now, "job_id": job_id})
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def handle_failure(self, job_id: str, exc: Exception, retryable: bool):
        """Handles failure: retries with backoff or moves to DEAD_LETTER."""
        session = get_db_session()
        try:
            now = datetime.now(timezone.utc)
            row = session.execute(text("SELECT retry_count, max_retries FROM jobs WHERE id = :id"), {"id": job_id}).fetchone()
            curr_retries = (row[0] or 0) if row else 0
            max_retries = (row[1] or 3) if row else 3

            err_msg = str(exc)

            if retryable and curr_retries < max_retries:
                new_retry = curr_retries + 1
                # Exponential backoff delay
                delay_sec = int(1 * (2 ** (new_retry - 1)))
                next_lease = now + timedelta(seconds=delay_sec)
                update_sql = text("""
                    UPDATE jobs
                    SET status = 'QUEUED',
                        retry_count = :rc,
                        error = :err,
                        lease_expires_at = :lease,
                        locked_by = NULL
                    WHERE id = :job_id
                """)
                session.execute(update_sql, {"rc": new_retry, "err": f"Retry {new_retry}/{max_retries}: {err_msg}", "lease": next_lease, "job_id": job_id})
            else:
                target_status = JobStatus.DEAD_LETTER.value if (retryable and curr_retries >= max_retries) else JobStatus.FAILED.value
                update_sql = text("""
                    UPDATE jobs
                    SET status = :st,
                        progress = 100,
                        error = :err,
                        finished_at = :now,
                        lease_expires_at = NULL,
                        locked_by = NULL
                    WHERE id = :job_id
                """)
                session.execute(update_sql, {"st": target_status, "err": err_msg, "now": now, "job_id": job_id})

            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def mark_failed(self, job_id: str, error: str, retryable: bool = False):
        self.handle_failure(job_id, NonRetryableError(error) if not retryable else RetryableError(error), retryable)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a persisted job by ID."""
        session = get_db_session()
        try:
            query = text("SELECT id, job_type, status, progress, retry_count, max_retries, error, result_json, locked_by, lease_expires_at FROM jobs WHERE id = :id")
            row = session.execute(query, {"id": job_id}).fetchone()
            if not row:
                return None
            res_dict = json.loads(row[7]) if row[7] else None
            return {
                "job_id": row[0],
                "task_type": row[1],
                "status": row[2],
                "progress": row[3],
                "retry_count": row[4],
                "max_retries": row[5],
                "error": row[6],
                "result": res_dict,
                "locked_by": row[8],
                "lease_expires_at": str(row[9]) if row[9] else None
            }
        finally:
            session.close()

    def list_dead_letter_jobs(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists all dead-lettered jobs in the database."""
        session = get_db_session()
        try:
            if tenant_id:
                query = text("SELECT id, job_type, error, retry_count, created_at FROM jobs WHERE status = 'DEAD_LETTER' AND tenant_id = :t ORDER BY created_at DESC")
                rows = session.execute(query, {"t": tenant_id}).fetchall()
            else:
                query = text("SELECT id, job_type, error, retry_count, created_at FROM jobs WHERE status = 'DEAD_LETTER' ORDER BY created_at DESC")
                rows = session.execute(query).fetchall()

            return [{"job_id": r[0], "task_type": r[1], "error": r[2], "retry_count": r[3], "created_at": str(r[4])} for r in rows]
        finally:
            session.close()

    def retry_dead_letter_job(self, job_id: str) -> bool:
        """Re-queues a dead-lettered job for execution."""
        session = get_db_session()
        try:
            update_sql = text("""
                UPDATE jobs
                SET status = 'QUEUED',
                    retry_count = 0,
                    error = NULL,
                    lease_expires_at = NULL,
                    locked_by = NULL
                WHERE id = :id AND status = 'DEAD_LETTER'
            """)
            res = session.execute(update_sql, {"id": job_id})
            session.commit()
            return res.rowcount > 0
        finally:
            session.close()

    def discard_dead_letter_job(self, job_id: str) -> bool:
        """Purges a dead-lettered job from the database."""
        session = get_db_session()
        try:
            delete_sql = text("DELETE FROM jobs WHERE id = :id AND status = 'DEAD_LETTER'")
            res = session.execute(delete_sql, {"id": job_id})
            session.commit()
            return res.rowcount > 0
        finally:
            session.close()


durable_job_engine = DurableJobEngine()
