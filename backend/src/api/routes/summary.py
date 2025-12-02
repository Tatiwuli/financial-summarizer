from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
import os
import json
import logging
from typing import Dict, Any
from datetime import datetime

from src.config.constants import CACHE_DIR
from src.utils.job_state import JobStatusManager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/summary")
async def get_summary(job_id: str):
    """
    Returns job status and any available outputs for the given job_id.
    """
    job_dir = os.path.join(CACHE_DIR, job_id)
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
        logger.exception("Failed to read status.json: %s", e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={
            "error": {"code": "status_read_error", "message": "Failed to read job status"}
        })

    # Load partial outputs if present
    #TODO: [Code efficiency] Now it's re-fetching the already rendered outputs.Should avoid re-checking the parts that was already fetched by frontend. 
    outputs: Dict[str, Any] = {}
    try:
        qa_path = os.path.join(job_dir, "q_a_summary.json")
        if os.path.exists(qa_path):
            with open(qa_path, "r", encoding="utf-8") as f:
                outputs["q_a_summary"] = json.load(f)
    except Exception as e:
        logger.exception("Failed to read q_a_summary.json: %s", e)

    try:
        ov_path = os.path.join(job_dir, "overview_summary.json")
        if os.path.exists(ov_path):
            with open(ov_path, "r", encoding="utf-8") as f:
                outputs["overview_summary"] = json.load(f)
    except Exception as e:
        logger.exception("Failed to read overview_summary.json: %s", e)

    try:
        judge_path = os.path.join(job_dir, "summary_evaluation.json")
        if os.path.exists(judge_path):
            with open(judge_path, "r", encoding="utf-8") as f:
                outputs["summary_evaluation"] = json.load(f)
    except Exception as e:
        logger.exception("Failed to read summary_evaluation.json: %s", e)

    response = dict(status_json)
    response["outputs"] = outputs
    return response


@router.post("/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job"""
    job_dir = os.path.join(CACHE_DIR, job_id)
    status_path = os.path.join(job_dir, "status.json")
    if not os.path.exists(status_path):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={
            "error": {"code": "job_not_found", "message": f"Job {job_id} not found"}
        })

    # signal cancel
    JobStatusManager.signal_cancel(job_id)

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
        JobStatusManager.write_json_atomic(status_path, current)
    except Exception as e:
        logger.exception("Failed to mark job cancelled: %s", e)

    # remove any persisted outputs so cancellation leaves no artifacts
    try:
        for fname in ("q_a_summary.json", "overview_summary.json", "summary_evaluation.json"):
            fpath = os.path.join(job_dir, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception as re:
                    logger.exception(
                        "Failed to remove %s for job %s: %s", fname, job_id, re)
    except Exception as e:
        logger.exception("Error during cancelled job cleanup: %s", e)

    return {"ok": True, "job_id": job_id, "status": "cancelled"}
