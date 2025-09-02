#    /llm_utils: (all are for earning call and conference) summarize_q_a, judge_q_a_summary, run_overview_workflow

import json
import logging
import os
from src.llm.llm_client import get_llm_client
from typing import Tuple
from src.config.runtime import (
    JUDGE_PROMPT_VERSION,
    OVERVIEW_PROMPT_VERSION,
    EFFORT_LEVEL_Q_A,
    EFFORT_LEVEL_JUDGE,
    EFFORT_LEVEL_Q_A_CONFERENCE,
    EARNINGS_SHORT_Q_A_PROMPT_VERSION,
    EARNINGS_LONG_Q_A_PROMPT_VERSION,
    EARNINGS_SHORT_Q_A_BULLET_PROMPT_VERSION,
    EARNINGS_LONG_Q_A_BULLET_PROMPT_VERSION,
    CONFERENCE_LONG_Q_A_PROMPT_VERSION,
    CONFERENCE_LONG_Q_A_BULLET_PROMPT_VERSION,
    Q_A_MODEL,
    CONFERENCE_Q_A_MODEL
)
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Load JSON prompt files


class PromptConfigError(Exception):
    pass


class LLMGenerationError(Exception):
    pass


# SUMMARIZE OUTPUT FORMAT
class Question(BaseModel):
    question: str
    answer_summary: str


class AnalystQA(BaseModel):
    name: str
    firm: str
    questions: List[Question]


class SummarizeOutputFormat(BaseModel):
    title: str
    analysts: List[AnalystQA]


# BULLET POINT OUTPUT FORMAT
class AnswerByExecutiveBullet(BaseModel):
    executive: str
    answer_summary: List[str]


class QuestionBullet(BaseModel):
    question: str
    # New grouped answers by executive; fallback support handled at render level
    answers: Optional[List[AnswerByExecutiveBullet]] = None
    # Backward-compat: allow plain list of bullet strings
    answer_summary: Optional[List[str]] = None


class AnalystQABullet(BaseModel):
    name: str
    firm: str
    questions: List[QuestionBullet]


class SummarizeOutputFormatBullet(BaseModel):
    title: str
    analysts: List[AnalystQABullet]


# CONFERENCE CALL OUTPUT FORMAT
class Topic(BaseModel):
    topic: str
    question_answers: List[AnalystQA]  # Reuse the same AnalystQA structure


class ConferenceSummarizeOutputFormat(BaseModel):
    title: str
    topics: List[Topic]


# CONFERENCE CALL BULLET POINT OUTPUT FORMAT
class TopicBullet(BaseModel):
    topic: str
    # Reuse the same AnalystQABullet structure
    question_answers: List[AnalystQABullet]


class ConferenceSummarizeOutputFormatBullet(BaseModel):
    title: str
    topics: List[TopicBullet]


# JUDGE OUTPUT FORMAT - Complete schemas for q_a_summary.json output structure


class Error(BaseModel):
    error: str
    summary_text: str
    transcript_text: str


class EvaluationResult(BaseModel):
    metric_name: str
    passed: bool
    errors: List[Error]


class OverallAssessment(BaseModel):
    total_criteria: int
    passed_criteria: int
    failed_criteria: int
    overall_passed: bool
    pass_rate: float
    evaluation_timestamp: str
    evaluation_summary: str


class JudgeOutputFormat(BaseModel):
    evaluation_results: List[EvaluationResult]
    overall_assessment: OverallAssessment


# Overall output format
class Executive(BaseModel):
    executive_name: str
    role: str


class OverviewOutputFormat(BaseModel):
    executives_list: List[Executive]
    overview: str

    class GuidanceItem(BaseModel):
        period_label: str
        metric_name: str
        metric_description: str

    guidance_outlook: Optional[List[GuidanceItem]] = None
   

