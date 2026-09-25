"""
Test Suite: Bounded Background Job Engine & Idempotency Governance
Verifies:
1. Bounded thread pool concurrency enforcement.
2. Atomic job claim and state transitions (QUEUED -> RUNNING -> SUCCEEDED / RETRYING / DEAD_LETTER).
3. Idempotency deduplication via idempotency keys.
4. Transient error retry with exponential backoff & jitter.
5. Non-retryable error immediate failure.
6. Dead Letter Queue (DLQ) state transition and manual replay/discard.
7. Backpressure queue capacity limits.
"""

import time
import pytest
import threading
from core.jobs.job_queue import (
    ProductionJobEngine,
    JobStatus,
    QueueFullError,
    RetryableError,
    NonRetryableError,
)


def test_bounded_worker_concurrency():
    """Verify that worker execution does not spawn unbounded threads."""
    engine = ProductionJobEngine(max_workers=3, max_queue_size=50)
    concurrent_executing = 0
    max_observed_concurrency = 0
    lock = threading.Lock()

    def slow_task(job, **payload):
        nonlocal concurrent_executing, max_observed_concurrency
        with lock:
            concurrent_executing += 1
            if concurrent_executing > max_observed_concurrency:
                max_observed_concurrency = concurrent_executing
        time.sleep(0.1)
        with lock:
            concurrent_executing -= 1
        return {"status": "done"}

    engine.register_handler("slow_task", slow_task)

    # Submit 10 jobs simultaneously
    jobs = [engine.submit_job("slow_task") for _ in range(10)]

    # Wait for completion
    time.sleep(0.8)

    # Concurrency must not exceed max_workers (3)
    assert max_observed_concurrency <= 3
    # All 10 jobs should have succeeded
    succeeded = [j for j in jobs if j.status == JobStatus.SUCCEEDED]
    assert len(succeeded) == 10
    engine.shutdown()


def test_idempotency_key_deduplication():
    """Verify that multiple submissions with the same idempotency key return the original job."""
    engine = ProductionJobEngine(max_workers=2)

    def simple_task(job, **payload):
        time.sleep(0.05)
        return {"result": payload.get("data")}

    engine.register_handler("simple_task", simple_task)

    job1 = engine.submit_job("simple_task", payload={"data": 42}, idempotency_key="unique_key_001")
    job2 = engine.submit_job("simple_task", payload={"data": 99}, idempotency_key="unique_key_001")

    # job2 must be the exact same job instance as job1
    assert job1.job_id == job2.job_id
    time.sleep(0.1)
    assert job1.status == JobStatus.SUCCEEDED
    assert job1.result == {"result": 42}
    engine.shutdown()


def test_retryable_error_exponential_backoff_and_dlq():
    """Verify that retryable errors attempt retries before moving to DEAD_LETTER."""
    engine = ProductionJobEngine(max_workers=2)
    attempts = 0

    def flaky_task(job, **payload):
        nonlocal attempts
        attempts += 1
        raise RetryableError(f"Temporary 429 Rate Limit error on attempt {attempts}")

    engine.register_handler("flaky_task", flaky_task)

    # Job with max 2 retries and very short base_delay for fast testing
    job = engine.submit_job("flaky_task", max_retries=2, base_delay=0.05)

    # Wait for retries to exhaust
    time.sleep(0.6)

    assert job.status == JobStatus.DEAD_LETTER
    assert attempts == 3  # Initial + 2 retries
    assert "Exceeded max retries" in (job.error or "")

    # Test DLQ inspection
    dlq_jobs = engine.list_dead_letter_jobs()
    assert len(dlq_jobs) == 1
    assert dlq_jobs[0].job_id == job.job_id

    # Test DLQ discard
    discarded = engine.discard_dead_letter_job(job.job_id)
    assert discarded is True
    assert len(engine.list_dead_letter_jobs()) == 0
    engine.shutdown()


def test_non_retryable_error_fails_immediately():
    """Verify that non-retryable errors (e.g. ValueError, bad schema) fail immediately without retries."""
    engine = ProductionJobEngine(max_workers=2)
    attempts = 0

    def invalid_data_task(job, **payload):
        nonlocal attempts
        attempts += 1
        raise NonRetryableError("Malformed schema: missing mandatory field")

    engine.register_handler("invalid_data_task", invalid_data_task)

    job = engine.submit_job("invalid_data_task", max_retries=3)
    time.sleep(0.1)

    assert job.status == JobStatus.FAILED
    assert attempts == 1  # Only 1 execution, zero retries
    assert "Malformed schema" in (job.error or "")
    engine.shutdown()


def test_queue_capacity_backpressure():
    """Verify that queue overflow raises QueueFullError to defend against worker exhaustion."""
    engine = ProductionJobEngine(max_workers=1, max_queue_size=3)

    def blocked_task(job, **payload):
        time.sleep(0.5)
        return {}

    engine.register_handler("blocked_task", blocked_task)

    # Fill queue to capacity (3 jobs)
    j1 = engine.submit_job("blocked_task")
    j2 = engine.submit_job("blocked_task")
    j3 = engine.submit_job("blocked_task")

    # 4th submission must raise QueueFullError
    with pytest.raises(QueueFullError) as exc_info:
        engine.submit_job("blocked_task")
    assert "Capacity" in str(exc_info.value)
    engine.shutdown()
