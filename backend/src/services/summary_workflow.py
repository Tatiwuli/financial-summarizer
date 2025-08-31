from src.services.job_utils import _get_lock_for_job
import json
from typing import Any, Dict, Optional, Type
import threading
import time
import os
import logging


from src.llm.llm_utils import summarize_q_a, judge_q_a_summary, run_overview_workflow
from src.config.runtime import (
    EARNINGS_SHORT_Q_A_PROMPT_VERSION,
    EARNINGS_LONG_Q_A_PROMPT_VERSION,

    CONFERENCE_LONG_Q_A_PROMPT_VERSION,
    EFFORT_LEVEL_Q_A,
    EFFORT_LEVEL_Q_A_CONFERENCE,
    Q_A_MODEL,
    CONFERENCE_Q_A_MODEL,
    TRANSCRIPTS_DIR
)

from pydantic import ValidationError
import threading

logger = logging.getLogger("summary_workflow")


class SummaryWorkflowError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def run_summary_workflow_from_saved_transcripts(transcript_name: str, call_type: str, summary_length: str, job_dir: Optional[str] = None, cancel_event: Optional[threading.Event] = None):
    """
    Execute the summary workflow using transcripts previously saved by validation

    """

    #  Load transcripts from saved JSON
    json_path = os.path.join(TRANSCRIPTS_DIR, transcript_name)
    if not os.path.exists(json_path):
        raise SummaryWorkflowError(
            "precheck_error", f"Transcript JSON not found: {json_path}")
    # load transcripts
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

    blocks: list[dict[str, Any]] = []
    validated_overview = None

    # Determine prompt version and model based on call type

    if call_type.lower() == "conference":
        if summary_length == "long":
            prompt_version = CONFERENCE_LONG_Q_A_PROMPT_VERSION
        else:
            print("Conference doesn't have a short version. Defaulting to long")
            prompt_version = CONFERENCE_LONG_Q_A_PROMPT_VERSION
        model = CONFERENCE_Q_A_MODEL
        effort_level = EFFORT_LEVEL_Q_A_CONFERENCE
    else:
        #    Default to earnings settings for unknown call types
        if summary_length == "short":
            prompt_version = EARNINGS_SHORT_Q_A_PROMPT_VERSION
        else:
            prompt_version = EARNINGS_LONG_Q_A_PROMPT_VERSION
        model = Q_A_MODEL
        effort_level = EFFORT_LEVEL_Q_A

    # If jobs_dir exists , record status
    # After validation , the q_a summary is running
    if job_dir:
        _update_status(job_dir, {
            "current_stage": "q_a_summary",
            "stages": {"q_a_summary": "running"},
            "updated_at": _now(),
            "percent_complete": 25,
        })

    # Early cancel check before Q&A
    if cancel_event is not None and cancel_event.is_set():
        if job_dir:
            _update_status(job_dir, {
                "current_stage": "failed",
                "updated_at": _now(),
                "error": {"code": "cancelled", "message": "User cancelled before start"},
            })
        return {
            "title": "Untitled",
            "call_type": call_type,
            "blocks": [],
        }

    # Run Q&A summary
    try:
        qa_resp = summarize_q_a(
            qa_transcript=qa_transcript,
            call_type=call_type,
            summary_length=summary_length,
            prompt_version=prompt_version,
            model=model,
            effort_level=effort_level,
        )

        # Get and organize the responses
        summary_metadata = qa_resp.get("metadata", {})
        remaining_tokens = summary_metadata.get("remaining_tokens")
        # Get the time it took to generate the summary
        total_time_sec = (summary_metadata.get("time") or 0)

        qa_summary_obj = qa_resp.get("summary", {}).get("obj")
        qa_summary_text = qa_resp.get(
            "summary", {}).get("text", "Empty summary")
        if not qa_summary_obj:  # Verification for frontend
            raise ValidationError(
                "LLM did not return a parsed Pydantic object for Summary Q&A")

        # Wrap the Q&A summary in a block
        block_type = "q_a_short" if summary_length == "short" else "q_a_long"
        qa_block = {
            "type": block_type,
            "metadata": summary_metadata,
            "data": qa_summary_obj.model_dump(),
        }
        blocks.append(qa_block)

        # Persist Q&A JSON atomically; if it fails, mark failed and stop
        if job_dir:
            ok = _write_json_atomic(
                os.path.join(job_dir, "q_a_summary.json"),
                {
                    "metadata": _format_for_json(summary_metadata),
                    "data": qa_summary_obj.model_dump(),
                },
            )
            if not ok:
                _update_status(job_dir, {
                    "stages": {"q_a_summary": "failed"},
                    "current_stage": "failed",
                    "updated_at": _now(),
                    "percent_complete": 25,
                    "error": {"code": "persist_error", "message": "Failed to write q_a_summary.json. Check the error logs on Render and retrieve the summary from the project folder"},
                })
                _append_warning(
                    job_dir, "Failed to save the Q&A summary output to the project folder")
                return {
                    "title": "Untitled",
                    "call_type": call_type,
                    "blocks": blocks,
                }

            # if success
            _update_status(job_dir, {
                "stages": {"q_a_summary": "completed"},
                "current_stage": "overview_summary",
                "updated_at": _now(),
                "percent_complete": 55,
            })
    except ValidationError as e:

        # If Q&A stage fails, mark it as failed and finalize job as failed
        if job_dir:
            _update_status(job_dir, {
                "stages": {"q_a_summary": "failed"},
                "current_stage": "failed",
                "updated_at": _now(),
                "percent_complete": 25,  # entire workflow fail, stopped in pdf validation
                "error": {"code": "llm_invalid_json", "message": str(e)},
            })
            _append_warning(
                job_dir, "Q&A summary failed: invalid JSON from LLM")
        raise SummaryWorkflowError("llm_invalid_json", str(e))
    except Exception as e:
        if job_dir:
            _update_status(job_dir, {
                "stages": {"q_a_summary": "failed"},
                "current_stage": "failed",
                "updated_at": _now(),
                "percent_complete": 25,
                "error": {"code": "llm_summary_error", "message": str(e)},
            })
            _append_warning(job_dir, f"Q&A summary failed: {str(e)}")
        raise SummaryWorkflowError("llm_summary_error", str(e))

    # Early cancel check before judge/overview
    if cancel_event is not None and cancel_event.is_set():
        if job_dir:
            _update_status(job_dir, {
                "current_stage": "failed",
                "stages": {"overview_summary": "failed", "summary_evaluation": "failed"},
                "updated_at": _now(),
                "error": {"code": "cancelled", "message": "Cancelled by user"},
            })
        return {
            "title": "Untitled",
            "call_type": call_type,
            "blocks": blocks,
        }

    # Check if the remaining tokens is less than the threshold for overview and judge. If it's less, do a exponential backoff
    def exponential_backoff(remaining: Optional[int], threshold: int):
        if remaining is None:
            return
        if remaining < threshold:
            for attempt in range(3):
                sleep_seconds = 2 ** attempt
                time.sleep(sleep_seconds)
            return

    exponential_backoff(remaining_tokens, 40000)

    results: Dict[str, Any] = {}
    errors: Dict[str, Exception] = {}

    # Run judge and update the status
    def run_judge():
        if job_dir:
            _update_status(job_dir, {
                "stages": {"summary_evaluation": "running"},
                "percent_complete": 55,
                "current_stage": "summary_evaluation",

                "updated_at": _now(),
            })
        return run_judge_workflow(
            version_prompt="version_2",
            qa_transcript=qa_transcript,
            qa_summary=qa_summary_text,
            summary_structure=summary_metadata.get("summary_structure") or {},
        )

    # Run overview and update the status
    def run_overview():
        if job_dir:
            _update_status(job_dir, {
                "stages": {"overview_summary": "running"},
                "updated_at": _now(),
            })
        return run_overview_workflow(
            presentation_transcript=presentation_transcript or "The call didn't have a presentation section. Refer to the Q&A summary instead",
            q_a_summary=qa_summary_text,
            call_type=call_type,
        )

    # Run judge and overview in parallel and write outputs as each completes
    from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
    timeout_seconds = 4 * 60
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_key = {
            executor.submit(run_judge): "judge",
            executor.submit(run_overview): "overview",
        }

        pending = set(future_to_key.keys())
        while pending:
            # If user cancels while the parallel tasks are running, break the while loop
            if cancel_event is not None and cancel_event.is_set():
                for fut in list(pending):
                    try:
                        fut.cancel()
                    except Exception:
                        pass
                    pending.remove(fut)
                break

            # If it's timeout, break the while loop
            time_left = timeout_seconds - (time.time() - start_time)
            if time_left <= 0:
                break

            # If none of the above, Run the parallel tasks
            try:
                for future in as_completed(list(pending), timeout=time_left):
                    key = future_to_key[future]
                    pending.remove(future)
                    try:
                        result_value = future.result()
                        results[key] = result_value
                        if key == "judge":  # if judge is completed
                            judge_summary_obj, judge_summary_metadata = result_value
                            total_time_sec += (judge_summary_metadata.get("time") or 0)
                            blocks.append({
                                "type": "judge",
                                "metadata": judge_summary_metadata,
                                "data": judge_summary_obj.model_dump(),
                            })
                            if job_dir:
                                # record the output
                                _write_json_atomic(os.path.join(job_dir, "summary_evaluation.json"), {
                                    "metadata": _format_for_json(judge_summary_metadata),
                                    "data": judge_summary_obj.model_dump(),
                                })
                                _update_status(job_dir, {
                                    "stages": {"summary_evaluation": "completed"},

                                    "updated_at": _now(),
                                })
                        elif key == "overview":  # if overview is completed
                            ov_resp = result_value
                            ov_obj = ov_resp.get("overview", {}).get(
                                "obj") if ov_resp else None
                            ov_metadata = ov_resp.get(
                                "metadata", {}) if ov_resp else {}
                            total_time_sec += (ov_metadata.get("time") or 0)
                            ov_metadata["total_time"] = round(total_time_sec)
                            # record the output
                            if ov_obj:
                                validated_overview = ov_obj
                                overview_block = {
                                    "type": "overview",
                                    "metadata": ov_metadata,
                                    "data": validated_overview.model_dump(),
                                }
                                blocks.append(overview_block)
                                if job_dir:
                                    _write_json_atomic(os.path.join(job_dir, "overview_summary.json"), {
                                        "metadata": _format_for_json(ov_metadata),
                                        "data": validated_overview.model_dump(),
                                    })
                                    _update_status(job_dir, {
                                        "stages": {"overview_summary": "completed"},
                                        "updated_at": _now(),
                                    })
                            else:
                                validated_overview = None
                    except Exception as exc:  # if the overview, judge tasks fail. Don't raise error, but record and inform the user
                        errors[key] = exc
                        if key == "judge":  # if judge fails
                            logger.exception(
                                "[summary_workflow] Judge generation failed: %s", exc)
                            if job_dir:
                                _update_status(job_dir, {
                                    "stages": {"summary_evaluation": "failed"},
                                    "updated_at": _now(),
                                })
                                from concurrent.futures import TimeoutError as _CFTimeout
                                if isinstance(exc, _CFTimeout):  # if judge timed out
                                    _append_warning(
                                        job_dir, "Judge timed out after 4 minutes")
                                else:
                                    _append_warning(
                                        job_dir, f"Judge failed: {str(exc)}")
                        elif key == "overview":
                            logger.exception(
                                "[summary_workflow] Overview generation failed: %s", exc)
                            if job_dir:
                                _update_status(job_dir, {
                                    "stages": {"overview_summary": "failed"},
                                    "updated_at": _now(),
                                })
                                from concurrent.futures import TimeoutError as _CFTimeout
                                if isinstance(exc, _CFTimeout):
                                    _append_warning(
                                        job_dir, "Overview timed out after 4 minutes")
                                else:
                                    _append_warning(
                                        job_dir, f"Overview failed: {str(exc)}")
            except TimeoutError:
                break

        # Handle any still-pending futures as timeouts or cancellation
        for future in pending:
            key = future_to_key[future]
            try:
                future.cancel()
            except Exception:
                pass
            if cancel_event is not None and cancel_event.is_set():
                errors[key] = Exception("Cancelled")
                if key == "judge" and job_dir:
                    _update_status(job_dir, {
                        "stages": {"summary_evaluation": "failed"},
                        "updated_at": _now(),
                    })
                if key == "overview" and job_dir:
                    _update_status(job_dir, {
                        "stages": {"overview_summary": "failed"},
                        "updated_at": _now(),
                    })
            else:
                errors[key] = TimeoutError(
                    f"Stage '{key}' timed out after {timeout_seconds}s")
                if key == "judge" and job_dir:
                    _update_status(job_dir, {
                        "stages": {"summary_evaluation": "failed"},
                        "updated_at": _now(),
                    })
                    _append_warning(job_dir, "Judge timed out after 4 minutes")
                if key == "overview" and job_dir:
                    _update_status(job_dir, {
                        "stages": {"overview_summary": "failed"},
                        "updated_at": _now(),
                    })
                    _append_warning(
                        job_dir, "Overview timed out after 4 minutes")

    # Finalize job if Q&A is completed and overview/judge are terminal (completed or failed)
    if job_dir:
        status_snapshot = _read_status(job_dir)
        stages = status_snapshot.get("stages", {})
        # q_a status is completed
        qa_done = stages.get("q_a_summary") == "completed"

        ov_terminal = stages.get("overview_summary") in ("completed", "failed")
        judge_terminal = stages.get(
            "summary_evaluation") in ("completed", "failed")
        # If cancelled, mark job as failed
        if status_snapshot.get("current_stage") == "cancelled":
            _update_status(job_dir, {
                "current_stage": "failed",
                "updated_at": _now(),
            })
            return  # return empty dict since it's cancelled

         # Overview and judge are 'terminal' when the task has finalized either because it was completed or failed. When they failed, we just render Q&A

        if qa_done and ov_terminal and judge_terminal:
            _update_status(job_dir, {
                "current_stage": "completed",
                "percent_complete": 100,
                "updated_at": _now(),
            })

    return {
        "title": validated_overview.title if validated_overview else "Untitled",
        "call_type": call_type,
        "blocks": blocks,
    }


