import threading
from typing import Dict


_JOB_LOCKS: Dict[str, threading.Lock] = {}
_META_LOCK = threading.Lock()


def _get_lock_for_job(job_id: str) -> threading.Lock:
    """Return a per-job lock to coordinate access to job resources.

    This lock is process-local. If multiple processes are used, prefer a
    filesystem lock or another inter-process synchronization mechanism.
    """
    with _META_LOCK:
        if job_id not in _JOB_LOCKS:
            _JOB_LOCKS[job_id] = threading.Lock()
    return _JOB_LOCKS[job_id]
