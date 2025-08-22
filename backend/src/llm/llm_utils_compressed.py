import os
import json
from typing import Optional, Type

from pydantic import BaseModel

from llmlingua import PromptCompressor

from src.llm.llm_client import get_llm_client
from src.config.runtime import (
    EFFORT_LEVEL_Q_A,
    EFFORT_LEVEL_JUDGE,
    LONG_Q_A_PROMPT_VERSION,
    JUDGE_PROMPT_VERSION,
    OVERVIEW_PROMPT_VERSION,
)
from src.llm.llm_utils import (
    SummarizeOutputFormat,
    JudgeOutputFormat,
    OverviewOutputFormat,
    load_prompts_summarize,
    load_prompts_judge,
)


# Load prompt configs (reuse the same loaders to ensure parity)
short_q_a_prompt, long_q_a_prompt, overview_prompt = load_prompts_summarize()
q_a_summary_prompt = load_prompts_judge()


_COMPRESSOR = None


def _get_compressor() -> PromptCompressor:
    global _COMPRESSOR
    if _COMPRESSOR is not None:
        return _COMPRESSOR

    model_name = os.getenv(
        "LLMLINGUA_MODEL",
        "microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
    )
    use_llmlingua2 = os.getenv(
        "LLMLINGUA2", "true").lower() in ("1", "true", "yes")

    # Force CPU where possible
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

    try:
        # Some versions accept device_map
        _COMPRESSOR = PromptCompressor(
            model_name=model_name,
            use_llmlingua2=use_llmlingua2,
            device_map="cpu",  # type: ignore
        )
        return _COMPRESSOR
    except TypeError:
        pass
    except AssertionError:
        pass

    _COMPRESSOR = PromptCompressor(
        model_name=model_name,
        use_llmlingua2=use_llmlingua2,
    )
    return _COMPRESSOR


def _compress_system_prompt(step: str, system_prompt: str) -> str:
    rate_env = os.getenv("LLMLINGUA_RATE", "0.5")
    try:
        rate = float(rate_env)
    except Exception:
        rate = 0.5

    print(f"[LLMLingua] Step: {step}")
    comp = _get_compressor()

    supports_vis = True
    supports_rate = True
    result = None

    # First attempt: rate + return_vis
    try:
        result = comp.compress_prompt(
            system_prompt,
            rate=rate,
            return_vis=True,
        )
    except TypeError as e:
        msg = str(e).lower()
        if "return_vis" in msg or "unexpected keyword" in msg:
            supports_vis = False
        if "rate" in msg:
            supports_rate = False

    # If first attempt failed, try again with adjusted kwargs
    if result is None:
        kwargs = {}
        if supports_rate:
            kwargs["rate"] = rate
        else:
            est_tokens = max(64, int(len(system_prompt) / 4))
            kwargs["target_token"] = est_tokens
        if supports_vis:
            kwargs["return_vis"] = True
        try:
            result = comp.compress_prompt(system_prompt, **kwargs)
        except TypeError as e:
            # Final fallback: remove vis and use target_token
            est_tokens = max(64, int(len(system_prompt) / 4))
            try:
                result = comp.compress_prompt(
                    system_prompt, target_token=est_tokens)
            except Exception as e2:
                print(f"[LLMLingua] Compression failed: {e2}")
                return system_prompt
        except Exception as e:
            print(f"[LLMLingua] Compression failed: {e}")
            return system_prompt

    compressed = result.get("compressed_prompt", "") or system_prompt
    origin_tokens = result.get("origin_tokens")
    compressed_tokens = result.get("compressed_tokens")
    ratio = result.get("ratio")

    # Visualization availability depends on version
    vis = None
    if supports_vis:
        vis = result.get("vis") or result.get("visualization")

    print("[LLMLingua] Compression Summary:")
    print(f"  - origin_tokens     : {origin_tokens}")
    print(f"  - compressed_tokens : {compressed_tokens}")
    print(f"  - ratio             : {ratio}")
    print("[LLMLingua] Compressed Prompt (first 400 chars):")
    print(compressed[:400])
    if vis is not None:
        try:
            print("[LLMLingua] Dropped Tokens Visualization:")
            print(json.dumps(vis, ensure_ascii=False)[:2000])
        except Exception:
            print("[LLMLingua] (vis) present but not JSON serializable for preview")
    elif supports_vis is False:
        print("[LLMLingua] Visualization not supported in this installed version.")
    print("-")

    return compressed


