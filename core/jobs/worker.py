"""
Standalone Durable Queue Worker Process.
Polls PostgreSQL 16 jobs table using SELECT ... FOR UPDATE SKIP LOCKED.
Handles durable background task execution with automatic heartbeat renewal and crash recovery.
"""

import sys
import time
import argparse
import logging
from core.jobs.durable_queue import DurableJobEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [worker:%(name)s] %(message)s"
)
logger = logging.getLogger("DurableWorker")


def run_worker(worker_id: str, poll_interval: float = 2.0):
    logger.info(f"Starting Durable Worker process with ID: {worker_id}")
    engine = DurableJobEngine(worker_id=worker_id)
    
    # Register default staging handlers
    engine.register_handler(
        "draft_generation",
        lambda jid, **p: {"article_id": f"art_{jid}", "title": p.get("title", "Draft"), "status": "COMPLETED", "words": 1500}
    )
    engine.register_handler(
        "generic",
        lambda jid, **p: {"status": "SUCCESS", "job_id": jid}
    )

    running = True

    try:
        while running:
            try:
                processed = engine.process_one_job()
                if not processed:
                    time.sleep(poll_interval)
            except KeyboardInterrupt:
                logger.info("Worker received shutdown signal. Stopping...")
                running = False
            except Exception as e:
                logger.error(f"Worker loop error: {str(e)}", exc_info=True)
                time.sleep(poll_interval)
    finally:
        logger.info(f"Worker {worker_id} terminated cleanly.")


def main():
    parser = argparse.ArgumentParser(description="OpenSEO Durable Background Worker")
    parser.add_argument("--worker-id", default=f"staging_worker_{int(time.time())}", help="Unique worker identifier")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Poll interval in seconds when queue is idle")
    args = parser.parse_args()

    run_worker(worker_id=args.worker_id, poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
