import hashlib
import json
import logging
import os
import threading
from datetime import datetime
from typing import Dict, Any

from src.config.constants import CACHE_DIR
from src.services.summary_workflow import run_summary_workflow_from_saved_transcripts
from src.utils.job_state import JobStatusManager
from src.utils.job_utils import _write_json_atomic
from src.config.runtime import (
    CONFERENCE_LONG_QA_PROMPT_VERSION,
    EARNINGS_SHORT_QA_PROMPT_VERSION,
    EARNINGS_LONG_QA_PROMPT_VERSION,
    OVERVIEW_PROMPT_VERSION,
    JUDGE_PROMPT_VERSION,
)

logger = logging.getLogger(__name__)

_JOB_INDEX_PATH = os.path.join(CACHE_DIR, "job_index.json")


def _compute_signature(content_hash: str, call_type: str, summary_length: str, prompt_sig: str, answer_format: str = "prose") -> str:
    """Compute a dedup signature using transcript hash, user parameters, prompt versions, and answer format."""
    try:
        raw = f"{content_hash}|{call_type}|{summary_length}|{prompt_sig}|{answer_format}".encode(
            "utf-8", errors="ignore"
        )
    except Exception:
        raw = b""
    return hashlib.sha1(raw).hexdigest()[:32]


# Helper function to read a JSON file safely
def _safe_read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        logging.warning("Failed to read JSON %s: %s", path, e)
        return None


# Helper function to read the job index
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


# Helper function to write the job index
def _write_job_index(path: str, data: dict) -> None:
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
        logging.warning("Failed to atomically write job index %s: %s", path, e)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _can_reuse_job(job_id: str) -> bool:
    job_dir = os.path.join(CACHE_DIR, job_id)
    status_path = os.path.join(job_dir, "status.json")
    status_json = _safe_read_json(status_path)
    if not status_json:
        return False

    stages = status_json.get("stages") or {}
    if not (
        isinstance(stages, dict)
        and stages.get("q_a_summary") == "completed"
        and stages.get("overview_summary") == "completed"
        and stages.get("summary_evaluation") == "completed"
    ):
        return False

    # Ensure all outputs exist and parse
    for fname in ("q_a_summary.json", "overview_summary.json", "summary_evaluation.json"):
        fpath = os.path.join(job_dir, fname)
        if _safe_read_json(fpath) is None:
            return False

    return True


def _run_workflow_background(
    transcript_json_name: str,
    call_type_bg: str,
    summary_length_bg: str,
    job_dir_bg: str,
    cancel_event_bg: threading.Event,
    answer_format_bg: str = "prose",
) -> None:
    try:
        run_summary_workflow_from_saved_transcripts(
            transcript_name=transcript_json_name,
            call_type=call_type_bg,
            summary_length=summary_length_bg,
            job_dir=job_dir_bg,
            cancel_event=cancel_event_bg,
            answer_format=answer_format_bg,
        )
    except Exception as e:
        logger.exception(
            "Background summary workflow failed for %s: %s", transcript_json_name, e)


def _create_new_job(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new job, starts the workflow, and updates the dedup index."""
    transcript_name = payload.get("transcript_name") or "transcript.json"
    call_type = payload.get("input", {}).get("call_type")
    summary_length = payload.get("input", {}).get("summary_length")

    # 1. Generate Job ID and Directory
    raw_id = f"{transcript_name}-{datetime.now().isoformat()}".encode("utf-8")
    job_id = hashlib.sha1(raw_id).hexdigest()[:16]
    job_dir = os.path.join(CACHE_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    # 2. Write Initial Status
    status_payload = {
        "job_id": job_id,
        "transcript_name": transcript_name,
        "current_stage": "q_a_summary",
        "stages": {
            "validating": "completed", "q_a_summary": "pending",
            "overview_summary": "pending", "summary_evaluation": "pending",
        },
        "percent_complete": 10,
        "updated_at": datetime.now().isoformat(),
        "input": payload.get("input", {}),
    }
    _write_json_atomic(os.path.join(job_dir, "status.json"), status_payload)

    # 3. Start Background Workflow
    cancel_evt = threading.Event()
    JobStatusManager.register_cancel_event(job_id, cancel_evt)
    answer_format = (payload.get("input", {}) or {}
                     ).get("answer_format", "prose")
    threading.Thread(
        target=_run_workflow_background,
        args=(transcript_name, call_type,
              summary_length, job_dir, cancel_evt, answer_format),
        daemon=True,
    ).start()

    # 4. Update Dedup Index
    try:
        transcript_path = os.path.join(CACHE_DIR, transcript_name)
        transcript_doc = _safe_read_json(transcript_path) or {}
        content_hash = transcript_doc.get("content_hash")
        if content_hash:
            if call_type.lower() == "conference":
                q_a_prompt_ver = CONFERENCE_LONG_QA_PROMPT_VERSION
            else:
                q_a_prompt_ver = EARNINGS_SHORT_QA_PROMPT_VERSION if (
                    summary_length or "").lower() == "short" else EARNINGS_LONG_QA_PROMPT_VERSION
            prompt_sig = f"{q_a_prompt_ver}|{OVERVIEW_PROMPT_VERSION}|{JUDGE_PROMPT_VERSION}"
            signature = _compute_signature(
                content_hash, call_type, summary_length, prompt_sig, answer_format)
            index = _read_job_index(_JOB_INDEX_PATH)
            index[signature] = job_id
            _write_job_index(_JOB_INDEX_PATH, index)
            logger.info("Dedup index updated: signature=%s job_id=%s",
                        signature, job_id)
    except Exception as e:
        logger.warning(
            "Failed to update dedup index for job %s: %s", job_id, e)

    return {**payload, "job_id": job_id, "dedup_hit": False}


def _handle_deduplication(payload: Dict[str, Any]) -> Dict[str, Any] | None:
    """Checks for a reusable job and returns a response payload if found."""
    try:
        call_type = payload.get("input", {}).get("call_type")
        summary_length = payload.get("input", {}).get("summary_length")
        transcript_name = payload.get("transcript_name")
        if not all([call_type, summary_length, transcript_name]):
            logger.warning("Missing required fields for deduplication check.")
            return None

        transcript_path = os.path.join(CACHE_DIR, transcript_name)
        transcript_doc = _safe_read_json(transcript_path)
        content_hash = (transcript_doc or {}).get("content_hash")

        if not content_hash:
            return None

        # Build prompt signature
        if call_type.lower() == "conference":
            q_a_prompt_ver = CONFERENCE_LONG_QA_PROMPT_VERSION
        else:
            q_a_prompt_ver = EARNINGS_SHORT_QA_PROMPT_VERSION if (
                summary_length or "").lower() == "short" else EARNINGS_LONG_QA_PROMPT_VERSION
        prompt_sig = f"{q_a_prompt_ver}|{OVERVIEW_PROMPT_VERSION}|{JUDGE_PROMPT_VERSION}"

        answer_format = (payload.get("input", {}) or {}).get(
            "answer_format", "prose")

        # Compute signature and check index
        signature = _compute_signature(
            content_hash, call_type, summary_length, prompt_sig, answer_format)
        index = _read_job_index(_JOB_INDEX_PATH)
        existing_job_id = index.get(signature)

        if isinstance(existing_job_id, str) and _can_reuse_job(existing_job_id):
            logger.info("Dedup hit: signature=%s job_id=%s",
                        signature, existing_job_id)
            return {**payload, "job_id": existing_job_id, "dedup_hit": True}

    except Exception as e:
        logger.warning(
            "Dedup check failed; proceeding to create new job: %s", e)

    return None