def summarize_q_a(
    qa_transcript: str,
    call_type: str,
    summary_length: str,
    prompt_version: str,
    model: str = "gpt-5",
    effort_level: Optional[str] = EFFORT_LEVEL_Q_A,
    text_format: Optional[Type[BaseModel]] = SummarizeOutputFormat,
) -> dict:

    print("Calling Summarize Q&A (compressed system prompt)")
    llm_client = get_llm_client(model)

    if summary_length == "short":
        short_q_a_prompts = short_q_a_prompt.get(
            "Q_A_SHORT_SUMMARY").get(prompt_version)
        system_prompt = short_q_a_prompts.get("system_prompt")
        user_prompt = short_q_a_prompts.get("user_prompt")
        output_structure = short_q_a_prompts.get("output_structure")
        max_output_tokens = short_q_a_prompts.get(
            "parameters").get("max_output_tokens")
    else:
        long_q_a_prompts = long_q_a_prompt.get(
            "Q_A_SUMMARY").get(prompt_version)
        system_prompt = long_q_a_prompts.get("system_prompt")
        user_prompt = long_q_a_prompts.get("user_prompt")
        output_structure = long_q_a_prompts.get("output_structure")
        max_output_tokens = long_q_a_prompts.get(
            "parameters").get("max_output_tokens")

    processed_user_prompt = user_prompt.format(TRANSCRIPT=qa_transcript)
    processed_system_prompt = system_prompt.format(
        OUTPUT_STRUCTURE=output_structure, CALL_TYPE=call_type
    )

    compressed_system_prompt = _compress_system_prompt(
        step="Q&A Summary", system_prompt=processed_system_prompt
    )

    llm_response = llm_client.generate(
        system_prompt=compressed_system_prompt,
        user_prompt=processed_user_prompt,
        max_output_tokens=max_output_tokens,
        effort_level=effort_level,
        text_format=text_format,
    )

    summary_text = llm_response.text
    summary_obj = llm_response.parsed

    rounded_time = round(
        llm_response.duration_seconds) if llm_response.duration_seconds is not None else None

    metadata = {
        "model": model,
        "summary_length": summary_length,
        "prompt_version": prompt_version,
        "effort_level": effort_level,
        "summary_structure": output_structure,
        "call_type": call_type,
        "max_output_tokens": max_output_tokens,
        "input_tokens": llm_response.input_tokens,
        "output_tokens": llm_response.output_tokens,
        "reasoning_tokens": llm_response.reasoning_tokens if model == "gpt-5" else None,
        "finish_reason": llm_response.finish_reason,
        "raw_response": llm_response.raw,
        "remaining_tokens": llm_response.remaining_tokens,
        "time": rounded_time,
    }

    final_output = {
        "summary": {"text": summary_text, "obj": summary_obj},
        "metadata": metadata,
    }

    print(f"-------------Q&A SUMMARY FOR {call_type}-------------")
    print("Finish reason: ", llm_response.finish_reason)
    print("Raw response: ", llm_response.raw)
    print("----------------------------------------------------------------------")
    print(f"--------------------------- START OF SUMMARY--------------------------------")
    print(summary_text)
    print(f"--------------------------- END OF SUMMARY--------------------------------")

    return final_output


