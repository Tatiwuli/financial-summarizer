#    /llm_utils: (all are for earning call and conference) summarize_q_a, judge_q_a_summary, write_call_overview

import json
import os
from llm_client import get_llm_client
from typing import Tuple
from src.config.runtime import LONG_Q_A_PROMPT_VERSION, JUDGE_PROMPT_VERSION, OVERVIEW_PROMPT_VERSION

# Load JSON prompt files

class PromptConfigError(Exception):
    pass
class LLMGenerationError(Exception):
    pass

def load_prompts_summarize():
   
    config_dir = os.path.join(os.path.dirname(
        os.path.dirname(__file__)), 'config', 'prompts_summarize')


    with open(os.path.join(config_dir, 'short_q_a.json'), 'r') as f:
        short_q_a_prompt = json.load(f)

    with open(os.path.join(config_dir, 'long_q_a.json'), 'r') as f:
        long_q_a_prompt = json.load(f)

    with open(os.path.join(config_dir, 'overview.json'), 'r') as f:
        overview_prompt = json.load(f)

    return short_q_a_prompt, long_q_a_prompt, overview_prompt


def load_prompts_judge():
    config_dir = os.path.join(os.path.dirname(
        os.path.dirname(__file__)), 'config', 'prompts_judge')

    with open(os.path.join(config_dir, 'q_a_summary.json'), 'r') as f:
        q_a_summary_prompt = json.load(f)

    return q_a_summary_prompt


short_q_a_prompt, long_q_a_prompt, overview_prompt = load_prompts_summarize()
q_a_summary_prompt = load_prompts_judge()


def summarize_q_a(q_a_transcript: str, call_type: str, summary_length: str, prompt_version:str, model ="gpt-5") -> dict:

    print("Calling Summarize Q&A")
    llm_client = get_llm_client(model)

    if summary_length == "short":
        short_q_a_prompts = short_q_a_prompt.get(
            "Q_A_SHORT_SUMMARY").get(prompt_version)

        system_prompt = short_q_a_prompts.get("system_prompt")
        user_prompt = short_q_a_prompts.get("user_prompt")
        output_structure = short_q_a_prompts.get("output_structure")
        max_output_tokens = short_q_a_prompts.get(
            "parameters").get("max_output_tokens")

    elif summary_length == "long":
        long_q_a_prompts = long_q_a_prompt.get(
            "Q_A_SUMMARY").get(prompt_version)
        system_prompt = long_q_a_prompts.get("system_prompt")
        user_prompt = long_q_a_prompts.get("user_prompt")
        output_structure = long_q_a_prompts.get("output_structure")
        max_output_tokens = long_q_a_prompts.get(
            "parameters").get("max_output_tokens")

    processed_user_prompt = user_prompt.format(TRANSCRIPT=q_a_transcript)
    processed_system_prompt = system_prompt.format(
        OUTPUT_STRUCTURE=output_structure, CALL_TYPE=call_type)

    #error de output eh feito ja no llm client
    llm_response = llm_client.generate(

        system_prompt=processed_system_prompt,
        user_prompt=processed_user_prompt,
        max_output_tokens=max_output_tokens
    )

    metadata = {
        "model": model,
        "summary_length": summary_length,
        "prompt_version": prompt_version,
        "summary_structure": output_structure,
        "call_type": call_type,
        "input_tokens": llm_response.input_tokens,
        "output_tokens": llm_response.output_tokens,
        "finish_reason": llm_response.finish_reason,
    }

    summary = llm_response.text

    final_output = {
        "summary": summary,
        "metadata": metadata
    }

    print(f"-------------Q&A SUMMARY FOR {call_type}-------------")
    print(metadata)
    print(f"---------------------------SUMMARY--------------------------------")
    print(summary)
    print(f"---------------------------SUMMARY--------------------------------")

    return final_output