def load_prompts_summarize():

    config_dir = os.path.join(os.path.dirname(
        os.path.dirname(__file__)), 'config', 'prompts_summarize')

    with open(os.path.join(config_dir, 'short_q_a.json'), 'r', encoding='utf-8') as f:
        short_q_a_prompt = json.load(f)

    with open(os.path.join(config_dir, 'long_q_a.json'), 'r', encoding='utf-8') as f:
        long_q_a_prompt = json.load(f)

    with open(os.path.join(config_dir, 'long_conference.json'), 'r', encoding='utf-8') as f:
        conference_q_a_prompt = json.load(f)

    with open(os.path.join(config_dir, 'overview.json'), 'r', encoding='utf-8') as f:
        overview_prompt = json.load(f)

    # Load bullet point prompts
    with open(os.path.join(config_dir, 'short_q_a_bullet.json'), 'r', encoding='utf-8') as f:
        short_q_a_bullet_prompt = json.load(f)

    with open(os.path.join(config_dir, 'long_q_a_bullet.json'), 'r', encoding='utf-8') as f:
        long_q_a_bullet_prompt = json.load(f)

    with open(os.path.join(config_dir, 'long_conference_bullet.json'), 'r', encoding='utf-8') as f:
        conference_q_a_bullet_prompt = json.load(f)

    return short_q_a_prompt, long_q_a_prompt, overview_prompt, conference_q_a_prompt, short_q_a_bullet_prompt, long_q_a_bullet_prompt, conference_q_a_bullet_prompt


def load_prompts_judge():
    config_dir = os.path.join(os.path.dirname(
        os.path.dirname(__file__)), 'config', 'prompts_judge')

    with open(os.path.join(config_dir, 'q_a_summary.json'), 'r', encoding='utf-8') as f:
        q_a_summary_prompt = json.load(f)

    return q_a_summary_prompt


short_q_a_prompt, long_q_a_prompt, overview_prompt, conference_q_a_prompt, short_q_a_bullet_prompt, long_q_a_bullet_prompt, conference_q_a_bullet_prompt = load_prompts_summarize()
q_a_summary_prompt = load_prompts_judge()

logger = logging.getLogger("llm_utils")


def _ensure_dict(obj, context: str) -> dict:
    if not isinstance(obj, dict):
        raise PromptConfigError(
            f"Expected a dict for {context}, got {type(obj).__name__}")
    return obj


def _require_str(d: dict, key: str, context: str) -> str:
    value = d.get(key)
    if not isinstance(value, str):
        raise PromptConfigError(f"Missing or invalid '{key}' in {context}")
    return value


def _require_params_max_tokens(d: dict, context: str) -> int:
    params = d.get("parameters")
    if not isinstance(params, dict):
        raise PromptConfigError(
            f"Missing or invalid 'parameters' in {context}")
    max_tokens = params.get("max_output_tokens")
    if not isinstance(max_tokens, int):
        raise PromptConfigError(
            f"Missing or invalid 'max_output_tokens' in {context}")
    return max_tokens


def _require_output_structure(d: dict, context: str) -> str:
    structure = d.get("output_structure")
    if not isinstance(structure, dict):
        raise PromptConfigError(
            f"Missing or invalid 'output_structure' in {context}")
    # Ensure JSON-valid preview inside prompt, not Python dict repr
    return json.dumps(structure, ensure_ascii=False)


def get_prompt_config(call_type: str, summary_length: str, answer_format: str = "prose") -> dict:
    """
    Centralized function to determine prompt configuration based on call type, summary length, and answer format.
    Returns a dict with prompt_version, model, and effort_level.
    """
    if call_type.lower() == "conference":
        # Conference calls only have long format
        if answer_format == "bullet":
            prompt_version = CONFERENCE_LONG_Q_A_BULLET_PROMPT_VERSION
        else:
            prompt_version = CONFERENCE_LONG_Q_A_PROMPT_VERSION
        model = CONFERENCE_Q_A_MODEL
        effort_level = EFFORT_LEVEL_Q_A_CONFERENCE
    else:
        # Earnings calls
        if summary_length == "short":
            if answer_format == "bullet":
                prompt_version = EARNINGS_SHORT_Q_A_BULLET_PROMPT_VERSION
            else:
                prompt_version = EARNINGS_SHORT_Q_A_PROMPT_VERSION
        else:
            if answer_format == "bullet":
                prompt_version = EARNINGS_LONG_Q_A_BULLET_PROMPT_VERSION
            else:
                prompt_version = EARNINGS_LONG_Q_A_PROMPT_VERSION
        model = Q_A_MODEL
        effort_level = EFFORT_LEVEL_Q_A

    return {
        "prompt_version": prompt_version,
        "model": model,
        "effort_level": effort_level
    }