def judge_q_a_summary(
    transcript: str,
    q_a_summary: str,
    summary_structure: str,
    prompt_version: str,
    model: str = "gpt-5",
    effort_level: Optional[str] = EFFORT_LEVEL_JUDGE,
    text_format: Optional[Type[BaseModel]] = JudgeOutputFormat,
) -> dict:

    llm_client = get_llm_client(model)

    judge_q_a_summary_prompts = q_a_summary_prompt.get(
        "Q_A_LLM_JUDGE").get(prompt_version)
    system_prompt = judge_q_a_summary_prompts.get("system_prompt")
    user_prompt = judge_q_a_summary_prompts.get("user_prompt")
    output_structure = judge_q_a_summary_prompts.get("output_structure")
    max_output_tokens = judge_q_a_summary_prompts.get(
        "parameters").get("max_output_tokens")

    processed_user_prompt = user_prompt.format(
        TRANSCRIPT=transcript, SUMMARY=q_a_summary, SUMMARY_STRUCTURE=summary_structure
    )
    processed_system_prompt = system_prompt.format(
        OUTPUT_STRUCTURE=output_structure)

    compressed_system_prompt = _compress_system_prompt(
        step="Judge Q&A Summary", system_prompt=processed_system_prompt
    )

    llm_response = llm_client.generate(
        system_prompt=compressed_system_prompt,
        user_prompt=processed_user_prompt,
        max_output_tokens=max_output_tokens,
        effort_level=effort_level,
        text_format=text_format,
    )

    rounded_time = round(
        llm_response.duration_seconds) if llm_response.duration_seconds is not None else None

    metadata = {
        "model": model,
        "effort_level": effort_level,
        "prompt_version": prompt_version,
        "max_output_tokens": max_output_tokens,
        "input_tokens": llm_response.input_tokens,
        "output_tokens": llm_response.output_tokens,
        "reasoning_tokens": llm_response.reasoning_tokens if model == "gpt-5" else None,
        "finish_reason": llm_response.finish_reason,
        "raw_response": llm_response.raw,
        "remaining_tokens": llm_response.remaining_tokens,
        "time": rounded_time,
    }

    eval_results_obj = llm_response.parsed
    eval_results_text = llm_response.text

    final_output = {
        "eval_results": {"text": eval_results_text, "obj": eval_results_obj},
        "metadata": metadata,
    }

    print(f"-------------EVALUATION OF Q&A SUMMARY -------------")
    print("Finish reason: ", llm_response.finish_reason)
    print("Raw response: ", llm_response.raw)
    print("----------------------------------------------------------------------")
    print(f"--------------------------- START OF EVALUATION RESULTS --------------------------------")
    print(eval_results_text)
    print(f"--------------------------- END OF EVALUATION RESULTS --------------------------------")

    return final_output


def write_call_overview(
    presentation_transcript: str,
    q_a_summary: str,
    call_type: str,
    prompt_version: str = OVERVIEW_PROMPT_VERSION,
    model: str = "gpt-5-mini",
    text_format: Optional[Type[BaseModel]] = OverviewOutputFormat,
) -> dict:

    print("Calling Write Call Overview (compressed system prompt)")
    llm_client = get_llm_client(model)

    write_call_overview_prompts = overview_prompt.get(
        "OVERVIEW").get(prompt_version)
    system_prompt = write_call_overview_prompts.get("system_prompt")
    user_prompt = write_call_overview_prompts.get("user_prompt")
    output_structure = write_call_overview_prompts.get("output_structure")
    max_output_tokens = write_call_overview_prompts.get(
        "parameters").get("max_output_tokens")

    processed_system_prompt = system_prompt.format(
        CALL_TYPE=call_type, OUTPUT_STRUCTURE=output_structure
    )
    processed_user_prompt = user_prompt.format(
        TRANSCRIPT=presentation_transcript, Q_A_SUMMARY=q_a_summary
    )

    compressed_system_prompt = _compress_system_prompt(
        step="Write Call Overview", system_prompt=processed_system_prompt
    )

    llm_response = llm_client.generate(
        system_prompt=compressed_system_prompt,
        user_prompt=processed_user_prompt,
        max_output_tokens=max_output_tokens,
        text_format=text_format,
    )

    rounded_time = round(
        llm_response.duration_seconds) if llm_response.duration_seconds is not None else None

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
        "metadata": metadata,
    }

    print(f"-------------CALL OVERVIEW FOR {call_type}-------------")
    print("Finish reason: ", llm_response.finish_reason)
    print("Raw response: ", llm_response.raw)
    print("----------------------------------------------------------------------")
    print(f"--------------------------- START OF CALL OVERVIEW --------------------------------")
    print(overview_text)
    print(f"--------------------------- END OF CALL OVERVIEW --------------------------------")

    return final_output
