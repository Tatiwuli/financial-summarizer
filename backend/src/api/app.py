from fastapi import FastAPI, status, Request, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import os
import logging
import time
import json
import hashlib
import threading
import shutil


from src.services.precheck import PrecheckError, run_validate_file
from src.services.job_utils import _get_lock_for_job
from src.services.summary_workflow import SummaryWorkflowError, run_summary_workflow_from_saved_transcripts
from src.services.job_utils import _get_lock_for_job
from src.config.runtime import (
    TRANSCRIPTS_DIR,
    EARNINGS_LONG_Q_A_PROMPT_VERSION,
    EARNINGS_SHORT_Q_A_PROMPT_VERSION,
    CONFERENCE_LONG_Q_A_PROMPT_VERSION,

    OVERVIEW_PROMPT_VERSION,
    JUDGE_PROMPT_VERSION,
)
from src.config.file_constants import RETENTION_DAYS, FORCE_CLEANUP_DAYS, CLEANUP_INTERVAL_SECONDS, TRANSCRIPTS_DIR


#Initializing the FastAPI app
app = FastAPI(title="Summarizer v1")


#Defining the origins to allow requests from
raw_origins = os.getenv("CORS_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in raw_origins.split(",") if o.strip()]

# For local test
ALLOWED_ORIGINS_LOCALHOST = [
    "http://localhost:8081", "http://192.168.15.3:8081"]


#Initializing the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")
logger.info(f"CORS_ORIGINS raw='{raw_origins}', parsed={ALLOWED_ORIGINS}")

# Global registry of cancel events per job_id for canceling jobs
_CANCEL_EVENTS: dict[str, threading.Event] = {}

# Path for dedup index mapping signature -> job_id
_JOB_INDEX_PATH = os.path.join(TRANSCRIPTS_DIR, "job_index.json")




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


# Helper function to run a cleanup cycle
def _run_cleanup_cycle():
    """One cleanup cycle: identify, delete, and prune index with locking."""
    logger.info("Cache cleanup cycle started.")
    try:
        os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
        now = datetime.now()
        normal_cutoff = now - timedelta(days=RETENTION_DAYS)
        force_cutoff = now - timedelta(days=FORCE_CLEANUP_DAYS)

        active_job_ids: set[str] = set()
        job_ids_to_delete: list[str] = []

        with os.scandir(TRANSCRIPTS_DIR) as it:
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
            job_dir = os.path.join(TRANSCRIPTS_DIR, job_id)
            job_lock = _get_lock_for_job(job_id)
            try:
                with job_lock:
                    shutil.rmtree(job_dir, ignore_errors=False)
                    logger.info("Cache cleanup: removed job_dir=%s", job_dir)
            except Exception as e:
                logging.warning(
                    "Cache cleanup: failed to remove %s: %s", job_dir, e)

        idx = _read_job_index(_JOB_INDEX_PATH)
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
        logging.exception("Cache cleanup cycle failed: %s", e)
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
        logging.exception("Failed to start cache cleanup worker: %s", e)


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


# CORS for allowing connection from the frontend
app.add_middleware(
    CORSMiddleware,

    allow_origins=ALLOWED_ORIGINS or ALLOWED_ORIGINS_LOCALHOST,  # frontend's URLs
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


# Middleware to log request/response and CORS headers for debugging : see on Render
@app.middleware("http")
async def cors_debug_logger(request: Request, call_next):
    start_time = time.time()
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    host = request.headers.get("host")
    xff = request.headers.get("x-forwarded-for")
    xfp = request.headers.get("x-forwarded-proto")
    logger.info(
        f"REQ method={request.method} path={request.url.path} origin={origin} referer={referer} host={host} xff={xff} xfp={xfp}"
    )
    response = await call_next(request)
    aco = response.headers.get("access-control-allow-origin")
    vary = response.headers.get("vary")
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        f"RES path={request.url.path} status={response.status_code} A-C-Allow-Origin={aco} Vary={vary} durMs={duration_ms}"
    )
    return response


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SummaryResponse(BaseModel):
    title: str
    call_type: str
    blocks: List[Any]


class PrecheckResponse(BaseModel):
    blocks: List[Any]

# ---------EXCEPTION HANDLERS ---------------


@app.exception_handler(PrecheckError)
async def precheck_error_handler(request: Request, exc: PrecheckError):
    return JSONResponse(
        content=ErrorResponse(error=ErrorDetail(
            code=exc.code, message=exc.message)).model_dump(),
        status_code=status.HTTP_400_BAD_REQUEST
    )


@app.exception_handler(SummaryWorkflowError)
async def summary_workflow_error_handler(request: Request, exc: SummaryWorkflowError):
    code_map = {
        "llm_invalid_json": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "llm_summary_error": status.HTTP_502_BAD_GATEWAY,
        "llm_judge_error": status.HTTP_502_BAD_GATEWAY,
        "llm_overview_error": status.HTTP_502_BAD_GATEWAY,
    }

    status_code = code_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    return JSONResponse(
        content=ErrorResponse(error=ErrorDetail(
            code=exc.code, message=exc.message)).model_dump(),
        status_code=status_code
    )


# ------------------- API ROUTES---------------------
@app.get("/")
def root():
    return {"message": "Financial Summarizer API"}

# Check server status


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.on_event("startup")
def _on_startup_cleanup_worker():
    try:
        _start_cleanup_thread()
    except Exception as e:
        logging.exception("Failed to start cleanup worker on startup: %s", e)

# Validate file


@app.post("/validate_file")
async def validate_file_endpoint(
    file: UploadFile = File(..., description="The pdf file to validate"),
    call_type: str = Form(...,
                          description="The type of call provided by user"),
    summary_length: str = Form(..., description="The desired summary length"),
    answer_format: str = Form(
        "prose", description="The answer format: prose or bullet")
):
    """
    Endpoint that receives a PDF file, validates it and returns the validation result and text sections
    """

    if file.content_type != "application/pdf":
        raise PrecheckError(
            "invalid_file_type",
            f"Tipo de arquivo inválido. Esperado arquivo com extensao '.pdf ', mas recebido '{file.content_type}'",
        )

    payload = run_validate_file(
        file=file, call_type=call_type, summary_length=summary_length, answer_format=answer_format)

    # Check if Q&A transcript exists. If not, mark the file not validated and return
    try:
        transcript_name_check = payload.get("transcript_name")
        if transcript_name_check:
            transcript_path_check = os.path.join(
                TRANSCRIPTS_DIR, transcript_name_check)
            with open(transcript_path_check, "r", encoding="utf-8") as f:
                saved_doc = json.load(f)
            qa_text_check = ((saved_doc or {}).get(
                "transcripts", {}).get("q_a") or "").strip()
            if not qa_text_check:
                payload = dict(payload)
                payload["is_validated"] = False

                payload["error"] = {
                    "code": "no_q_a_transcript",
                    "message": "No Q&A transcript found",
                }
    except Exception as e:
        logging.exception("Post-validation Q&A check failed: %s", e)

    # If validation failed, return early without creating a job
    if not bool(payload.get("is_validated")):
        return payload

    # --------- DEDUP CHECK (reuse only if all outputs completed and present) ---------
    try:
        transcript_name_for_sig = payload.get("transcript_name")
        transcript_json_path = os.path.join(
            TRANSCRIPTS_DIR, transcript_name_for_sig)
        transcript_doc = _safe_read_json(transcript_json_path)
        content_hash = (transcript_doc or {}).get("content_hash")
        if content_hash:
            # Build prompt signature (include Q&A prompt based on call_type and summary_length, plus Overview and Judge)

            if call_type.lower() == "conference":
                q_a_prompt_ver = (
                    CONFERENCE_LONG_Q_A_PROMPT_VERSION
                )
            else:
                # Default to earnings settings for earnings or unknown call types
                q_a_prompt_ver = (
                    EARNINGS_SHORT_Q_A_PROMPT_VERSION if (summary_length or "").lower(
                    ) == "short" else EARNINGS_LONG_Q_A_PROMPT_VERSION
                )
            prompt_sig = f"{q_a_prompt_ver}|{OVERVIEW_PROMPT_VERSION}|{JUDGE_PROMPT_VERSION}"
            # Prefer answer_format from validation payload; fallback to saved transcript JSON
            answer_format = (payload.get("input", {}) or {}
                             ).get("answer_format", "prose")
            if not isinstance(answer_format, str) or answer_format not in ("prose", "bullet"):
                try:
                    answer_format = (transcript_doc.get("input", {}) or {}).get(
                        "answer_format", "prose")
                except Exception:
                    answer_format = "prose"
            signature = _compute_signature(
                content_hash, call_type, summary_length, prompt_sig, answer_format)
            print(f"prompt_sig: {prompt_sig}")
            index = _read_job_index(_JOB_INDEX_PATH)
            existing_job_id = index.get(signature)
            if isinstance(existing_job_id, str) and existing_job_id:
                print(
                    f"[DEDUP] Therre is a matched Existing job_id: {existing_job_id}")
                if _can_reuse_job(existing_job_id):
                    print(
                        f"[DEDUP] The existing job_id {existing_job_id} can be reused")
                    logger.info("Dedup hit: signature=%s job_id=%s",
                                signature, existing_job_id)
                    reused = dict(payload)
                    reused["job_id"] = existing_job_id
                    reused["dedup_hit"] = True
                    return reused
    except Exception as e:
        logging.warning(
            "Dedup check failed; proceeding to create new job: %s", e)

    # Create a job to run the summary workflow asynchronously
    transcript_name = payload.get("transcript_name") or "transcript.json"
    # Generate a simple job_id based on transcript name + timestamp
    raw_id = f"{transcript_name}-{datetime.now().isoformat()}".encode("utf-8",
                                                                      errors="ignore")
    job_id = hashlib.sha1(raw_id).hexdigest()[:16]

    # Prepare job directory and initial status.json
    job_dir = os.path.join(TRANSCRIPTS_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    # Write initial status.json
    status_payload = {
        "job_id": job_id,
        "transcript_name": transcript_name,
        "current_stage": "q_a_summary",
        "stages": {
            "validating": "completed",
            "q_a_summary": "pending",
            "overview_summary": "pending",
            "summary_evaluation": "pending",
        },
        "percent_complete": 10,
        "updated_at": datetime.now().isoformat(),
        "input": payload.get("input", {}),
    }
    try:
        _write_json_atomic(os.path.join(
            job_dir, "status.json"), status_payload)
    except Exception as e:
        logging.exception("Failed to write initial status.json: %s", e)

    # Prepare cancel event and start background thread
    cancel_evt = threading.Event()
    _CANCEL_EVENTS[job_id] = cancel_evt

    # Trigger the summary workflow asynchronously using saved transcripts JSON
    def _run_workflow_background(transcript_json_name: str, call_type_bg: str, summary_length_bg: str, job_dir_bg: str, cancel_event_bg: threading.Event, answer_format_bg: str = "prose"):
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
            logging.exception("Background summary workflow failed: %s", e)

    # Extract answer_format preferring payload; fallback to saved transcript JSON
    answer_format = (payload.get("input", {}) or {}
                     ).get("answer_format", "prose")
    if not isinstance(answer_format, str) or answer_format not in ("prose", "bullet"):
        try:
            transcript_json_path = os.path.join(
                TRANSCRIPTS_DIR, transcript_name)
            with open(transcript_json_path, "r", encoding="utf-8") as f:
                saved_doc = json.load(f)
            answer_format = (saved_doc.get("input", {}) or {}
                             ).get("answer_format", "prose")
        except Exception as e:
            logging.warning(
                "Failed to extract answer_format from transcript, using default: %s", e)
            answer_format = "prose"
    logging.info("[validate_file endpoint] answer format: %s", answer_format)

    try:
        threading.Thread(
            target=_run_workflow_background,
            args=(transcript_name, call_type,
                  summary_length, job_dir, cancel_evt, answer_format),
            daemon=True,
        ).start()
    except Exception as e:
        logging.exception(
            "Failed to start background thread for summary workflow: %s", e)

    # Update dedup index mapping to this new job_id
    try:
        transcript_json_for_index = os.path.join(
            TRANSCRIPTS_DIR, transcript_name)
        transcript_doc_for_index = _safe_read_json(
            transcript_json_for_index) or {}
        ch = transcript_doc_for_index.get("content_hash")
        if ch:

            if call_type.lower() == "conference":
                q_a_prompt_ver_idx = (
                    CONFERENCE_LONG_Q_A_PROMPT_VERSION
                )
            else:
                # Default to earnings settings for earnings or unknown call types
                q_a_prompt_ver_idx = (
                    EARNINGS_SHORT_Q_A_PROMPT_VERSION if (summary_length or "").lower(
                    ) == "short" else EARNINGS_LONG_Q_A_PROMPT_VERSION
                )
            prompt_sig_idx = f"{q_a_prompt_ver_idx}|{OVERVIEW_PROMPT_VERSION}|{JUDGE_PROMPT_VERSION}"
            # Prefer answer_format from validation payload; fallback to saved transcript JSON
            answer_format_idx = (payload.get("input", {}) or {}).get(
                "answer_format", "prose")
            if not isinstance(answer_format_idx, str) or answer_format_idx not in ("prose", "bullet"):
                try:
                    answer_format_idx = (transcript_doc_for_index.get(
                        "input", {}) or {}).get("answer_format", "prose")
                except Exception:
                    answer_format_idx = "prose"
            sig = _compute_signature(
                ch, call_type, summary_length, prompt_sig_idx, answer_format_idx)
            idx = _read_job_index(_JOB_INDEX_PATH)
            idx[sig] = job_id
            _write_job_index(_JOB_INDEX_PATH, idx)
            logger.info(
                "Dedup index updated: signature=%s job_id=%s", sig, job_id)
    except Exception as e:
        logging.warning("Failed to update dedup index: %s", e)

    # Add job_id to the response for frontend polling
    extended = dict(payload)
    extended["job_id"] = job_id
    extended["dedup_hit"] = False
    return extended


@app.get("/summary")
async def get_summary(job_id: str):
    """
    Returns job status and any available outputs for the given job_id.
    """
    job_dir = os.path.join(TRANSCRIPTS_DIR, job_id)
    status_path = os.path.join(job_dir, "status.json")
    if not os.path.exists(status_path):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={
            "error": {"code": "job_not_found", "message": f"Job {job_id} not found"}
        })

    # Load status
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            status_json = json.load(f)
    except Exception as e:
        logging.exception("Failed to read status.json: %s", e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
            "error": {"code": "status_read_error", "message": "Failed to read job status"}
        })

    # Load partial outputs if present
    outputs: Dict[str, Any] = {}
    try:
        qa_path = os.path.join(job_dir, "q_a_summary.json")
        if os.path.exists(qa_path):
            with open(qa_path, "r", encoding="utf-8") as f:
                outputs["q_a_summary"] = json.load(f)
    except Exception as e:
        logging.exception("Failed to read q_a_summary.json: %s", e)

    try:
        ov_path = os.path.join(job_dir, "overview_summary.json")
        if os.path.exists(ov_path):
            with open(ov_path, "r", encoding="utf-8") as f:
                outputs["overview_summary"] = json.load(f)
    except Exception as e:
        logging.exception("Failed to read overview_summary.json: %s", e)

    try:
        judge_path = os.path.join(job_dir, "summary_evaluation.json")
        if os.path.exists(judge_path):
            with open(judge_path, "r", encoding="utf-8") as f:
                outputs["summary_evaluation"] = json.load(f)
    except Exception as e:
        logging.exception("Failed to read summary_evaluation.json: %s", e)

    response = dict(status_json)
    response["outputs"] = outputs
    return response