# ---------------- Persistence helpers ----------------

def _write_json_atomic(path: str, data: Dict[str, Any]) -> bool:
    """
    Writes the data to the json file by replacing entirely the  old one
    """
    try:
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp_path, path)
        return True
    except Exception as e:
        logger.exception(
            "[summary_workflow] Failed to atomically write %s: %s", path, e)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return False


def _format_for_json(obj: Dict[str, Any]) -> Dict[str, Any]:
    # Remove or convert any non-serializable fields from metadata
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


def _read_status(job_dir: str) -> Dict[str, Any]:
    status_path = os.path.join(job_dir, "status.json")
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(
            "[summary_workflow] Failed to read status.json for job_dir=%s path=%s: %s", job_dir, status_path, e)
        return {}


def _update_status(job_dir: str, updates: Dict[str, Any]):
    status = _read_status(job_dir)
    job_id = os.path.basename(job_dir)
    status_lock = _get_lock_for_job(job_id)
    with status_lock:
        # Merge naive
        for k, v in updates.items():
            if k == "stages" and isinstance(v, dict):
                status.setdefault("stages", {}).update(v)
            else:
                status[k] = v
        ok = _write_json_atomic(os.path.join(job_dir, "status.json"), status)
        if not ok:
            logger.error(
                "[summary_workflow] Failed to update status.json for job_id=%s with updates=%s", job_id, updates)


