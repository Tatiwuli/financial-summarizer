import threading
from typing import Dict, Optional, Any
from enum import Enum


import threading
import os
import json
import logging
from typing import Dict
from datetime import datetime


logger = logging.getLogger(__name__)


class Stage(str, Enum):
    QA_SUMMARY = "q_a_summary"
    OVERVIEW = "overview_summary"
    JUDGE = "summary_evaluation"


class Status(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# ----- READ AND WRITES


class JobStatusManager:
    """Encapsulates all logic for reading, writing, and updating job status."""

    def __init__(self, job_dir: Optional[str]):
        self.job_dir = job_dir
        self.is_managed = job_dir is not None
        if self.is_managed:
            self.status_path = os.path.join(job_dir, "status.json")
            self.job_id = os.path.basename(job_dir)
            self.lock = JobStatusManager.get_lock_for_job(self.job_id)

    # Class-level cancel events registry
    _CANCEL_EVENTS: Dict[str, threading.Event] = {}

    @classmethod
    def register_cancel_event(cls, job_id: str, event: threading.Event) -> None:
        cls._CANCEL_EVENTS[job_id] = event

    @classmethod
    def signal_cancel(cls, job_id: str) -> None:
        evt = cls._CANCEL_EVENTS.get(job_id)
        if evt is not None:
            try:
                evt.set()
            except Exception:
                pass

    @classmethod
    def get_cancel_event(cls, job_id: str) -> Optional[threading.Event]:
        return cls._CANCEL_EVENTS.get(job_id)

    # ------------- Class-level locks and helpers -------------
    _JOB_LOCKS: Dict[str, threading.Lock] = {}
    _META_LOCK = threading.Lock()

    @classmethod
    def get_lock_for_job(cls, job_id: str) -> threading.Lock:
        """Return a per-job lock to coordinate access to job resources."""
        with cls._META_LOCK:
            if job_id not in cls._JOB_LOCKS:
                cls._JOB_LOCKS[job_id] = threading.Lock()
        return cls._JOB_LOCKS[job_id]

    @staticmethod
    def _parse_iso(dt_str: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(dt_str)
        except Exception:
            return None

    @staticmethod
    def job_last_updated(job_dir: str) -> datetime:
        """Determine last-updated time for a job directory.
        Prefer status.json's updated_at; fallback to directory mtime.
        """
        status_path = os.path.join(job_dir, "status.json")
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = (data or {}).get("updated_at")
            dt = JobStatusManager._parse_iso(
                ts) if isinstance(ts, str) else None
            if dt is not None:
                return dt
        except Exception:
            pass
        try:
            return datetime.fromtimestamp(os.path.getmtime(job_dir))
        except Exception:
            return datetime.now()

    @staticmethod
    def read_job_index(path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except FileNotFoundError:
            return {}
        except Exception as e:
            logging.warning("Failed to read job index %s: %s", path, e)
            return {}

    @staticmethod
    def write_json_atomic(path: str, data: dict) -> None:
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

    def _read_status(self) -> Dict[str, Any]:
        if not self.is_managed:
            return {}
        try:
            with open(self.status_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read status for job {self.job_id}: {e}")
            return {}

    def _write_status(self, status: Dict[str, Any]) -> bool:
        if not self.is_managed:
            return True
        tmp_path = f"{self.status_path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False)
            os.replace(tmp_path, self.status_path)
            return True
        except Exception as e:
            logger.exception(
                f"Failed to write status for job {self.job_id}: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return False

    def update_status(self, updates: Dict[str, Any]):
        if not self.is_managed:
            return
        with self.lock:
            status = self._read_status()
            # Merge logic for nested 'stages' dictionary
            for key, value in updates.items():
                if key == "stages" and isinstance(value, dict):
                    status.setdefault("stages", {}).update(value)
                else:
                    status[key] = value

            status["updated_at"] = datetime.now().isoformat()
            self._write_status(status)

    def add_warning(self, message: str):
        if not self.is_managed:
            return
        with self.lock:
            status = self._read_status()
            warnings = status.get("warnings", [])
            warnings.append(message)
            status["warnings"] = warnings
            self._write_status(status)

    def set_stage_status(self, stage: Stage, status: Status, error: Optional[Dict] = None):
        update_payload = {"stages": {stage.value: status.value}}
        if status == Status.FAILED and error:
            update_payload["error"] = error
        self.update_status(update_payload)

    def fail_job(self, code: str, message: str):
        self.update_status({
            "current_stage": "failed",
            "error": {"code": code, "message": message}
        })

    def is_job_complete(self) -> bool:
        if not self.is_managed:
            return False
        status = self._read_status()
        stages = status.get("stages", {})
        qa_done = stages.get(Stage.QA_SUMMARY.value) == Status.COMPLETED.value
        ov_terminal = stages.get(Stage.OVERVIEW.value) in (
            Status.COMPLETED.value, Status.FAILED.value)
        judge_terminal = stages.get(Stage.JUDGE.value) in (
            Status.COMPLETED.value, Status.FAILED.value)
        return qa_done and ov_terminal and judge_terminal


# ---------------CANCEL EVENTS---------------
# Process-local registry of cancel events per job_id
class JobStatusManager(JobStatusManager):
    # Class-level cancel events registry
    _CANCEL_EVENTS: Dict[str, threading.Event] = {}

    @classmethod
    def register_cancel_event(cls, job_id: str, event: threading.Event) -> None:
        cls._CANCEL_EVENTS[job_id] = event

    @classmethod
    def signal_cancel(cls, job_id: str) -> None:
        evt = cls._CANCEL_EVENTS.get(job_id)
        if evt is not None:
            try:
                evt.set()
            except Exception:
                pass

    @classmethod
    def get_cancel_event(cls, job_id: str) -> Optional[threading.Event]:
        return cls._CANCEL_EVENTS.get(job_id)
