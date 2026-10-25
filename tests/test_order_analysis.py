
from langchain_core.messages import AIMessage, ToolMessage
from unittest.mock import patch
from app.schemas.orders import Order
from app.services import order_analysis


class FakeLLM:
    "Simula respostas do modelo sem chamar a API do Gemini."

    def __init__(self, responses):
        self.responses = responses
        self.received_messages = []
        self.tools = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    def invoke(self, messages):
        self.received_messages.append(list(messages))
        return self.responses.pop(0)

class FakeTool:
    "Simula a ferramenta de consulta de pedidos."

    name = "lookup_order_tool"

    def __init__(self):
        self.results = []

    def invoke(self, args):
        self.results.append(args)

        return {
            "order_id": "PED-1001",
            "status": "delivered",
            "items": [
                {
                    "name": "Batata frita",
                    "quantity": 1,
                    "price": 12.00,
                }
            ],
        }


def create_order():
    """Cria um pedido fictício para os testes."""

    return Order(
        order_id="PED-1001",
        customer_id="CLI-001",
        restaurant="Cantina da Praça",
        status="delivered",
        items=[
            {
                "name": "Batata frita",
                "quantity": 1,
                "price": 12.00,
            }
        ],
        total=12.00,
    )




def test_agent_uses_tool_and_processes_its_result(monkeypatch):
    tool_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "lookup_order_tool",
                "args": {"order_id": "PED-1001"},
                "id": "call_1",
            }
        ],
    )

    final_response = AIMessage(
        content="O pedido inclui batata frita, mas não comprova a entrega.",
    )

    fake_llm = FakeLLM([tool_response, final_response])
    fake_tool = FakeTool()

    monkeypatch.setattr(
        order_analysis,
        "get_llm",
        lambda: fake_llm,
    )

    monkeypatch.setattr(
        order_analysis,
        "lookup_order_tool",
        fake_tool,
    )

    result = order_analysis.analyze_order_issue(
        order=create_order(),
        customer_message="Meu pedido chegou sem as batatas fritas.",
    )

    assert result == final_response.content

    assert fake_tool.results == [
        {"order_id": "PED-1001"}
    ]

    assert len(fake_llm.received_messages) == 2

    second_call_messages = fake_llm.received_messages[1]

    assert any(
        isinstance(message, ToolMessage)
        and "PED-1001" in message.content
        for message in second_call_messages
    )


def test_agent_returns_response_without_tool_call(monkeypatch):
    final_response = AIMessage(
        content="A reclamação precisa ser verificada.",
    )

    fake_llm = FakeLLM([final_response])

    monkeypatch.setattr(
        order_analysis,
        "get_llm",
        lambda: fake_llm,
    )

    result = order_analysis.analyze_order_issue(
        order=create_order(),
        customer_message="Meu pedido chegou atrasado.",
    )

    assert result == "A reclamação precisa ser verificada."
    assert len(fake_llm.received_messages) == 1