def summarize_q_a(qa_transcript: str, call_type: str, summary_length: str, prompt_version: str, model="gpt-5", effort_level=EFFORT_LEVEL_Q_A, text_format=None, answer_format="prose") -> dict:

    logger.info("Calling Summarize Q&A")
    llm_client = get_llm_client(model)

    # Select the appropriate Pydantic model based on call type and answer format
    if text_format is None:
        if call_type == "conference":
            if answer_format == "bullet":
                text_format = ConferenceSummarizeOutputFormatBullet
            else:
                text_format = ConferenceSummarizeOutputFormat
        else:
            if answer_format == "bullet":
                text_format = SummarizeOutputFormatBullet
            else:
                text_format = SummarizeOutputFormat

    # Get prompts
    if call_type == "conference":
        # Conference calls use the long_conference.json file
        if answer_format == "bullet":
            conference_section = _ensure_dict(conference_q_a_bullet_prompt.get(
                "LONG_CONFERENCE_SUMMARY"), "long_conference_bullet.json -> LONG_CONFERENCE_SUMMARY")
        else:
            conference_section = _ensure_dict(conference_q_a_prompt.get(
                "LONG_CONFERENCE_SUMMARY"), "long_conference.json -> LONG_CONFERENCE_SUMMARY")
        prompts = _ensure_dict(conference_section.get(
            prompt_version), f"conference Q&A prompts['{prompt_version}']")

    # Validate prompts formatting
        system_prompt = _require_str(
            prompts, "system_prompt", "conference Q&A prompts")
        user_prompt = _require_str(
            prompts, "user_prompt", "conference Q&A prompts")
        output_structure_json = _require_output_structure(
            prompts, "conference Q&A prompts")
        max_output_tokens = _require_params_max_tokens(
            prompts, "conference Q&A prompts")
        effort_level = EFFORT_LEVEL_Q_A_CONFERENCE

    else:  # for earnig calls
        effort_level = EFFORT_LEVEL_Q_A
        # Earnings calls use short_q_a.json or long_q_a.json based on summary_length
        if summary_length == "short":
            if answer_format == "bullet":
                short_section = _ensure_dict(short_q_a_bullet_prompt.get(
                    "Q_A_SHORT_SUMMARY"), "short_q_a_bullet.json -> Q_A_SHORT_SUMMARY")
            else:
                short_section = _ensure_dict(short_q_a_prompt.get(
                    "Q_A_SHORT_SUMMARY"), "short_q_a.json -> Q_A_SHORT_SUMMARY")
            prompts = _ensure_dict(short_section.get(
                prompt_version), f"short Q&A prompts['{prompt_version}']")

            # Validate prompts formatting
            system_prompt = _require_str(
                prompts, "system_prompt", "short Q&A prompts")
            user_prompt = _require_str(
                prompts, "user_prompt", "short Q&A prompts")
            output_structure_json = _require_output_structure(
                prompts, "short Q&A prompts")
            max_output_tokens = _require_params_max_tokens(
                prompts, "short Q&A prompts")

        elif summary_length == "long":
            if answer_format == "bullet":
                long_section = _ensure_dict(long_q_a_bullet_prompt.get(
                    "Q_A_SUMMARY"), "long_q_a_bullet.json -> Q_A_SUMMARY")
            else:
                long_section = _ensure_dict(long_q_a_prompt.get(
                    "Q_A_SUMMARY"), "long_q_a.json -> Q_A_SUMMARY")

            prompts = _ensure_dict(long_section.get(
                prompt_version), f"long Q&A prompts['{prompt_version}']")
            system_prompt = _require_str(
                prompts, "system_prompt", "long Q&A prompts")
            user_prompt = _require_str(
                prompts, "user_prompt", "long Q&A prompts")
            output_structure_json = _require_output_structure(
                prompts, "long Q&A prompts")
            max_output_tokens = _require_params_max_tokens(
                prompts, "long Q&A prompts")

    processed_user_prompt = user_prompt.format(TRANSCRIPT=qa_transcript)
    processed_system_prompt = system_prompt.format(
        OUTPUT_STRUCTURE=output_structure_json, CALL_TYPE=call_type)

    # error de output eh feito ja no llm client
    llm_response = llm_client.generate(

        system_prompt=processed_system_prompt,
        user_prompt=processed_user_prompt,
        max_output_tokens=max_output_tokens,
        effort_level=effort_level,
        text_format=text_format
    )

    summary_text = llm_response.text  # to pass to jduge llm
    summary_obj = llm_response.parsed

    # Round time to 0 decimals for metadata
    rounded_time = None
    if llm_response.duration_seconds is not None:
        rounded_time = round(llm_response.duration_seconds)
    else:
        rounded_time = None

    metadata = {

        "model": model,
        "summary_length": summary_length,
        "answer_format": answer_format,
        "prompt_version": prompt_version,
        "effort_level": effort_level,
        "summary_structure": json.loads(output_structure_json),
        "call_type": call_type,
        "max_output_tokens": max_output_tokens,
        "input_tokens": llm_response.input_tokens,
        "output_tokens": llm_response.output_tokens,
        "reasoning_tokens": llm_response.reasoning_tokens if model == "gpt-5" else None,
        "finish_reason": llm_response.finish_reason,
        "raw_response": llm_response.raw,  # for debugging
        "remaining_tokens": llm_response.remaining_tokens,
        "time": rounded_time,
    }

    final_output = {
        "summary": {"text": summary_text, "obj": summary_obj},
        "metadata": metadata
    }

    logger.info(f"-------------Q&A SUMMARY FOR {call_type}-------------")
    logger.info(f"Finish reason: {llm_response.finish_reason}")
    logger.debug(f"Raw response: {llm_response.raw}")
    logger.info(
        "----------------------------------------------------------------------")
    logger.info(
        "--------------------------- START OF SUMMARY--------------------------------")
    logger.info(summary_text)
    logger.info(
        "--------------------------- END OF SUMMARY--------------------------------")

    return final_output


