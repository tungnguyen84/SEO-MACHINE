"""
Test Suite: Durable PostgreSQL Job Queue, Multi-Worker Claiming & Crash Recovery
Verifies:
1. Multi-worker distributed job claiming across processes with SELECT FOR UPDATE SKIP LOCKED (zero duplicates).
2. Queue durability across worker kill and restart (jobs not lost).
3. Job crash recovery: zombie jobs with expired leases are reclaimed and processed.
4. Idempotency persistence across restart.
5. Queue saturation and backpressure under load.
"""

import os
import time
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from concurrent.futures import ThreadPoolExecutor
import uuid
from core.database import get_db_session
from core.jobs.durable_queue import DurableJobEngine, QueueFullError, RetryableError

POSTGRES_URL = "postgresql://openseo_user:openseo_secure_staging_password_2026@127.0.0.1:5432/openseo_staging"


@pytest.fixture(scope="module", autouse=True)
def setup_env():
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = POSTGRES_URL
    yield
    if old:
        os.environ["DATABASE_URL"] = old


@pytest.fixture(autouse=True)
def clean_jobs_table():
    clean_session = get_db_session()
    try:
        clean_session.execute(text("DELETE FROM jobs"))
        clean_session.commit()
    finally:
        clean_session.close()
    yield
    clean_session = get_db_session()
    try:
        clean_session.execute(text("DELETE FROM jobs"))
        clean_session.commit()
    finally:
        clean_session.close()


def test_01_multi_worker_job_claiming_no_duplicates():
    """
    Simulates TWO independent worker processes competing for the same queued jobs.
    Uses PostgreSQL SELECT FOR UPDATE SKIP LOCKED to verify zero duplicate claims.
    """
    worker_1 = DurableJobEngine(worker_id="worker_process_01", lease_seconds=30)
    worker_2 = DurableJobEngine(worker_id="worker_process_02", lease_seconds=30)

    # Submit 10 competing jobs
    job_ids = []
    for i in range(10):
        res = worker_1.submit_job(
            task_type="multi_worker_task",
            payload={"item_id": i},
            tenant_id="tenant_mw_test"
        )
        job_ids.append(res["job_id"])

    claimed_by_w1 = []
    claimed_by_w2 = []

    def run_worker_1():
        while True:
            job = worker_1.claim_next_job()
            if not job:
                break
            claimed_by_w1.append(job["job_id"])
            time.sleep(0.02)
            worker_1.mark_succeeded(job["job_id"], {"status": "done_by_w1"})

    def run_worker_2():
        while True:
            job = worker_2.claim_next_job()
            if not job:
                break
            claimed_by_w2.append(job["job_id"])
            time.sleep(0.02)
            worker_2.mark_succeeded(job["job_id"], {"status": "done_by_w2"})

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(run_worker_1)
        f2 = pool.submit(run_worker_2)
        f1.result()
        f2.result()

    # Total claimed must equal 10
    total_claimed = len(claimed_by_w1) + len(claimed_by_w2)
    assert total_claimed == 10

    # Overlap between worker 1 and worker 2 claims must be exactly 0 (No duplicate claims!)
    overlap = set(claimed_by_w1).intersection(set(claimed_by_w2))
    assert len(overlap) == 0

    print(f"\n[MULTI-WORKER RESULT] Worker 1 claimed: {len(claimed_by_w1)}, Worker 2 claimed: {len(claimed_by_w2)}, Overlap: 0")


def test_02_durable_queue_across_worker_restart():
    """
    Submits jobs to PostgreSQL.
    Terminates / destroys worker 1 instance.
    Instantiates fresh worker 2 instance.
    Verifies queued jobs were persisted in PostgreSQL and are processed cleanly.
    """
    worker_submitter = DurableJobEngine(worker_id="submitter_temp")
    res = worker_submitter.submit_job(
        task_type="restart_survivor_task",
        payload={"data": "persisted_value"},
        tenant_id="tenant_restart_test"
    )
    job_id = res["job_id"]

    # "Kill" worker submitter (simulate process death)
    del worker_submitter

    # Start new worker after simulated restart
    worker_new = DurableJobEngine(worker_id="new_worker_after_reboot")
    worker_new.register_handler("restart_survivor_task", lambda jid, **payload: {"processed": payload["data"]})

    # Claim and execute
    processed = worker_new.process_one_job()
    assert processed is True

    # Verify job completed in PostgreSQL
    job_data = worker_new.get_job(job_id)
    assert job_data is not None
    assert job_data["status"] == "SUCCEEDED"
    assert job_data["result"] == {"processed": "persisted_value"}