def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat()


def _append_warning(job_dir: str, message: str):
    status = _read_status(job_dir)
    warnings = status.get("warnings") or []
    if not isinstance(warnings, list):
        warnings = [str(warnings)]
    warnings.append(message)
    status["warnings"] = warnings
    _write_json_atomic(os.path.join(job_dir, "status.json"), status)


def run_judge_workflow(version_prompt: str, qa_transcript: str, qa_summary: str, summary_structure: str):

    if not qa_transcript:

        raise SummaryWorkflowError(
            "precheck_error", f"No Q&A transcript found")

    try:
        judge_resp = judge_q_a_summary(
            transcript=qa_transcript,
            q_a_summary=qa_summary,    # passe o MESMO texto que o summarize gerou
            summary_structure=summary_structure,
            prompt_version=version_prompt
        )

        # Convert the Pydantic model to dict format expected by map_judge
        # Transform list-based evaluation_results to dict-based format
        judge_summary_obj = judge_resp.get("eval_results", {}).get("obj")
        judge_summary_metadata = judge_resp.get("metadata", {})
        if not judge_summary_obj:
            raise ValidationError(
                "LLM did not return a parsed Pydantic object for Judge")

        print("--------------------------------")
        print("Version: ", version_prompt)
        print("JUDGE OUTPUT: ")
        print(judge_summary_obj)
        print()
        print("JUDGE METADATA: ")
        print(judge_summary_metadata)
        return judge_summary_obj, judge_summary_metadata

    except ValidationError as e:
        raise SummaryWorkflowError("llm_invalid_json", str(e))
    except Exception as e:
        raise SummaryWorkflowError("llm_judge_error", str(e))
