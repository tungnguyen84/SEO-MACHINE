"""
Production Bounded Background Job Engine & Distributed State Machine
Provides bounded thread-pool concurrency, atomic job claiming, idempotency keys,
exponential backoff with jitter for retryable failures, and Dead Letter Queue (DLQ) governance.
"""

import time
import random
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DEAD_LETTER = "DEAD_LETTER"
    CANCELLED = "CANCELLED"


class QueueFullError(Exception):
    """Raised when job queue capacity is exceeded (backpressure)."""
    pass


class DuplicateJobError(Exception):
    """Raised when an idempotent job is currently active."""
    pass


class JobExecutionError(Exception):
    """Base error for job processing."""
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class NonRetryableError(JobExecutionError):
    def __init__(self, message: str):
        super().__init__(message, retryable=False)


class RetryableError(JobExecutionError):
    def __init__(self, message: str):
        super().__init__(message, retryable=True)


class BoundedJob:
    """Represents a job managed by the bounded execution engine."""
    def __init__(
        self,
        job_id: str,
        task_type: str,
        tenant_id: str = "tenant_default",
        site_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        base_delay: float = 0.5,
    ):
        self.job_id = job_id
        self.task_type = task_type
        self.tenant_id = tenant_id
        self.site_id = site_id
        self.idempotency_key = idempotency_key
        self.payload = payload or {}
        self.max_retries = max_retries
        self.base_delay = base_delay

        self.status: JobStatus = JobStatus.QUEUED
        self.retry_count: int = 0
        self.progress: int = 0
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.error_trace: Optional[str] = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
        self.completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "task_type": self.task_type,
            "tenant_id": self.tenant_id,
            "site_id": self.site_id,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "progress": self.progress,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
        }


