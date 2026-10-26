
from app.agent.order_graph import (
    build_order_analysis_graph,
    decide_next_step,
    validate_evidence,
)
from app.schemas.orders import ComplaintAnalysis, Order


def make_analysis(
    *,
    confirmed_facts=None,
    evidence=None,
    requires_human_review=False,
):
    return ComplaintAnalysis(
        confirmed_facts=confirmed_facts or [],
        evidence=evidence or [],
        complaint_assessment="Reclamação analisada com os dados disponíveis.",
        recommended_next_step="Verificar a ocorrência com o restaurante.",
        missing_information=[],
        requires_human_review=requires_human_review,
    )


def make_order():
    return Order(
        order_id="PED-1001",
        customer_id="CLI-001",
        restaurant="Restaurante Teste",
        status="delivered",
        items=[
            {"name": "Batata frita", "quantity": 1, "price": 12.0}
        ],
        total=12.0,
    )


def test_validate_evidence_flags_empty_analysis():
    analysis = make_analysis()

    result = validate_evidence({"analysis": analysis})

    assert result["requires_human_review"] is True
    assert "error" in result


def test_validate_evidence_accepts_analysis_with_evidence():
    analysis = make_analysis(
        confirmed_facts=["O pedido consta como entregue."]
    )

    result = validate_evidence({"analysis": analysis})

    assert result == {}


def test_decide_next_step_requires_review_when_error_exists():
    result = decide_next_step(
        {
            "error": "analysis_execution_failed",
            "analysis": make_analysis(),
        }
    )

    assert result["requires_human_review"] is True


def test_decide_next_step_preserves_model_review_decision():
    analysis = make_analysis(requires_human_review=True)

    result = decide_next_step({"analysis": analysis})

    assert result["requires_human_review"] is True


def test_graph_runs_all_nodes_without_calling_external_llm():
    expected_analysis = make_analysis(
        confirmed_facts=["O pedido consta como entregue."],
        evidence=["Registro do pedido PED-1001."],
    )

    def fake_analyze_node(state):
        assert state["order"].order_id == "PED-1001"
        assert state["customer_message"] == "Meu pedido não chegou."
        return {"analysis": expected_analysis}

    graph = build_order_analysis_graph(fake_analyze_node)

    result = graph.invoke(
        {
            "order": make_order(),
            "customer_message": "Meu pedido não chegou.",
        }
    )

    assert result["analysis"] == expected_analysis
    assert result["requires_human_review"] is False
    assert "error" not in result