# ------------------------------OLD CODE--------------------------------
# def run_summary_workflow(file: UploadFile, call_type: str, summary_length: str):

#     blocks = []

#     validated_overview = None  # Variable scope

#     # Validate PDF

#     precheck_result = run_validate_file(file=file)
#     blocks_list = precheck_result.get("blocks", [])
#     if not blocks_list:
#         raise SummaryWorkflowError(
#             "precheck_error", "No blocks returned from precheck")

#     # if blocks exist
#     precheck_block = blocks_list[0]
#     data = precheck_block.get("data", {})
#     qa_transcript = data.get("qa_transcript")
#     presentation_transcript = data.get("presentation_transcript")

#     if not qa_transcript:

#         raise SummaryWorkflowError(
#             "precheck_error", f"No Q&A transcript found")

#     if summary_length == "short":
#         prompt_version = SHORT_Q_A_PROMPT_VERSION
#     else:
#         prompt_version = LONG_Q_A_PROMPT_VERSION

#     try:
#         qa_resp = summarize_q_a(
#             qa_transcript=qa_transcript,
#             call_type=call_type,
#             summary_length=summary_length,  # do config
#             prompt_version=prompt_version
#         )
#         # Texto (string JSON) retornado pelo LLM
#         summary_metadata = qa_resp.get("metadata", {})
#         remaining_tokens = summary_metadata.get("remaining_tokens")

