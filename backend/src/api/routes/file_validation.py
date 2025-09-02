from fastapi import APIRouter, File, Form, UploadFile
import os
import logging
from typing import Dict, Any

from src.services.precheck import PrecheckError, run_validate_file
from src.utils.job_creation import (
    _safe_read_json, _handle_deduplication, _create_new_job
)
from src.config.constants import CACHE_DIR

# --- Globals & Setup ---
router = APIRouter()
logger = logging.getLogger(__name__)


# --- API Endpoint ---

@router.post("/validate_file")
async def validate_file_endpoint(
    file: UploadFile = File(..., description="The PDF file to validate"),
    call_type: str = Form(...,
                          description="The type of call provided by user"),
    summary_length: str = Form(..., description="The desired summary length"),
    answer_format: str = Form(
        "prose", description="The answer format: prose or bullet")
):
    """
    Receives a PDF file, validates it, and initiates the summary workflow.
    """

    # 1) Validate + extract
    if file.content_type != "application/pdf":
        raise PrecheckError(
            "invalid_file_type",
            f"Invalid file type. Expected '.pdf', but received '{file.content_type}'",
        )

    payload: Dict[str, Any] = run_validate_file(
        file=file, call_type=call_type, summary_length=summary_length, answer_format=answer_format)

    # 2) Ensure Q&A transcript exists
    try:
        transcript_name = payload.get("transcript_name")
        if transcript_name:
            transcript_path = os.path.join(CACHE_DIR, transcript_name)
            saved_doc = _safe_read_json(transcript_path)
            qa_text = (saved_doc or {}).get(
                "transcripts", {}).get("q_a", "").strip()
            if not qa_text:
                payload["is_validated"] = False
                payload["error"] = {
                    "code": "no_q_a_transcript",
                    "message": "No Q&A transcript found in the document.",
                }
    except Exception as e:
        logger.exception("Post-validation Q&A check failed: %s", e)
        payload["is_validated"] = False
        payload["error"] = {"code": "validation_error",
                            "message": "An unexpected error occurred during validation."}

    # 3) Early return on invalid
    if not payload.get("is_validated"):
        return payload

    # 4) Try to reuse an existing job
    if reused_job_payload := _handle_deduplication(payload):
        return reused_job_payload

    # 5) Create a new job
    return _create_new_job(payload)
