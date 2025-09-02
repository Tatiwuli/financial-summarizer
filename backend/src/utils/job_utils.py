import threading
import os
import json
import logging
from typing import Dict
from datetime import datetime


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


# Helper function to parse ISO datetime strings
def _parse_iso(dt_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


# Helper function to determine the last-updated time for a job directory
def _job_last_updated(job_dir: str) -> datetime:
    """Determine last-updated time for a job directory.
    Prefer status.json's updated_at; fallback to directory mtime.
    """
    status_path = os.path.join(job_dir, "status.json")
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ts = (data or {}).get("updated_at")
        dt = _parse_iso(ts) if isinstance(ts, str) else None
        if dt is not None:
            return dt
    except Exception:
        pass
    try:
        return datetime.fromtimestamp(os.path.getmtime(job_dir))
    except Exception:
        return datetime.now()


# Helper function to determine if a job is terminal
def _job_is_terminal(job_dir: str) -> bool:
    status_path = os.path.join(job_dir, "status.json")
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        stage = (data or {}).get("current_stage")
        return stage in ("completed", "failed", "cancelled")
    except Exception:
        # If unreadable, be conservative: allow cleanup based on age only
        return True


# Helper function to read job index
def _read_job_index(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        logging.warning("Failed to read job index %s: %s", path, e)
        return {}



# Helper function to write a JSON file atomically
def _write_json_atomic(path: str, data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            try:
                f.flush()
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(tmp, path)
    except Exception as e:
        logging.exception("Failed to atomically write %s: %s", path, e)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
