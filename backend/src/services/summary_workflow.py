import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from typing import Any, Dict, Optional, Tuple
from pydantic import ValidationError

from src.config.constants import CACHE_DIR
from src.llm.llm_utils import (
    get_prompt_config,
    judge_q_a_summary,
    run_overview_workflow,
    summarize_q_a,
)
# Import the manager and helpers from their new, shared location
from src.utils.job_state import JobStatusManager, Stage, Status

logger = logging.getLogger("summary_workflow")

PARALLEL_TIMEOUT_SECONDS = 5 * 60

# --- Custom Exception ---


class SummaryWorkflowError(Exception):
    """Custom exception for workflow-specific errors."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

# --- Core Workflow Logic ---


def run_summary_workflow_from_saved_transcripts(
    transcript_name: str,
    call_type: str,
    summary_length: str,
    job_dir: Optional[str] = None,
    cancel_event: Optional[threading.Event] = None,
    answer_format: str = "prose",
) -> Dict[str, Any]:
    """
    Executes the summary workflow by orchestrating distinct stages.
    """
    job_manager = JobStatusManager(job_dir)
    blocks: list[dict[str, Any]] = []
    total_time_sec = 0.0

    try:
        #Fetch transcripts from local cache
        qa_transcript, presentation_transcript = _load_transcripts(
            transcript_name)

        #Configuring prompt
        prompt_config = get_prompt_config(
            call_type, summary_length, answer_format)

        # Early cancellation check
        if cancel_event and cancel_event.is_set():
            job_manager.fail_job("cancelled", "User cancelled before start")
            return {"title": "Untitled", "call_type": call_type, "blocks": blocks or []}

        # Summarize Q&A
        qa_block, qa_summary_text, summary_metadata, time_taken = _execute_qa_summary(
            qa_transcript=qa_transcript,
            prompt_config=prompt_config,
            job_manager=job_manager,
            summary_length=summary_length,
            answer_format=answer_format,
            call_type=call_type
        )
        blocks.append(qa_block)
        total_time_sec += time_taken

        # Mid-workflow cancellation check
        if cancel_event and cancel_event.is_set():
            job_manager.set_stage_status(Stage.OVERVIEW, Status.FAILED)
            job_manager.set_stage_status(Stage.JUDGE, Status.FAILED)
            job_manager.fail_job(
                "cancelled", "User cancelled after Q&A summary")
            return {"title": "Untitled", "call_type": call_type, "blocks": blocks or []}

        # exponential backoff if reach rate limit
        _apply_exponential_backoff(summary_metadata.get("remaining_tokens"))

        # Call Overview and Judge Stages in Parallel
        parallel_blocks, parallel_time_sec = _execute_parallel_stages(
            qa_transcript=qa_transcript,
            presentation_transcript=presentation_transcript,
            qa_summary_text=qa_summary_text,
            summary_metadata=summary_metadata,
            call_type=call_type,
            job_manager=job_manager,
            cancel_event=cancel_event
        )
        blocks.extend(parallel_blocks)
        total_time_sec += parallel_time_sec

    except SummaryWorkflowError as e:
        logger.error(f"Workflow failed with code {e.code}: {e.message}")
        job_manager.fail_job(e.code, e.message)
        return {"title": "Untitled", "call_type": call_type, "blocks": blocks or []}

    # Mark job complete
    if job_manager.is_job_complete():
        job_manager.update_status({
            "current_stage": "completed",
            "percent_complete": 100
        })

    # Find the title from the overview block if it exists
    title = "Untitled"
    for block in blocks:
        if block.get("type") == "overview":
            title = block.get("data", {}).get("title", "Untitled")
            block["metadata"]["total_time"] = round(total_time_sec)
            break

    return {"title": title, "call_type": call_type, "blocks": blocks}

# --- Helper Functions for Workflow Stages ---


def _load_transcripts(transcript_name: str) -> Tuple[str, str]:
    """Loads Q&A and presentation transcripts from a JSON file."""
    json_path = os.path.join(CACHE_DIR, transcript_name)
    if not os.path.exists(json_path):
        raise SummaryWorkflowError(
            "precheck_error", f"Transcript JSON not found: {json_path}")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
    except Exception as e:
        raise SummaryWorkflowError(
            "precheck_error", f"Failed to load transcripts: {e}")

    transcripts = saved.get("transcripts", {})
    qa_transcript = transcripts.get("q_a") or ""
    presentation_transcript = transcripts.get("presentation") or ""

    if not qa_transcript:
        raise SummaryWorkflowError("precheck_error", "No Q&A transcript found")

    return qa_transcript, presentation_transcript


def _execute_qa_summary(**kwargs) -> Tuple[Dict, str, Dict, float]:
    """Runs the Q&A summarization, handles its errors, and updates job status."""
    job_manager: JobStatusManager = kwargs["job_manager"]
    job_manager.update_status({
        "current_stage": Stage.QA_SUMMARY.value,
        "stages": {Stage.QA_SUMMARY.value: Status.RUNNING.value},
        "percent_complete": 25,
    })

    try:
        qa_resp = summarize_q_a(
            qa_transcript=kwargs["qa_transcript"],
            call_type=kwargs["call_type"],
            summary_length=kwargs["summary_length"],
            prompt_version=kwargs["prompt_config"]["prompt_version"],
            model=kwargs["prompt_config"]["model"],
            effort_level=kwargs["prompt_config"]["effort_level"],
            answer_format=kwargs["answer_format"],
        )

        summary_metadata = qa_resp.get("metadata", {})
        qa_summary_obj = qa_resp.get("summary", {}).get("obj")
        if not qa_summary_obj:
            raise ValidationError(
                "LLM did not return a parsed Pydantic object for Summary Q&A")

        qa_summary_text = qa_resp.get(
            "summary", {}).get("text", "Empty summary")

        if job_manager.has_job_directory:
            payload = {"metadata": _format_for_json(
                summary_metadata), "data": qa_summary_obj.model_dump()}
            JobStatusManager.write_json_atomic(os.path.join(
                job_manager.job_dir, "q_a_summary.json"), payload)

        job_manager.update_status({
            "stages": {Stage.QA_SUMMARY.value: Status.COMPLETED.value},
            "percent_complete": 55,
        })

        block_type = "q_a_short" if kwargs["summary_length"] == "short" else "q_a_long"
        qa_block = {
            "type": block_type,
            "metadata": summary_metadata,
            "data": qa_summary_obj.model_dump(),
        }
        time_taken = summary_metadata.get("time", 0.0)

        return qa_block, qa_summary_text, summary_metadata, time_taken

    except ValidationError as e:
        job_manager.set_stage_status(Stage.QA_SUMMARY, Status.FAILED)
        job_manager.add_warning("Q&A summary failed: invalid JSON from LLM")
        raise SummaryWorkflowError("llm_invalid_json", str(e))
    except Exception as e:
        job_manager.set_stage_status(Stage.QA_SUMMARY, Status.FAILED)
        job_manager.add_warning(f"Q&A summary failed: {e}")
        raise SummaryWorkflowError("llm_summary_error", str(e))


def _execute_parallel_stages(**kwargs) -> Tuple[list, float]:
    """Runs overview and judge workflows concurrently."""
    job_manager: JobStatusManager = kwargs["job_manager"]
    cancel_event: Optional[threading.Event] = kwargs["cancel_event"]

    completed_blocks = []
    total_time_sec = 0.0

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_stage = {
            executor.submit(_run_overview_task, **kwargs): Stage.OVERVIEW,
            executor.submit(_run_judge_task, **kwargs): Stage.JUDGE,
        }

        try:
            for future in as_completed(future_to_stage, timeout=PARALLEL_TIMEOUT_SECONDS):
                stage = future_to_stage[future]

                if cancel_event and cancel_event.is_set():
                    future.cancel()
                    job_manager.set_stage_status(stage, Status.FAILED)
                    continue

                try:
                    block, time_taken = future.result()
                    if block:
                        completed_blocks.append(block)
                    total_time_sec += time_taken
                    job_manager.set_stage_status(stage, Status.COMPLETED)
                except Exception as e:
                    logger.exception(
                        f"Parallel stage '{stage.value}' failed: {e}")
                    job_manager.set_stage_status(stage, Status.FAILED)
                    job_manager.add_warning(
                        f"Stage '{stage.value}' failed: {e}")
        except FutureTimeoutError:
            logger.error("Parallel stage processing timed out.")
            for future, stage in future_to_stage.items():
                if not future.done():
                    future.cancel()
                    job_manager.set_stage_status(stage, Status.FAILED)
                    job_manager.add_warning(
                        f"Stage '{stage.value}' timed out after {PARALLEL_TIMEOUT_SECONDS}s")

    return completed_blocks, total_time_sec


def _run_overview_task(**kwargs) -> Tuple[Optional[Dict], float]:
    """Task wrapper for running the overview workflow."""
    job_manager: JobStatusManager = kwargs["job_manager"]
    job_manager.update_status({"current_stage": Stage.OVERVIEW.value, "stages": {
                              Stage.OVERVIEW.value: Status.RUNNING.value}})

    resp = run_overview_workflow(
        presentation_transcript=kwargs["presentation_transcript"] or "No presentation section.",
        q_a_summary=kwargs["qa_summary_text"],
        call_type=kwargs["call_type"],
    )

    ov_obj = resp.get("overview", {}).get("obj")
    metadata = resp.get("metadata", {})
    time_taken = metadata.get("time", 0.0)

    if ov_obj:
        block = {"type": "overview", "metadata": metadata,
                 "data": ov_obj.model_dump()}
        if job_manager.has_job_directory:
            payload = {"metadata": _format_for_json(
                metadata), "data": ov_obj.model_dump()}
            JobStatusManager.write_json_atomic(os.path.join(
                job_manager.job_dir, "overview_summary.json"), payload)
        return block, time_taken
    return None, time_taken


def _run_judge_task(**kwargs) -> Tuple[Optional[Dict], float]:
    """Task wrapper for running the judge workflow."""
    job_manager: JobStatusManager = kwargs["job_manager"]
    job_manager.update_status({"current_stage": Stage.JUDGE.value, "stages": {
                              Stage.JUDGE.value: Status.RUNNING.value}})

    try:
        judge_resp = judge_q_a_summary(
            transcript=kwargs["qa_transcript"],
            q_a_summary=kwargs["qa_summary_text"],
            summary_structure=kwargs["summary_metadata"].get(
                "summary_structure", {}),
            prompt_version="version_2"
        )
        judge_obj = judge_resp.get("eval_results", {}).get("obj")
        if not judge_obj:
            raise ValidationError(
                "LLM did not return a parsed Pydantic object for Judge")

        metadata = judge_resp.get("metadata", {})
        time_taken = metadata.get("time", 0.0)

        block = {"type": "judge", "metadata": metadata,
                 "data": judge_obj.model_dump()}
        if job_manager.has_job_directory:
            payload = {"metadata": _format_for_json(
                metadata), "data": judge_obj.model_dump()}
            JobStatusManager.write_json_atomic(os.path.join(
                job_manager.job_dir, "summary_evaluation.json"), payload)

        return block, time_taken

    except Exception as e:
        # Catching a broad exception here to wrap it for the parallel executor
        raise SummaryWorkflowError("llm_judge_error", str(e))

# --- Utility Functions ---


def _apply_exponential_backoff(remaining_tokens: Optional[int], threshold: int = 40000):
    """Waits if remaining tokens are below a threshold to avoid rate limiting."""
    if remaining_tokens is not None and remaining_tokens < threshold:
        logger.info(f"Token count {remaining_tokens} is low, pausing briefly.")
        time.sleep(5)


# Local JSON sanitizer for metadata payloads
def _format_for_json(obj: Dict[str, Any]) -> Dict[str, Any]:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        safe: Dict[str, Any] = {}
        for k, v in (obj or {}).items():
            try:
                json.dumps(v)
                safe[k] = v
            except Exception:
                safe[k] = str(v)
        return safe
