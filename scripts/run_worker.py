"""scripts/run_worker.py - Huey 分散タスクワーカー起動スクリプト (Step 41)"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.backend.tasks.huey import huey, check_huey_health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("huey_worker")


def main():
    parser = argparse.ArgumentParser(description="AutoNovel Huey Task Worker")
    parser.add_argument("-w", "--workers", type=int, default=2, help="Number of worker processes/threads")
    parser.add_argument("-k", "--worker-type", choices=["thread", "process", "greenlet"], default="thread", help="Worker execution model")
    parser.add_argument("--health-check", action="store_true", help="Run health check and exit")

    args = parser.parse_args()

    health = check_huey_health()
    logger.info("Huey health status: %s", health)

    if args.health_check:
        print(health)
        sys.exit(0 if health.get("status") == "healthy" else 1)

    logger.info("Starting Huey consumer with %d %s workers...", args.workers, args.worker_type)
    consumer = huey.create_consumer(
        workers=args.workers,
        worker_type=args.worker_type,
    )

    # Step 45: グレイスフルシャットダウンハンドラ
    import signal

    def _shutdown_signal_handler(signum, frame):
        logger.info("Received termination signal (%d). Shutting down consumer gracefully...", signum)
        try:
            consumer.stop()
        except Exception as ex:
            logger.warning("Error during consumer.stop(): %s", ex)
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _shutdown_signal_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _shutdown_signal_handler)
    except Exception as e:
        logger.debug("Could not register custom signal handlers: %s", e)

    try:
        consumer.run()
    except KeyboardInterrupt:
        logger.info("Worker stopped by KeyboardInterrupt.")
    finally:
        try:
            consumer.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
