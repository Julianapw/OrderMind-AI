import json
import logging
from datetime import datetime
from pathlib import Path

from app.services.order_analysis import analyze_order_issue
from app.tools.order_lookup import get_order_by_id


logger = logging.getLogger(__name__)

CASES = [
    {
        "name": "missing_item",
        "order_id": "PED-1001",
        "customer_message": "Meu pedido chegou sem as batatas fritas.",
    },
    {
        "name": "late_delivery",
        "order_id": "PED-1001",
        "customer_message": "Meu pedido chegou atrasado.",
    },
    {
        "name": "unknown_reason",
        "order_id": "PED-1001",
        "customer_message": "Quero saber por que meu pedido foi cancelado.",
    },
    {
        "name": "order_preparing",
        "order_id": "PED-1002",
        "customer_message": (
            "Meu pedido está demorando muito. Quando vai chegar?"
        ),
    },
    {
        "name": "order_delivered",
        "order_id": "PED-1003",
        "customer_message": "Meu pedido ainda não chegou.",
    },
]


API_ERROR_TERMS = (
    "429",
    "resource_exhausted",
    "quota exceeded",
    "rate limit",
    "too many requests",
    "unavailable",
    "service unavailable",
    "deadline_exceeded",
    "deadline expired",
    "timed out",
    "timeout",
    "503",
    "504",
)


def classify_execution_error(error: Exception) -> str:
    """Classify provider errors without exposing them as successful analyses."""
    message = str(error).lower()

    if any(
        term in message
        for term in (
            "429",
            "resource_exhausted",
            "quota exceeded",
            "rate limit",
            "too many requests",
        )
    ):
        return "api_quota_error"

    if any(
        term in message
        for term in (
            "deadline_exceeded",
            "deadline expired",
            "timed out",
            "timeout",
            "504",
        )
    ):
        return "api_timeout"

    if any(
        term in message
        for term in (
            "unavailable",
            "service unavailable",
            "503",
        )
    ):
        return "api_unavailable"

    if any(term in message for term in API_ERROR_TERMS):
        return "api_error"

    return "execution_error"


def analysis_to_text(analysis) -> str:
    """Convert structured analysis into text for keyword-based evaluation."""
    if isinstance(analysis, str):
        return analysis

    fields = [
        *getattr(analysis, "confirmed_facts", []),
        *getattr(analysis, "evidence", []),
        getattr(analysis, "complaint_assessment", ""),
        getattr(analysis, "recommended_next_step", ""),
        *getattr(analysis, "missing_information", []),
    ]

    return "\n".join(str(field) for field in fields if field)


def evaluate_response(response: str) -> dict:
    """Check for uncertainty acknowledgement and a suggested next step."""
    text = response.lower()

    uncertainty_terms = [
        "não é possível confirmar",
        "não permitem confirmar",
        "não há informação",
        "não temos informação",
        "não é possível verificar",
        "não permitem verificar",
        "precisa ser verificado",
        "recomenda-se verificar",
        "não comprov",
        "não há registro",
        "não contêm",
        "não contém",
        "não estão disponíveis",
        "informações disponíveis",
        "evidências disponíveis",
        "evidências insuficientes",
        "são insuficientes",
        "faltam os registros",
        "não permite confirmar",
        "não permite verificar",
    ]

    next_step_terms = [
        "recomenda",
        "recomenda-se",
        "verificar",
        "confirmar com o cliente",
        "contatar",
        "encaminhar",
        "consultar",
        "entrar em contato",
        "equipe de suporte",
        "próximo passo",
    ]

    matched_uncertainty = [
        term for term in uncertainty_terms if term in text
    ]
    matched_next_steps = [
        term for term in next_step_terms if term in text
    ]

    return {
        "acknowledges_uncertainty": bool(matched_uncertainty),
        "matched_uncertainty_terms": matched_uncertainty,
        "recommends_next_step": bool(matched_next_steps),
        "matched_next_step_terms": matched_next_steps,
        "response_length": len(response),
    }


