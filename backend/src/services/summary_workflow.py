import json
from typing import Any, Dict, Optional, Type
from src.llm.llm_utils import summarize_q_a, judge_q_a_summary, write_call_overview
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
    all_metadata = {}
    validated_overview = None  # Variable scope

    # Validate PDF

    precheck_result = run_precheck(file=file)
    blocks_list = precheck_result.get("blocks", [])
    if not blocks_list:
        raise SummaryWorkflowError(
            "precheck_error", "No blocks returned from precheck")

    #if blocks exist 
    precheck_block = blocks_list[0]
    data = precheck_block.get("data", {})
    qa_transcript = data.get("qa_transcript")
    presentation_transcript = data.get("presentation_transcript")

    if not qa_transcript:
    
        raise SummaryWorkflowError("precheck_error", f"No Q&A transcript found")



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
        qa_summary_obj = qa_resp.get("summary", {}).get("obj")
        qa_summary_text = qa_resp.get("summary", {}).get("text", "Empty summary")
        if not qa_summary_obj:
            raise ValidationError(
                "LLM did not return a parsed Pydantic object for Summary Q&A")

        # if valid :
        block_type = "q_a_short" if summary_length == "short" else "q_a_long"
        blocks.append(
            {
                "type": block_type,
                "data": qa_summary_obj.model_dump()
            }
        )

        all_metadata["summary_metadata"] = all_metadata.get(
            "summary_metadata", {})
        all_metadata["summary_metadata"].update(summary_metadata)

    except ValidationError as e:
        raise SummaryWorkflowError("llm_invalid_json", str(e))
    except Exception as e:
        raise SummaryWorkflowError(
            "llm_summary_error", str(e))  # broader exception

    # 3) JUDGE (obrigatório e sempre após Q&A)

    try:
        judge_resp = judge_q_a_summary(
            transcript=qa_transcript,
            q_a_summary=qa_summary_text,    # passe o MESMO texto que o summarize gerou
            summary_structure=summary_metadata.get("summary_structure")
        )

        # Convert the Pydantic model to dict format expected by map_judge
        # Transform list-based evaluation_results to dict-based format
        judge_summary_obj = judge_resp.get("eval_results", {}).get("obj")
        judge_summary_metadata = judge_resp.get("metadata", {})
        if not judge_summary_obj:
            raise ValidationError(
                "LLM did not return a parsed Pydantic object for Judge")

        blocks.append(
            {
                "type": "judge",
                "data": judge_summary_obj.model_dump()
            }
        )

        all_metadata["judge_metadata"] = all_metadata.get("judge_metadata", {})
        all_metadata["judge_metadata"].update(judge_summary_metadata)

    except ValidationError as e:
        raise SummaryWorkflowError("llm_invalid_json", str(e))
    except Exception as e:
        raise SummaryWorkflowError("llm_judge_error", str(e))

    # 4) OVERVIEW (obrigatório)
    try:
        ov_resp = write_call_overview(
            # teu util já trata vazio com string custom
            presentation_transcript=presentation_transcript or "The call didn't have a presentation section. Refer to the Q&A summary instead",
            q_a_summary=qa_summary_text,
            call_type=call_type
        )

        ov_obj = ov_resp.get("overview", {}).get("obj")

        ov_metadata = ov_resp.get("metadata", {})
        if not ov_obj:
            raise ValidationError(
                "LLM did not return a parsed Pydantic object for Overview ")

        validated_overview = ov_obj

        blocks.append(
            {
                "type": "overview",
                "data": validated_overview.model_dump()
            }
        )

        all_metadata["overview_metadata"] = all_metadata.get(
            "overview_metadata", {})
        all_metadata["overview_metadata"].update(ov_metadata)

    except ValidationError as e:
        raise SummaryWorkflowError("llm_invalid_json", str(e))

    except Exception as e:
        raise SummaryWorkflowError("llm_overview_error", str(e))

    return {
        "title": validated_overview.title if validated_overview else "Untitled",
        "call_type": call_type,
        "blocks": blocks,   # ordem: q_a_* → judge → overvie
        "meta": all_metadata
    }