def judge_q_a_summary(transcript: str, q_a_summary: str, summary_structure: str, prompt_version: str, model="gpt-5", effort_level=EFFORT_LEVEL_JUDGE, text_format=JudgeOutputFormat) -> dict:

    # logger.info("Calling Judge Q&A Summary")
    llm_client = get_llm_client(model)

    judge_section = _ensure_dict(q_a_summary_prompt.get(
        "Q_A_LLM_JUDGE"), "q_a_summary.json -> Q_A_LLM_JUDGE")
    prompts = _ensure_dict(judge_section.get(
        prompt_version), f"q_a_summary.json -> Q_A_LLM_JUDGE['{prompt_version}']")

    system_prompt = _require_str(prompts, "system_prompt", "judge Q&A prompts")
    user_prompt = _require_str(prompts, "user_prompt", "judge Q&A prompts")
    output_structure_json = _require_output_structure(
        prompts, "judge Q&A prompts")
    max_output_tokens = _require_params_max_tokens(
        prompts, "judge Q&A prompts")

    processed_user_prompt = user_prompt.format(
        TRANSCRIPT=transcript, SUMMARY=q_a_summary, SUMMARY_STRUCTURE=summary_structure)

    processed_system_prompt = system_prompt.format(
        OUTPUT_STRUCTURE=output_structure_json)

    llm_response = llm_client.generate(

        system_prompt=processed_system_prompt,
        user_prompt=processed_user_prompt,
        max_output_tokens=max_output_tokens,
        effort_level=effort_level,
        text_format=text_format
    )

    rounded_time = None
    try:
        if llm_response.duration_seconds is not None:
            rounded_time = round(llm_response.duration_seconds)
    except Exception:
        rounded_time = None

    metadata = {
        "model": model,
        "effort_level": effort_level,
        "prompt_version": prompt_version,
        "max_output_tokens": max_output_tokens,
        "input_tokens": llm_response.input_tokens,
        "output_tokens": llm_response.output_tokens,
        "reasoning_tokens": llm_response.reasoning_tokens if model == "gpt-5" else None,
        "finish_reason": llm_response.finish_reason,
        "raw_response": llm_response.raw,  # for debugging
        "remaining_tokens": llm_response.remaining_tokens,
        "time": rounded_time,
    }

    eval_results_obj = llm_response.parsed
    eval_results_text = llm_response.text

    final_output = {
        "eval_results": {"text": eval_results_text, "obj": eval_results_obj},
        "metadata": metadata
    }

    logger.info("-------------EVALUATION OF Q&A SUMMARY -------------")
    logger.info(f"Finish reason: {llm_response.finish_reason}")
    logger.debug(f"Raw response: {llm_response.raw}")
    logger.info(
        "----------------------------------------------------------------------")
    logger.info(
        "--------------------------- START OF EVALUATION RESULTS --------------------------------")
    logger.info(eval_results_text)
    logger.info(
        "--------------------------- END OF EVALUATION RESULTS --------------------------------")

    return final_output