def evaluate_scenario(response: str, case: dict, order=None) -> dict:
    """Check whether the response addresses the specific test scenario."""
    text = response.lower()
    checks = {}

    if case["name"] == "missing_item":
        checks["mentions_missing_item"] = any(
            term in text
            for term in ("batata frita", "batatas fritas")
        )
        checks["acknowledges_delivery_uncertainty"] = any(
            term in text
            for term in [
                "não é possível confirmar",
                "não permite confirmar",
                "não comprova",
                "não confirma",
                "não há como confirmar",
                "não garante",
                "não foi possível confirmar",
                "não há evidência",
                "não há evidências",
            ]
        )

    elif case["name"] == "late_delivery":
        checks["acknowledges_missing_timestamps"] = any(
            term in text
            for term in [
                "horário",
                "horários",
                "registro de entrega",
                "registros de entrega",
                "não há informação",
                "não estão disponíveis",
                "não é possível confirmar",
                "não permite confirmar",
                "evidências insuficientes",
                "não há registro",
                "não foi possível confirmar",
            ]
        )

    elif case["name"] == "unknown_reason":
        checks["mentions_delivered_status"] = any(
            term in text
            for term in [
                "consta como entregue",
                "status de entregue",
                "status é entregue",
                "foi entregue",
                "marcado como entregue",
                "status: delivered",
                "status delivered",
            ]
        )
        checks["avoids_inventing_cancellation_reason"] = any(
            term in text
            for term in [
                "não há registro",
                "não consta cancelamento",
                "não há informação sobre o cancelamento",
                "não é possível confirmar o motivo",
                "não é possível identificar o motivo",
                "não foi possível confirmar o motivo",
                "motivo não informado",
            ]
        )

    elif case["name"] == "order_preparing":
        checks["mentions_preparing_status"] = any(
            term in text
            for term in [
                "em preparação",
                "está sendo preparado",
                "ainda está preparando",
                "preparando o pedido",
                "status: preparing",
                "status preparing",
            ]
        )
        checks["acknowledges_missing_eta"] = any(
            term in text
            for term in [
                "previsão de entrega",
                "horário estimado",
                "não é possível informar quando",
                "não há previsão",
                "não temos uma previsão",
                "não há informação sobre o horário",
                "sem previsão",
            ]
        )

    elif case["name"] == "order_delivered":
        checks["mentions_delivered_status"] = any(
            term in text
            for term in [
                "consta como entregue",
                "status de entregue",
                "status é entregue",
                "foi marcado como entregue",
                "marcado como entregue",
                "status: delivered",
                "status delivered",
            ]
        )
        checks["suggests_checking_discrepancy"] = any(
            term in text
            for term in [
                "verificar com o restaurante",
                "contatar o restaurante",
                "entrar em contato com o restaurante",
                "equipe de suporte",
                "verificar a divergência",
                "confirmar com o cliente",
                "investigar a divergência",
            ]
        )

    return {
        "checks": checks,
        "passed": bool(checks) and all(checks.values()),
        # Os cenários são avaliações de suporte; não autorizam
        # automaticamente uma decisão operacional sem supervisão.
        "manual_review_required": True,
    }


def summarize_results(results: list[dict]) -> dict:
    """Summarize completed, approved, failed, and review-required cases."""
    completed_results = [
        result
        for result in results
        if result.get("status") == "completed"
    ]

    approved = sum(
        result.get("scenario_checks", {}).get("passed") is True
        for result in completed_results
    )

    failed = sum(
        result.get("scenario_checks", {}).get("passed") is False
        for result in completed_results
    )

    manual_review = sum(
        result.get("requires_human_review") is True
        or result.get("scenario_checks", {}).get(
            "manual_review_required"
        ) is True
        for result in completed_results
    )

    return {
        "completed": len(completed_results),
        "approved": approved,
        "failed": failed,
        "manual_review": manual_review,
        "registered": len(results),
    }


def run_evaluation() -> None:
    """Run evaluation scenarios and save results to a JSON file."""
    output_dir = Path("evaluation_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for index, case in enumerate(CASES):
        print(f"\nExecutando caso: {case['name']}")

        try:
            order = get_order_by_id(case["order_id"])

            if order is None:
                result = {
                    "case": case["name"],
                    "status": "invalid_test_data",
                    "error": f"Pedido não encontrado: {case['order_id']}",
                }
                results.append(result)
                print(result["error"])
                continue

            analysis = analyze_order_issue(
                order=order,
                customer_message=case["customer_message"],
            )

            response_text = analysis_to_text(analysis)
            checks = evaluate_response(response_text)
            scenario_checks = evaluate_scenario(
                response=response_text,
                case=case,
                order=order,
            )

            result = {
                "case": case["name"],
                "status": "completed",
                "order_id": case["order_id"],
                "customer_message": case["customer_message"],
                "analysis": (
                    analysis.model_dump()
                    if hasattr(analysis, "model_dump")
                    else {"response": str(analysis)}
                ),
                "checks": checks,
                "scenario_checks": scenario_checks,
                "requires_human_review": getattr(
                    analysis,
                    "requires_human_review",
                    None,
                ),
            }

            results.append(result)

            print("\nAnálise estruturada do agente:")
            print(
                json.dumps(
                    result["analysis"],
                    ensure_ascii=False,
                    indent=2,
                )
            )
            print("\nVerificações automáticas:")
            print(json.dumps(checks, ensure_ascii=False, indent=2))
            print("\nVerificações específicas do cenário:")
            print(
                json.dumps(
                    scenario_checks,
                    ensure_ascii=False,
                    indent=2,
                )
            )

        except Exception as exc:
            status = classify_execution_error(exc)
            logger.exception(
                "Falha na avaliação do cenário %s",
                case["name"],
            )

            results.append({
                "case": case["name"],
                "status": status,
                "error": str(exc),
            })

            print(f"Erro ao executar o caso ({status}): {exc}")

            if status.startswith("api_"):
                print(
                    "\nErro do serviço de IA. "
                    "Interrompendo a avaliação para evitar novas chamadas."
                )

                for remaining_case in CASES[index + 1:]:
                    results.append({
                        "case": remaining_case["name"],
                        "status": "not_executed",
                        "reason": (
                            "Avaliação interrompida devido a erro da API."
                        ),
                    })
                break

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"evaluation_{timestamp}.json"

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)

    summary = summarize_results(results)

    print(f"\nResultados salvos em: {output_file}")
    print(f"Casos concluídos: {summary['completed']}/{len(CASES)}")
    print(f"Casos registrados: {summary['registered']}/{len(CASES)}")
    print("\nResumo da avaliação")
    print("===================")
    print(f"Cenários concluídos: {summary['completed']}")
    print(f"Cenários aprovados: {summary['approved']}")
    print(f"Cenários reprovados: {summary['failed']}")
    print(f"Revisões manuais necessárias: {summary['manual_review']}")


if __name__ == "__main__":
    run_evaluation()