@app.post("/cancel")
async def cancel_job(job_id: str):
    job_dir = os.path.join(TRANSCRIPTS_DIR, job_id)
    status_path = os.path.join(job_dir, "status.json")
    if not os.path.exists(status_path):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={
            "error": {"code": "job_not_found", "message": f"Job {job_id} not found"}
        })

    # signal cancel
    evt = _CANCEL_EVENTS.get(job_id)
    if evt is not None:
        try:
            evt.set()
        except Exception:
            pass

    # update status to cancelled immediately
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            current = json.load(f)
    except Exception:
        current = {}

    current["current_stage"] = "cancelled"
    current["updated_at"] = datetime.now().isoformat()
    stages = current.get("stages") or {}
    if isinstance(stages, dict):
        for k, v in list(stages.items()):
            if v == "running":
                stages[k] = "failed"
        current["stages"] = stages
    current["error"] = {"code": "cancelled", "message": "Cancelled by user"}

    try:
        _write_json_atomic(status_path, current)
    except Exception as e:
        logging.exception("Failed to mark job cancelled: %s", e)

    # remove any persisted outputs so cancellation leaves no artifacts
    try:
        for fname in ("q_a_summary.json", "overview_summary.json", "summary_evaluation.json"):
            fpath = os.path.join(job_dir, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception as re:
                    logging.exception(
                        "Failed to remove %s for job %s: %s", fname, job_id, re)
    except Exception as e:
        logging.exception("Error during cancelled job cleanup: %s", e)

    return {"ok": True, "job_id": job_id, "status": "cancelled"}


# @app.post("/v1/summarize")
# async def summarize_endpoint(
#     file: UploadFile = File(..., description="The pdf file to summarize"),
#     call_type: str = Form(..., description="The type of call to summarize"),

#     summary_length: str = Form(..., description="The length of the summary")
# ):
#     """
#     Old endpoint that handles the entire workflow from pdf processing to summary generation.

#     """

#     if file.content_type != "application/pdf":
#         raise PrecheckError(
#             "invalid_file_type", f"Tipo de arquivo inválido. Esperado arquivo com extensao '.pdf ', mas recebido '{file.content_type}'")

#     payload = run_summary_workflow(
#         file=file, call_type=call_type, summary_length=summary_length)
#     return payload


# ------------------- DEDUP HELPERS ---------------------
def _compute_signature(content_hash: str, call_type: str, summary_length: str, prompt_sig: str, answer_format: str = "prose") -> str:
    """Compute a dedup signature using transcript hash, user parameters, prompt versions, and answer format."""
    try:
        raw = f"{content_hash}|{call_type}|{summary_length}|{prompt_sig}|{answer_format}".encode(
            "utf-8", errors="ignore"
        )
    except Exception:
        raw = b""
    return hashlib.sha1(raw).hexdigest()[:32]


def _safe_read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        logging.warning("Failed to read JSON %s: %s", path, e)
        return None


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
    job_dir = os.path.join(TRANSCRIPTS_DIR, job_id)
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
