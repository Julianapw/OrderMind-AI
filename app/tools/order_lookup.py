
import json
from pathlib import Path

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
