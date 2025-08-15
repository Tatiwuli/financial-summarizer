import json
from typing import Any, Dict
from src.llm.llm_response_processor import LlmSummaryValidationError, map_short_q_a, map_long_q_a, map_judge, map_overview
from src.llm.llm_utils import summarize_q_a, judge_q_a_summary, write_call_overview
from src.services.precheck import run_precheck
from src.config.runtime import CALL_TYPE, SUMMARY_LENGTH, SHORT_Q_A_PROMPT_VERSION, LONG_Q_A_PROMPT_VERSION
from datetime import datetime


class SummaryWorkflowError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _ensure_dict(text_or_dict: Any) -> Dict[str, Any]:
    """Aceita string JSON ou dict; retorna dict ou levanta erro."""
    if isinstance(text_or_dict, dict):
        return text_or_dict
    if isinstance(text_or_dict, str):
        s = text_or_dict.strip()
        # remove cerquilha de bloco de código se vier
        if s.startswith("```"):
            s = s.strip("`")
            if s.lower().startswith("json"):
                s = s[4:].strip()
        return json.loads(s)
    # não aceitamos outros tipos
    raise SummaryWorkflowError(
        "llm_invalid_json", "Saída do LLM não é JSON válido.")


def run_summary_workflow():

    blocks = []

    # Check pdf processor
    precheck_result = run_precheck()

    precheck_block = precheck_result.get("blocks")[0]

    q_a_transcript = precheck_block.get("data").get("qa_transcript")
    presentation_transcript = precheck_block.get(
        "data").get("presentation_transcript")

    call_type = CALL_TYPE
    summary_length = SUMMARY_LENGTH

    if summary_length == "short":
        prompt_version = SHORT_Q_A_PROMPT_VERSION
    else:
        prompt_version = LONG_Q_A_PROMPT_VERSION

    # erros dos outputs ja sao tratados no llm client

    try:
        qa_resp = summarize_q_a(
            q_a_transcript=q_a_transcript,
            call_type=call_type,
            summary_length=summary_length,  # do config
            prompt_version=prompt_version
        )
        # Texto (string JSON) retornado pelo LLM
        qa_summary_raw = qa_resp.get("summary")

        qa_summary_metadata = qa_resp.get("metadata", {})

        # valida output de json
        qa_summary_json = _ensure_dict(qa_summary_raw)
        
        # mapa para o bloco
        if summary_length == "short":
            blocks.append(map_short_q_a(qa_summary_json))

        else:
            blocks.append(map_long_q_a(qa_summary_json))

    except LlmSummaryValidationError as e:
        raise SummaryWorkflowError("llm_invalid_json", str(e))
    except json.JSONDecodeError as e:
        raise SummaryWorkflowError(
            "llm_invalid_json", f"JSON inválido do LLM (Q&A): {e}")
    except Exception as e:
        # erro técnico (client, rate limit, etc.)
        raise SummaryWorkflowError(
            "llm_summary_error", f"Falha ao gerar Q&A: {e}")

    # 3) JUDGE (obrigatório e sempre após Q&A)

    try:
        judge_resp = judge_q_a_summary(
            transcript=q_a_transcript,
            q_a_summary=qa_summary_raw,        # passe o MESMO texto que o summarize gerou
            summary_structure=qa_summary_metadata.get("summary_structure")
        )
        judge_text_raw = judge_resp.get("eval_results")

        judge_result_json = _ensure_dict(judge_text_raw)

        blocks.append(map_judge(judge_result_json))
        

    except LlmSummaryValidationError as e:
        raise SummaryWorkflowError("llm_invalid_json", f"Judge inválido: {e}")
    except json.JSONDecodeError as e:
        raise SummaryWorkflowError(
            "llm_invalid_json", f"JSON inválido do LLM (Judge): {e}")
    except Exception as e:
        raise SummaryWorkflowError(
            "llm_judge_error", f"Falha ao avaliar Q&A: {e}")

    # 4) OVERVIEW (obrigatório)

  #  write_call_overview(presentation_transcript: str, q_a_summary: str, call_type: str, prompt_version=OVERVIEW_PROMPT_VERSION, model="gpt-5-mini")
    try:
        ov_resp = write_call_overview(
            # teu util já trata vazio com string custom
            presentation_transcript=presentation_transcript or "The call didn't have a presentation section. Refer to the Q&A summary instead",
            q_a_summary=qa_summary_raw,
            call_type=call_type
        )
        ov_text_raw = ov_resp.get("overview")

        ov_json = _ensure_dict(ov_text_raw)

        blocks.append(map_overview(ov_json))
    except LlmSummaryValidationError as e:
        # overview é obrigatório → paramos
        raise SummaryWorkflowError(
            "llm_invalid_json", f"Overview inválido: {e}")
    except json.JSONDecodeError as e:
        raise SummaryWorkflowError(
            "llm_invalid_json", f"JSON inválido do LLM (Overview): {e}")
    except Exception as e:
        raise SummaryWorkflowError(
            "llm_overview_error", f"Falha ao gerar overview: {e}")

    meta = precheck_result.get("meta", {}).copy()

    meta["generated_at"] = datetime.utcnow().isoformat()
    return {
        "title": ov_json["title"],
        "call_type": call_type,
        "blocks": blocks,   # ordem: q_a_* → judge → overview
        "meta": meta
    }