#         total_time_sec = (summary_metadata.get("time") or 0)
#         qa_summary_obj = qa_resp.get("summary", {}).get("obj")
#         qa_summary_text = qa_resp.get(
#             "summary", {}).get("text", "Empty summary")
#         if not qa_summary_obj:
#             raise ValidationError(
#                 "LLM did not return a parsed Pydantic object for Summary Q&A")

#         # if valid :
#         block_type = "q_a_short" if summary_length == "short" else "q_a_long"
#         blocks.append(
#             {
#                 "type": block_type,
#                 "metadata": summary_metadata,
#                 "data": qa_summary_obj.model_dump()
#             }
#         )

#     except ValidationError as e:
#         raise SummaryWorkflowError("llm_invalid_json", str(e))
#     except Exception as e:
#         raise SummaryWorkflowError(
#             "llm_summary_error", str(e))  # broader exception

#     # 3) Judge and Overview in parallel
#     # Backoff ONCE based only on summary remaining tokens with threshold=40k
#     def exponential_backoff(remaining: Optional[int], threshold: int):
#         if remaining is None:
#             return
#         if remaining < threshold:
#             for attempt in range(3):
#                 sleep_seconds = 2 ** attempt
#                 time.sleep(sleep_seconds)
#             return

#     # MAX TOKENS COMBINED FOR JUDGE AND OVERVIEW
#     exponential_backoff(remaining_tokens, 40000)

