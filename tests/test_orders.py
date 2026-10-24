
import pytest
from pydantic import ValidationError

from app.schemas.orders import Order
from app.tools.order_lookup import (
    get_order_by_id,
    load_orders,
)


def test_load_orders():
    orders = load_orders()

    assert len(orders) == 3


def test_find_existing_order():
    order = get_order_by_id("PED-1001")

    assert order is not None
    assert order.restaurant == "Cantina da Praça"
    assert len(order.items) == 3


def test_unknown_order_returns_none():
    assert get_order_by_id("PED-9999") is None


def test_order_rejects_invalid_status():
    order_data = load_orders()[0].model_dump()
    order_data["status"] = "unknown_status"

    with pytest.raises(ValidationError):
        Order.model_validate(order_data)


def test_order_rejects_negative_quantity():
    order_data = load_orders()[0].model_dump()
    order_data["items"][0]["quantity"] = -1

    with pytest.raises(ValidationError):
        Order.model_validate(order_data)
