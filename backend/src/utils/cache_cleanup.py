import os
import shutil
import time
import threading
import logging
from datetime import datetime, timedelta

from src.utils.job_utils import (
    _get_lock_for_job,
    _job_last_updated,
    _job_is_terminal,
    _read_json_file,
    _write_job_index
)
from src.config.constants import RETENTION_DAYS, FORCE_CLEANUP_DAYS, CLEANUP_INTERVAL_SECONDS, CACHE_DIR


logger = logging.getLogger(__name__)


# Path for dedup index mapping signature -> job_id
_JOB_INDEX_PATH = os.path.join(CACHE_DIR, "job_index.json")


class CacheCleanupError(Exception):
    def __init__(self, message: str):
        self.message = message
        self.transcripts_dir = CACHE_DIR
        self.retention_days = RETENTION_DAYS
        self.force_cleanup_days = FORCE_CLEANUP_DAYS
        self.cleanup_interval_seconds = CLEANUP_INTERVAL_SECONDS


# Helper function to run a cleanup cycle
def _run_cleanup_cycle():
    """One cleanup cycle: identify, delete, and prune index with locking."""
    logger.info("Cache cleanup cycle started.")
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        now = datetime.now()
        normal_cutoff = now - timedelta(days=RETENTION_DAYS)
        force_cutoff = now - timedelta(days=FORCE_CLEANUP_DAYS)

        active_job_ids: set[str] = set()
        job_ids_to_delete: list[str] = []

        with os.scandir(CACHE_DIR) as it:
            for entry in it:
                if not entry.is_dir():
                    continue
                job_id = entry.name
                job_dir = entry.path
                job_lock = _get_lock_for_job(job_id)
                with job_lock:
                    last_updated = _job_last_updated(job_dir)
                    if last_updated < force_cutoff:
                        job_ids_to_delete.append(job_id)
                        logger.info("Staging STUCK job for deletion (older than %d days): %s",
                                    FORCE_CLEANUP_DAYS, job_id)
                        continue
                    if last_updated < normal_cutoff and _job_is_terminal(job_dir):
                        job_ids_to_delete.append(job_id)
                        logger.info(
                            "Staging finished job for deletion: %s", job_id)
                        continue
                    active_job_ids.add(job_id)

        for job_id in job_ids_to_delete:
            job_dir = os.path.join(CACHE_DIR, job_id)
            job_lock = _get_lock_for_job(job_id)
            try:
                with job_lock:
                    shutil.rmtree(job_dir, ignore_errors=False)
                    logger.info("Cache cleanup: removed job_dir=%s", job_dir)
            except Exception as e:
                logger.warning(
                    "Cache cleanup: failed to remove %s: %s", job_dir, e)

        idx = _read_json_file(_JOB_INDEX_PATH)
        if not isinstance(idx, dict):
            idx = {}
        original_count = len(idx)
        pruned_idx = {sig: jid for sig,
                      jid in idx.items() if jid in active_job_ids}
        if len(pruned_idx) != original_count:
            _write_job_index(_JOB_INDEX_PATH, pruned_idx)
            logger.info("Job index prune: removed=%d kept=%d",
                        original_count - len(pruned_idx), len(pruned_idx))
    except Exception as e:
        logger.exception("Cache cleanup cycle failed: %s", e)
    logger.info("Cache cleanup cycle finished.")


# Helper function to start the cleanup thread
def _start_cleanup_thread():
    def _worker():
        # Initial delay to avoid competing with cold-start workload
        time.sleep(10)
        while True:
            _run_cleanup_cycle()
            try:
                time.sleep(CLEANUP_INTERVAL_SECONDS)
            except Exception:
                # If sleep interrupted, continue loop
                pass

    try:
        threading.Thread(target=_worker, name="cache-cleaner",
                         daemon=True).start()
        logger.info("Cache cleanup worker started: retention_days=%d force_days=%d interval_s=%d",
                    RETENTION_DAYS, FORCE_CLEANUP_DAYS, CLEANUP_INTERVAL_SECONDS)
    except Exception as e:
        logger.exception("Failed to start cache cleanup worker: %s", e)