class ProductionJobEngine:
    """
    Central background engine with bounded concurrency, atomic claiming,
    idempotency deduplication, backpressure, and dead letter management.
    """

    def __init__(self, max_workers: int = 5, max_queue_size: int = 1000):
        self._max_workers = max_workers
        self._max_queue_size = max_queue_size
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="OpenSEO-Worker")
        self._lock = threading.Lock()

        # Job repository
        self._jobs: Dict[str, BoundedJob] = {}
        # Idempotency index: idempotency_key -> job_id
        self._idempotency_index: Dict[str, str] = {}
        # Registered task runners: task_type -> callable(job, **payload)
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, task_type: str, handler: Callable):
        """Registers a runner function for a specific task type."""
        with self._lock:
            self._handlers[task_type] = handler

    def submit_job(
        self,
        task_type: str,
        payload: Optional[Dict[str, Any]] = None,
        tenant_id: str = "tenant_default",
        site_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        max_retries: int = 3,
        base_delay: float = 0.5,
        auto_dispatch: bool = True
    ) -> BoundedJob:
        """Submits a job to the engine with idempotency and backpressure checks."""
        with self._lock:
            # Backpressure enforcement
            active_jobs = [j for j in self._jobs.values() if j.status in (JobStatus.QUEUED, JobStatus.RUNNING)]
            if len(active_jobs) >= self._max_queue_size:
                raise QueueFullError(f"Job queue full. Capacity ({self._max_queue_size}) exceeded.")

            # Idempotency check
            if idempotency_key:
                existing_job_id = self._idempotency_index.get(idempotency_key)
                if existing_job_id and existing_job_id in self._jobs:
                    existing_job = self._jobs[existing_job_id]
                    if existing_job.status in (JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.SUCCEEDED):
                        # Return existing job without re-queueing
                        return existing_job

            job_id = f"job_{uuid.uuid4().hex[:12]}"
            job = BoundedJob(
                job_id=job_id,
                task_type=task_type,
                tenant_id=tenant_id,
                site_id=site_id,
                idempotency_key=idempotency_key,
                payload=payload,
                max_retries=max_retries,
                base_delay=base_delay
            )
            self._jobs[job_id] = job
            if idempotency_key:
                self._idempotency_index[idempotency_key] = job_id

        if auto_dispatch:
            self._dispatch(job_id)

        return job

    def _dispatch(self, job_id: str):
        """Dispatches job to bounded thread pool worker."""
        self._executor.submit(self._run_job_wrapper, job_id)

    def _run_job_wrapper(self, job_id: str):
        """Thread worker wrapper that handles atomic claiming, execution, retries, and DLQ."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status not in (JobStatus.QUEUED, JobStatus.RETRYING):
                return
            # Atomic claim
            job.status = JobStatus.RUNNING
            job.progress = 10
            job.updated_at = datetime.now(timezone.utc).isoformat()
            handler = self._handlers.get(job.task_type)

        if not handler:
            self._mark_failed(job_id, f"No handler registered for task type '{job.task_type}'", retryable=False)
            return

        try:
            result = handler(job, **job.payload)
            self._mark_succeeded(job_id, result)
        except Exception as exc:
            is_retryable = self._is_exception_retryable(exc)
            self._handle_failure(job_id, exc, retryable=is_retryable)

    def _is_exception_retryable(self, exc: Exception) -> bool:
        if isinstance(exc, RetryableError):
            return True
        if isinstance(exc, NonRetryableError):
            return False
        # Catch standard transient errors (e.g. connection timeout, 429, 502, 503)
        msg = str(exc).lower()
        if any(term in msg for term in ["timeout", "timed out", "429", "rate limit", "502", "503", "connection reset"]):
            return True
        return False

    def _handle_failure(self, job_id: str, exc: Exception, retryable: bool):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return

            err_msg = str(exc)
            if retryable and job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.RETRYING
                job.error = f"Retry {job.retry_count}/{job.max_retries}: {err_msg}"
                job.updated_at = datetime.now(timezone.utc).isoformat()
                # Exponential backoff + jitter
                delay = (job.base_delay * (2 ** (job.retry_count - 1))) + (random.uniform(0.05, 0.15))
            else:
                # Retries exhausted or non-retryable error
                if retryable and job.retry_count >= job.max_retries:
                    job.status = JobStatus.DEAD_LETTER
                    job.error = f"Exceeded max retries ({job.max_retries}). Last error: {err_msg}"
                else:
                    job.status = JobStatus.FAILED
                    job.error = err_msg
                job.progress = 100
                job.completed_at = datetime.now(timezone.utc).isoformat()
                job.updated_at = job.completed_at
                return

        # If retrying, sleep for backoff outside lock and re-dispatch
        time.sleep(delay)
        self._dispatch(job_id)

    def _mark_succeeded(self, job_id: str, result: Any):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = JobStatus.SUCCEEDED
            job.progress = 100
            job.result = result if isinstance(result, dict) else {"output": result}
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.updated_at = job.completed_at

    def _mark_failed(self, job_id: str, error: str, retryable: bool = False):
        self._handle_failure(job_id, NonRetryableError(error) if not retryable else RetryableError(error), retryable)

    def get_job(self, job_id: str, tenant_id: Optional[str] = None) -> Optional[BoundedJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            if tenant_id and job.tenant_id != tenant_id:
                return None
            return job

    def list_jobs(self, tenant_id: Optional[str] = None, status: Optional[JobStatus] = None) -> List[BoundedJob]:
        with self._lock:
            jobs = list(self._jobs.values())
            if tenant_id:
                jobs = [j for j in jobs if j.tenant_id == tenant_id]
            if status:
                jobs = [j for j in jobs if j.status == status]
            return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def list_dead_letter_jobs(self, tenant_id: Optional[str] = None) -> List[BoundedJob]:
        """Returns all jobs currently residing in the Dead Letter Queue (DLQ)."""
        return self.list_jobs(tenant_id=tenant_id, status=JobStatus.DEAD_LETTER)

    def retry_dead_letter_job(self, job_id: str, tenant_id: Optional[str] = None) -> BoundedJob:
        """Manually retries a dead-lettered job, resetting retry count and re-enqueuing."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise KeyError(f"Job '{job_id}' not found.")
            if tenant_id and job.tenant_id != tenant_id:
                raise PermissionError("Cross-tenant DLQ manipulation blocked.")
            if job.status != JobStatus.DEAD_LETTER:
                raise ValueError(f"Job '{job_id}' is in state '{job.status.value}', not DEAD_LETTER.")

            job.status = JobStatus.QUEUED
            job.retry_count = 0
            job.error = None
            job.updated_at = datetime.now(timezone.utc).isoformat()

        self._dispatch(job_id)
        return job

    def discard_dead_letter_job(self, job_id: str, tenant_id: Optional[str] = None) -> bool:
        """Purges a dead-lettered job from the queue."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            if tenant_id and job.tenant_id != tenant_id:
                raise PermissionError("Cross-tenant DLQ manipulation blocked.")
            del self._jobs[job_id]
            if job.idempotency_key:
                self._idempotency_index.pop(job.idempotency_key, None)
            return True

    def cancel_job(self, job_id: str, tenant_id: Optional[str] = None) -> bool:
        """Cancels a queued or retrying job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            if tenant_id and job.tenant_id != tenant_id:
                raise PermissionError("Cross-tenant job cancellation blocked.")
            if job.status in (JobStatus.QUEUED, JobStatus.RETRYING):
                job.status = JobStatus.CANCELLED
                job.updated_at = datetime.now(timezone.utc).isoformat()
                return True
            return False

    def shutdown(self, wait: bool = True):
        self._executor.shutdown(wait=wait)

    def clear(self):
        with self._lock:
            self._jobs.clear()
            self._idempotency_index.clear()


# Global default engine instance
production_job_engine = ProductionJobEngine(max_workers=5, max_queue_size=1000)
