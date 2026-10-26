import logging
from typing import Callable, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas.orders import ComplaintAnalysis, Order
from app.tools.order_lookup import get_order_by_id


logger = logging.getLogger(__name__)


class OrderAnalysisState(TypedDict, total=False):
    order_id: str
    order: Order
    customer_message: str
    analysis: ComplaintAnalysis
    error: str
    requires_human_review: bool


def lookup_order(state: OrderAnalysisState) -> dict:
    """Busca o pedido antes de iniciar a análise."""
    order_id = state.get("order_id")

    if not order_id:
        return {
            "error": "O ID do pedido não foi informado.",
            "requires_human_review": True,
        }

    try:
        order = get_order_by_id(order_id)
    except Exception:
        logger.exception("Falha ao consultar o pedido %s", order_id)
        return {
            "error": "Não foi possível consultar o pedido.",
            "requires_human_review": True,
        }

    if order is None:
        return {
            "error": f"Nenhum pedido encontrado com o ID {order_id}.",
            "requires_human_review": True,
        }

    return {"order": order}


def route_after_lookup(
    state: OrderAnalysisState,
) -> Literal["analyze_complaint", "decide_next_step"]:
    """Só inicia a análise quando o pedido foi encontrado."""
    if state.get("error") or state.get("order") is None:
        return "decide_next_step"

    return "analyze_complaint"


def validate_evidence(state: OrderAnalysisState) -> dict:
    """Valida a análise sem ocultar erros anteriores."""
    # Preserva erros de execução e de comunicação com o provedor.
    if state.get("error"):
        return {"requires_human_review": True}

    analysis = state.get("analysis")

    if analysis is None:
        return {
            "error": "A análise não foi produzida.",
            "requires_human_review": True,
        }

    # Uma análise sem fatos confirmados nem evidências não deve
    # ser tratada como suficiente para orientar uma decisão.
    if not analysis.confirmed_facts and not analysis.evidence:
        return {
            "error": "A análise não contém evidências suficientes.",
            "requires_human_review": True,
        }

    return {}


def decide_next_step(state: OrderAnalysisState) -> dict:
    """Determina se o caso pode prosseguir ou precisa de revisão humana."""
    analysis = state.get("analysis")

    if state.get("error") or analysis is None:
        return {"requires_human_review": True}

    # Não sobrescreve uma solicitação de revisão já registrada.
    if state.get("requires_human_review"):
        return {"requires_human_review": True}

    return {
        "requires_human_review": analysis.requires_human_review
    }


def build_order_analysis_graph(analyze_node: Callable):
    """Monta o fluxo de consulta, análise, validação e decisão."""
    graph = StateGraph(OrderAnalysisState)

    graph.add_node("lookup_order", lookup_order)
    graph.add_node("analyze_complaint", analyze_node)
    graph.add_node("validate_evidence", validate_evidence)
    graph.add_node("decide_next_step", decide_next_step)

    graph.add_edge(START, "lookup_order")

    graph.add_conditional_edges(
        "lookup_order",
        route_after_lookup,
        {
            "analyze_complaint": "analyze_complaint",
            "decide_next_step": "decide_next_step",
        },
    )

    graph.add_edge("analyze_complaint", "validate_evidence")
    graph.add_edge("validate_evidence", "decide_next_step")
    graph.add_edge("decide_next_step", END)

    return graph.compile()
