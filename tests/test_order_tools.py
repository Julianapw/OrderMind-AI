
from app.tools.order_lookup import lookup_order_tool


def test_lookup_order_tool_returns_order_data():
    result = lookup_order_tool.invoke({"order_id": "PED-1001"})

    assert result["order_id"] == "PED-1001"
    assert result["restaurant"] == "Cantina da Praça"
    assert result["status"] == "delivered"


def test_lookup_order_tool_handles_unknown_order():
    result = lookup_order_tool.invoke({"order_id": "PED-9999"})

    assert "Nenhum pedido encontrado" in result