def test_03_job_crash_recovery_zombie_lease():
    """
    Simulates a worker crash while a job is in 'RUNNING' state.
    Once lease expires, another worker automatically reclaims and finishes the job.
    """
    engine = DurableJobEngine(worker_id="crashed_worker", lease_seconds=1)
    res = engine.submit_job("zombie_reclaim_task", payload={"run_count": 1})
    job_id = res["job_id"]

    # Claim job with worker
    claimed = engine.claim_next_job()
    assert claimed is not None
    assert claimed["job_id"] == job_id

    # Verify job is now marked RUNNING in DB
    session = get_db_session()
    try:
        # Simulate worker crashed: job left in RUNNING, and lease expired 10 seconds ago
        expired_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        session.execute(
            text("UPDATE jobs SET lease_expires_at = :exp WHERE id = :id"),
            {"exp": expired_time, "id": job_id}
        )
        session.commit()
    finally:
        session.close()

    # New surviving worker wakes up
    surviving_worker = DurableJobEngine(worker_id="rescuer_worker", lease_seconds=30)
    surviving_worker.register_handler("zombie_reclaim_task", lambda jid, **p: {"recovered_and_done": True})

    # Surviving worker reclaims the expired zombie job
    reclaimed = surviving_worker.claim_next_job()
    assert reclaimed is not None
    assert reclaimed["job_id"] == job_id
    assert surviving_worker.worker_id != "crashed_worker"

    # Finish job
    surviving_worker.mark_succeeded(job_id, {"status": "recovered"})
    final_job = surviving_worker.get_job(job_id)
    assert final_job["status"] == "SUCCEEDED"


def test_04_idempotency_persisted_across_restart():
    """
    Submits an external operation job with an idempotency key.
    Restarts worker. Resubmits with identical key.
    Verifies duplicate is rejected and existing job returned.
    """
    engine_1 = DurableJobEngine(worker_id="w_idem_1")
    idem_key = f"external_payment_payout_{uuid.uuid4().hex[:8]}"

    res_1 = engine_1.submit_job(
        "payment_job",
        payload={"amount": 500},
        idempotency_key=idem_key
    )
    assert res_1.get("is_duplicate") is not True

    # Process job to SUCCEEDED
    engine_1.register_handler("payment_job", lambda jid, **p: {"charged": p["amount"]})
    engine_1.process_one_job()

    # Destroy engine_1 and boot engine_2 (simulate restart)
    del engine_1
    engine_2 = DurableJobEngine(worker_id="w_idem_2")

    # Resubmit with identical key
    res_2 = engine_2.submit_job(
        "payment_job",
        payload={"amount": 500},
        idempotency_key=idem_key
    )
    assert res_2.get("is_duplicate") is True
    assert res_2["job_id"] == res_1["job_id"]
    assert res_2["status"] == "SUCCEEDED"


def test_05_queue_saturation_backpressure():
    """
    Tests queue capacity saturation: submitting beyond max_queue_size raises QueueFullError.
    """
    # Create engine with small queue size for test
    engine = DurableJobEngine(worker_id="w_backpressure", max_queue_size=5)

    # Clean existing QUEUED/RUNNING jobs from previous tests
    session = get_db_session()
    try:
        session.execute(text("DELETE FROM jobs WHERE status IN ('QUEUED', 'RUNNING')"))
        session.commit()
    finally:
        session.close()

    # Fill queue to capacity (5 jobs)
    for i in range(5):
        engine.submit_job("bp_task", payload={"idx": i})

    # 6th job must raise QueueFullError
    with pytest.raises(QueueFullError) as exc_info:
        engine.submit_job("bp_task", payload={"idx": 999})
    assert "Capacity" in str(exc_info.value)
