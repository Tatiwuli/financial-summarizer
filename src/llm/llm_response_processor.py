from typing import Dict, Any, List


class LlmSummaryValidationError(Exception):
    pass


def map_short_q_a(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Validação mínima (gate de parada)
    if not isinstance(payload, dict):
        raise LlmSummaryValidationError(
            "short_q_a: payload não é objeto JSON.")
    title = payload.get("title")
    rows = payload.get("questions-answer")
    if not title or not isinstance(rows, list) or len(rows) == 0:
        raise LlmSummaryValidationError(
            "short_q_a: campos obrigatórios ausentes.")

    # Mantemos a estrutura original no bloco.data
    return {
        "type": "q_a_short",
        "data": payload
    }


def map_long_q_a(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise LlmSummaryValidationError("long_q_a: payload não é objeto JSON.")
    title = payload.get("title")
    analysts = payload.get("analysts")
    if not title or not isinstance(analysts, list) or len(analysts) == 0:
        raise LlmSummaryValidationError(
            "long_q_a: campos obrigatórios ausentes.")

    return {
        "type": "q_a_long",
        "data": payload
    }


def map_overview(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise LlmSummaryValidationError("overview: payload não é objeto JSON.")
    # Campos esperados pela sua prompt de overview
    if not payload.get("title") or payload.get("overview") is None:
        raise LlmSummaryValidationError(
            "overview: campos obrigatórios ausentes.")

    return {
        "type": "overview",
        "data": payload
    }


class LlmSummaryValidationError(Exception):
    pass


def map_judge(payload: Dict[str, Any]) -> Dict[str, Any]:
    # payload deve ser o JSON do judge já parseado
    if not isinstance(payload, dict):
        raise LlmSummaryValidationError("judge: payload não é objeto JSON.")

    evaluation_results = payload.get("evaluation_results")
    overall_assessment = payload.get("overall_assessment")
    if not isinstance(evaluation_results, dict) or not isinstance(overall_assessment, dict):
        raise LlmSummaryValidationError(
            "judge: campos obrigatórios ausentes (evaluation_results/overall_assessment).")

    required_criteria = [
        "factuality",
        "metric_accuracy",
        "question_accuracy",
        "metric_specificity",
        "question_completedness",
        "question_grouping",
        "answer_completedness",
    ]

    # Cada critério deve conter passed (bool) e errors (lista)
    for key in required_criteria:
        criterion = evaluation_results.get(key)
        if not isinstance(criterion, dict):
            raise LlmSummaryValidationError(
                f"judge: critério '{key}' inválido (não é objeto).")

        if "passed" not in criterion or not isinstance(criterion["passed"], bool):
            # >>> o campo é booleano (true/false). Se vier string, invalida.
            raise LlmSummaryValidationError(
                f"judge: critério '{key}'.passed deve ser booleano.")

        errors = criterion.get("errors", [])
        if errors is None:
            errors = []
        if not isinstance(errors, list):
            raise LlmSummaryValidationError(
                f"judge: critério '{key}'.errors deve ser lista.")
        # valida formato dos erros quando existirem
        for i, err in enumerate(errors):
            if not isinstance(err, dict):
                raise LlmSummaryValidationError(
                    f"judge: critério '{key}'.errors[{i}] deve ser objeto.")
            # campos básicos — se quiser relaxar, remova alguma exigência
            for field in ("error", "summary_text", "transcript_text"):
                if field not in err or not isinstance(err[field], str):
                    raise LlmSummaryValidationError(
                        f"judge: critério '{key}'.errors[{i}].{field} deve ser string."
                    )

        # normaliza ‘errors’ de volta (se estava None)
        criterion["errors"] = errors

    # overall_assessment
    if "overall_passed" not in overall_assessment :
        raise LlmSummaryValidationError(
            "judge: overall_assessment.overall_passed deve ser booleano.")

    def _to_int_or_raise(field: str):
        val = overall_assessment.get(field, None)
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        if isinstance(val, str) and val.strip().isdigit():
            return int(val.strip())
        if val is None:
            return None  # permitir ausência se o prompt não obrigar
        raise LlmSummaryValidationError(
            f"judge: overall_assessment.{field} deve ser número inteiro ou string numérica.")

    for k in ("total_criteria", "passed_criteria", "failed_criteria"):
        overall_assessment[k] = _to_int_or_raise(k)

    return {"type": "judge", "data": payload}
