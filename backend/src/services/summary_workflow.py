import json
from typing import Any, Dict, Optional, Type
import time

from src.llm.llm_utils import summarize_q_a, judge_q_a_summary, write_call_overview
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.services.precheck import run_precheck
from src.config.runtime import CALL_TYPE, SUMMARY_LENGTH, SHORT_Q_A_PROMPT_VERSION, LONG_Q_A_PROMPT_VERSION
from fastapi import UploadFile
from pydantic import ValidationError


class SummaryWorkflowError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def run_summary_workflow(file: UploadFile, call_type: str, summary_length: str):

    blocks = []

    validated_overview = None  # Variable scope

    # Validate PDF

    precheck_result = run_precheck(file=file)
    blocks_list = precheck_result.get("blocks", [])
    if not blocks_list:
        raise SummaryWorkflowError(
            "precheck_error", "No blocks returned from precheck")

    # if blocks exist
    precheck_block = blocks_list[0]
    data = precheck_block.get("data", {})
    qa_transcript = data.get("qa_transcript")
    presentation_transcript = data.get("presentation_transcript")

    if not qa_transcript:

        raise SummaryWorkflowError(
            "precheck_error", f"No Q&A transcript found")

    if summary_length == "short":
        prompt_version = SHORT_Q_A_PROMPT_VERSION
    else:
        prompt_version = LONG_Q_A_PROMPT_VERSION

    try:
        qa_resp = summarize_q_a(
            qa_transcript=qa_transcript,
            call_type=call_type,
            summary_length=summary_length,  # do config
            prompt_version=prompt_version
        )
        # Texto (string JSON) retornado pelo LLM
        summary_metadata = qa_resp.get("metadata", {})
        remaining_tokens = summary_metadata.get("remaining_tokens")

        total_time_sec = (summary_metadata.get("time") or 0)
        qa_summary_obj = qa_resp.get("summary", {}).get("obj")
        qa_summary_text = qa_resp.get(
            "summary", {}).get("text", "Empty summary")
        if not qa_summary_obj:
            raise ValidationError(
                "LLM did not return a parsed Pydantic object for Summary Q&A")

        # if valid :
        block_type = "q_a_short" if summary_length == "short" else "q_a_long"
        blocks.append(
            {
                "type": block_type,
                "metadata": summary_metadata,
                "data": qa_summary_obj.model_dump()
            }
        )

    except ValidationError as e:
        raise SummaryWorkflowError("llm_invalid_json", str(e))
    except Exception as e:
        raise SummaryWorkflowError(
            "llm_summary_error", str(e))  # broader exception

    # 3) Judge and Overview in parallel
    # Backoff ONCE based only on summary remaining tokens with threshold=40k
    def exponential_backoff(remaining: Optional[int], threshold: int):
        if remaining is None:
            return
        if remaining < threshold:
            for attempt in range(3):
                sleep_seconds = 2 ** attempt
                time.sleep(sleep_seconds)
            return

    # MAX TOKENS COMBINED FOR JUDGE AND OVERVIEW
    exponential_backoff(remaining_tokens, 40000)

    results: Dict[str, Any] = {}
    errors: Dict[str, Exception] = {}

    def run_judge():
        return run_judge_workflow(
            version_prompt="version_2",
            qa_transcript=qa_transcript,
            qa_summary=qa_summary_text,
            summary_structure=summary_metadata.get("summary_structure", ""),
        )

    def run_overview():
        return write_call_overview(
            presentation_transcript=presentation_transcript or "The call didn't have a presentation section. Refer to the Q&A summary instead",
            q_a_summary=qa_summary_text,
            call_type=call_type
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_key = {
            executor.submit(run_judge): "judge",
            executor.submit(run_overview): "overview",
        }
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                errors[key] = exc

    # Handle judge result
    if "judge" in results and not isinstance(results.get("judge"), Exception):
        judge_summary_obj, judge_summary_metadata = results["judge"]
        total_time_sec += (judge_summary_metadata.get("time") or 0)
        blocks.append(
            {
                "type": "judge",
                "metadata": judge_summary_metadata,
                "data": judge_summary_obj.model_dump(),
            }
        )
    elif "judge" in errors:
        raise SummaryWorkflowError("llm_judge_error", str(errors["judge"]))

    # Handle overview result
    if "overview" in results and not isinstance(results.get("overview"), Exception):
        ov_resp = results["overview"]
    elif "overview" in errors:
        raise SummaryWorkflowError(
            "llm_overview_error", str(errors["overview"]))
    else:
        ov_resp = None

    # Append overview block
    ov_obj = ov_resp.get("overview", {}).get("obj") if ov_resp else None
    ov_metadata = ov_resp.get("metadata", {}) if ov_resp else {}
    # finalize total_time and attach to overview metadata
    total_time_sec += (ov_metadata.get("time") or 0)
    ov_metadata["total_time"] = round(total_time_sec)
    if not ov_obj:
        raise SummaryWorkflowError(
            "llm_invalid_json", "LLM did not return a parsed Pydantic object for Overview ")

    validated_overview = ov_obj

    blocks.append(
        {
            "type": "overview",
            "metadata": ov_metadata,
            "data": validated_overview.model_dump()
        }
    )

    return {
        "title": validated_overview.title if validated_overview else "Untitled",
        "call_type": call_type,
        "blocks": blocks  
    }


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
