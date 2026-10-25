
import json
from pathlib import Path

from langchain_core.tools import tool

from app.schemas.orders import Order


DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "sample_orders.json"
)


def load_orders() -> list[Order]:
    """Load and validate the fictional order database."""
    with DATA_FILE.open("r", encoding="utf-8") as file:
        raw_orders = json.load(file)

    return [
        Order.model_validate(order)
        for order in raw_orders
    ]


def get_order_by_id(order_id: str) -> Order | None:
    """Find an order by its identifier."""
    for order in load_orders():
        if order.order_id == order_id:
            return order

    return None


@tool
def lookup_order_tool(order_id: str) -> dict | str:
    """Busca um pedido pelo ID e retorna seus dados registrados.

    Use esta ferramenta quando precisar verificar os dados
    de um pedido antes de analisar uma reclamação.
    """
    order = get_order_by_id(order_id)

    if order is None:
        return f"Nenhum pedido encontrado com o ID {order_id}."

    return order.model_dump()
