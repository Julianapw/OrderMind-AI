
import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas.orders import ComplaintAnalysis, Order


logger = logging.getLogger(__name__)


class OrderAnalysisState(TypedDict, total=False):
    order: Order
    customer_message: str
    analysis: ComplaintAnalysis
    error: str
    requires_human_review: bool


def validate_evidence(state: OrderAnalysisState) -> dict:
    analysis = state.get("analysis")

    if analysis is None:
        return {
            "error": "A análise não foi produzida.",
            "requires_human_review": True,
        }

    if not analysis.confirmed_facts and not analysis.evidence:
        return {
            "error": "A análise não contém evidências suficientes.",
            "requires_human_review": True,
        }

    return {}


def decide_next_step(state: OrderAnalysisState) -> dict:
    analysis = state.get("analysis")

    if state.get("error") or analysis is None:
        return {"requires_human_review": True}

    return {
        "requires_human_review": analysis.requires_human_review
    }


def build_order_analysis_graph(analyze_node):
    graph = StateGraph(OrderAnalysisState)

    graph.add_node("analyze_complaint", analyze_node)
    graph.add_node("validate_evidence", validate_evidence)
    graph.add_node("decide_next_step", decide_next_step)

    graph.add_edge(START, "analyze_complaint")
    graph.add_edge("analyze_complaint", "validate_evidence")
    graph.add_edge("validate_evidence", "decide_next_step")
    graph.add_edge("decide_next_step", END)

    return graph.compile()