def judge_q_a_summary(transcript: str, q_a_summary: str, summary_structure: str, prompt_version = JUDGE_PROMPT_VERSION, model="gpt-5") -> dict:

    print("Calling Judge Q&A Summary")
    llm_client = get_llm_client(model)

    judge_q_a_summary_prompts = q_a_summary_prompt.get(
        "Q_A_LLM_JUDGE").get(prompt_version)

    system_prompt = judge_q_a_summary_prompts.get("system_prompt")
    user_prompt = judge_q_a_summary_prompts.get("user_prompt")
    output_structure = judge_q_a_summary_prompts.get("output_structure")
    max_output_tokens = judge_q_a_summary_prompts.get(
        "parameters").get("max_output_tokens")

    processed_user_prompt = user_prompt.format(
        TRANSCRIPT=transcript, SUMMARY=q_a_summary, SUMMARY_STRUCTURE=summary_structure)

    processed_system_prompt = system_prompt.format(
        OUTPUT_STRUCTURE=output_structure)

    llm_response = llm_client.generate(
        system_prompt=processed_system_prompt,
        user_prompt=processed_user_prompt,
        max_output_tokens=max_output_tokens
    )

    metadata = {
        "model": model,
        "prompt_version": prompt_version,
        "input_tokens": llm_response.input_tokens,
        "output_tokens": llm_response.output_tokens,
        "finish_reason": llm_response.finish_reason,
    }

    eval_results = llm_response.text

    final_output = {
        "eval_results": eval_results,
        "metadata": metadata
    }

    print(f"-------------EVALUATION OF Q&A SUMMARY -------------")
    print(metadata)
    print(f"---------------------------EVALUATION RESULTS --------------------------------")
    print(eval_results)
    print(f"---------------------------EVALUATION RESULTS --------------------------------")

    return final_output


def write_call_overview(presentation_transcript: str, q_a_summary: str, call_type: str, prompt_version=OVERVIEW_PROMPT_VERSION, model="gpt-5-mini") -> dict:

    print("Calling Write Call Overview")
    llm_client = get_llm_client(model)

    write_call_overview_prompts = overview_prompt.get(
        "OVERVIEW").get(prompt_version)

    system_prompt = write_call_overview_prompts.get("system_prompt")
    user_prompt = write_call_overview_prompts.get("user_prompt")
    output_structure = write_call_overview_prompts.get("output_structure")
    max_output_tokens = write_call_overview_prompts.get(
        "parameters").get("max_output_tokens")

    processed_system_prompt = system_prompt.format(CALL_TYPE=call_type, OUTPUT_STRUCTURE=output_structure)
    processed_user_prompt = user_prompt.format(TRANSCRIPT=presentation_transcript, Q_A_SUMMARY=q_a_summary)

    llm_response = llm_client.generate(
        system_prompt=processed_system_prompt,
        user_prompt=processed_user_prompt,
        max_output_tokens=max_output_tokens
    )

    metadata = {
        "model": model,
        "prompt_version": prompt_version,
        "input_tokens": llm_response.input_tokens,
        "output_tokens": llm_response.output_tokens,
        "finish_reason": llm_response.finish_reason,
    }

    overview = llm_response.text

    final_output = {        
        "overview": overview,
        "metadata": metadata
    }

    print(f"-------------CALL OVERVIEW FOR {call_type}-------------")
    print(metadata)
    print(f"---------------------------CALL OVERVIEW --------------------------------")
    print(overview)
    print(f"---------------------------CALL OVERVIEW --------------------------------")

    return final_output


# summary_output = summarize_q_a(q_a_transcript="", call_type="conference call", model="gpt-5-mini",
#               summary_length="short", prompt_version="version_1")

# judge_q_a_summary(transcript="", q_a_summary=summary_output.get("summary"), summary_structure= summary_output.get("metadata").get("summary_structure"),
#                   prompt_version="version_1", model="gpt-5-mini")

summary_output= {
    "summary": "No transcript provided",
    "metadata": {
        "summary_structure": "No summary structure provided"
    }
}


write_call_overview(presentation_transcript="", q_a_summary=summary_output.get("summary"), prompt_version="version_1", call_type="conference call", model="gpt-5-mini")