def run_overview_workflow(presentation_transcript: str, q_a_summary: str, call_type: str, prompt_version=OVERVIEW_PROMPT_VERSION, model="gpt-5-mini", text_format=OverviewOutputFormat) -> dict:

    logger.info("Calling Write Call Overview")
    llm_client = get_llm_client(model)

    overview_section = _ensure_dict(overview_prompt.get(
        "OVERVIEW"), "overview.json -> OVERVIEW")
    write_call_overview_prompts = _ensure_dict(overview_section.get(
        prompt_version), f"overview.json -> OVERVIEW['{prompt_version}']")

    system_prompt = _require_str(
        write_call_overview_prompts, "system_prompt", "overview prompts")
    user_prompt = _require_str(
        write_call_overview_prompts, "user_prompt", "overview prompts")
    output_structure_json = _require_output_structure(
        write_call_overview_prompts, "overview prompts")

    max_output_tokens = _require_params_max_tokens(
        write_call_overview_prompts, "overview prompts")

    processed_system_prompt = system_prompt.format(
        CALL_TYPE=call_type, OUTPUT_STRUCTURE=output_structure_json)
    processed_user_prompt = user_prompt.format(
        TRANSCRIPT=presentation_transcript, Q_A_SUMMARY=q_a_summary)

    llm_response = llm_client.generate(
        system_prompt=processed_system_prompt,
        user_prompt=processed_user_prompt,
        max_output_tokens=max_output_tokens,

        text_format=text_format
    )

    if llm_response.finish_reason == 'length' or llm_response.finish_reason == 'max_tokens':
        logger.error(
            f"Overview generation stopped due to token limit. Finish reason: {llm_response.finish_reason}")

        raise LLMGenerationError(
            f"Overview generation failed: The response was truncated because it reached the maximum token limit of {max_output_tokens}."
        )

    rounded_time = None
    try:
        if llm_response.duration_seconds is not None:
            rounded_time = round(llm_response.duration_seconds)
    except Exception:
        rounded_time = None

    metadata = {
        "model": model,
        "prompt_version": prompt_version,
        "max_output_tokens": max_output_tokens,
        "input_tokens": llm_response.input_tokens,
        "output_tokens": llm_response.output_tokens,
        "reasoning_tokens": llm_response.reasoning_tokens if model == "gpt-5" else None,
        "finish_reason": llm_response.finish_reason,
        "remaining_tokens": llm_response.remaining_tokens,
        "time": rounded_time,
    }

    overview_obj = llm_response.parsed
    overview_text = llm_response.text

    final_output = {
        "overview": {"text": overview_text, "obj": overview_obj},
        "metadata": metadata
    }

    logger.info(f"-------------CALL OVERVIEW FOR {call_type}-------------")
    logger.info(f"Finish reason: {llm_response.finish_reason}")
    logger.debug(f"Raw response: {llm_response.raw}")
    logger.info(
        "----------------------------------------------------------------------")
    logger.info(
        "--------------------------- START OF CALL OVERVIEW --------------------------------")
    logger.info(overview_text)
    logger.info(
        "--------------------------- END OF CALL OVERVIEW --------------------------------")

    return final_output
