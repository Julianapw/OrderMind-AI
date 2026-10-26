
import json

import pytest

from app.evaluation import evaluate_agent


def test_quota_error_stops_remaining_cases(monkeypatch, tmp_path):
    cases = [
        {
            "name": "case_1",
            "order_id": "PED-1001",
            "customer_message": "Meu pedido atrasou.",
        },
        {
            "name": "case_2",
            "order_id": "PED-1002",
            "customer_message": "Meu pedido não chegou.",
        },
        {
            "name": "case_3",
            "order_id": "PED-1003",
            "customer_message": "Meu pedido está errado.",
        },
    ]

    calls = []

    monkeypatch.setattr(evaluate_agent, "CASES", cases)
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        evaluate_agent,
        "get_order_by_id",
        lambda order_id: {"order_id": order_id},
    )

    def fake_analyze_order_issue(order, customer_message):
        calls.append(order["order_id"])
        raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")

    monkeypatch.setattr(
        evaluate_agent,
        "analyze_order_issue",
        fake_analyze_order_issue,
    )

    evaluate_agent.run_evaluation()

    result_files = list(
        (tmp_path / "evaluation_results").glob("evaluation_*.json")
    )

    assert len(result_files) == 1

    with result_files[0].open(encoding="utf-8") as file:
        results = json.load(file)

    assert calls == ["PED-1001"]
    assert results[0]["status"] == "api_quota_error"
    assert results[1]["status"] == "not_executed"
    assert results[2]["status"] == "not_executed"


@pytest.mark.parametrize(
    "case_name,response",
    [
        (
            "missing_item",
            "Você informou que faltou a batata frita. "
            "Não é possível confirmar a entrega de todos os itens.",
        ),
        (
            "late_delivery",
            "Não há informação sobre os horários de entrega "
            "para confirmar o atraso.",
        ),
        (
            "unknown_reason",
            "O pedido consta como entregue. Não há registro "
            "que permita confirmar o motivo do cancelamento.",
        ),
        (
            "order_preparing",
            "O pedido está em preparação, mas não há previsão "
            "de entrega disponível.",
        ),
        (
            "order_delivered",
            "O pedido consta como entregue. Recomendo verificar "
            "a divergência com o restaurante.",
        ),
    ],
)
def test_evaluate_scenario_passes_valid_responses(case_name, response):
    case = next(
        case
        for case in evaluate_agent.CASES
        if case["name"] == case_name
    )

    result = evaluate_agent.evaluate_scenario(
        response=response,
        case=case,
        order=None,
    )

    assert result["passed"] is True
    assert all(result["checks"].values())
    assert result["manual_review_required"] is True


def test_evaluate_scenario_fails_when_required_information_is_missing():
    case = next(
        case
        for case in evaluate_agent.CASES
        if case["name"] == "missing_item"
    )

    response = "Entendo sua reclamação. Vamos analisar o ocorrido."

    result = evaluate_agent.evaluate_scenario(
        response=response,
        case=case,
        order=None,
    )

    assert result["passed"] is False
    assert result["checks"]["mentions_missing_item"] is False
    assert result["checks"]["acknowledges_delivery_uncertainty"] is False


def test_summarize_results_counts_statuses():
    results = [
        {
            "status": "completed",
            "scenario_checks": {
                "passed": True,
                "manual_review_required": True,
            },
        },
        {
            "status": "completed",
            "scenario_checks": {
                "passed": False,
                "manual_review_required": True,
            },
        },
        {
            "status": "api_quota_error",
            "error": "Quota exceeded",
        },
        {
            "status": "not_executed",
        },
    ]

    summary = evaluate_agent.summarize_results(results)

    assert summary == {
        "completed": 2,
        "approved": 1,
        "failed": 1,
        "manual_review": 2,
        "registered": 4,
    }


def test_summarize_results_handles_empty_results():
    summary = evaluate_agent.summarize_results([])

    assert summary == {
        "completed": 0,
        "approved": 0,
        "failed": 0,
        "manual_review": 0,
        "registered": 0,
    }