#     results: Dict[str, Any] = {}
#     errors: Dict[str, Exception] = {}

#     def run_judge():
#         return run_judge_workflow(
#             version_prompt="version_2",
#             qa_transcript=qa_transcript,
#             qa_summary=qa_summary_text,
#             summary_structure=summary_metadata.get("summary_structure", ""),
#         )

#     def run_overview():
#         return run_overview_workflow(
#             presentation_transcript=presentation_transcript or "The call didn't have a presentation section. Refer to the Q&A summary instead",
#             q_a_summary=qa_summary_text,
#             call_type=call_type
#         )

#     with ThreadPoolExecutor(max_workers=2) as executor:
#         future_to_key = {
#             executor.submit(run_judge): "judge",
#             executor.submit(run_overview): "overview",
#         }
#         for future in as_completed(future_to_key):
#             key = future_to_key[future]
#             try:
#                 results[key] = future.result()
#             except Exception as exc:
#                 errors[key] = exc

#     # Handle judge result (allow partial success)
#     if "judge" in results and not isinstance(results.get("judge"), Exception):
#         judge_summary_obj, judge_summary_metadata = results["judge"]
#         total_time_sec += (judge_summary_metadata.get("time") or 0)
#         blocks.append(
#             {
#                 "type": "judge",
#                 "metadata": judge_summary_metadata,
#                 "data": judge_summary_obj.model_dump(),
#             }
#         )
#     else:
#         if "judge" in errors:
#             # Log and proceed (partial success mode)
#             print("[SUMMARY_WORKFLOW] Judge generation failed:", errors["judge"])
#     # elif "judge" in errors:  COMMENTED OUT - Try partial success
#     #     raise SummaryWorkflowError("llm_judge_error", str(errors["judge"]))

#     # Handle overview result
#     if "overview" in results and not isinstance(results.get("overview"), Exception):
#         ov_resp = results["overview"]
#     # elif "overview" in errors:
#     #     raise SummaryWorkflowError(
#     #         "llm_overview_error", str(errors["overview"])) COMMENTED OUT - try partial success
#     else:
#         if "overview" in errors:
#             # Log and proceed (partial success mode)
#             print("[SUMMARY_WORKFLOW] Overview generation failed:",
#                   errors["overview"])
#         ov_resp = None

#     # Append overview block
#     ov_obj = ov_resp.get("overview", {}).get("obj") if ov_resp else None
#     ov_metadata = ov_resp.get("metadata", {}) if ov_resp else {}
#     # finalize total_time and attach to overview metadata
#     total_time_sec += (ov_metadata.get("time") or 0)
#     ov_metadata["total_time"] = round(total_time_sec)
#     if ov_obj:
#         validated_overview = ov_obj
#         blocks.append(
#             {
#                 "type": "overview",
#                 "metadata": ov_metadata,
#                 "data": validated_overview.model_dump()
#             }
#         )
#     else:
#         validated_overview = None

#     return {
#         "title": validated_overview.title if validated_overview else "Untitled",
#         "call_type": call_type,
#         "blocks": blocks
#     }
