
from unittest.mock import Mock

from langchain_core.messages import AIMessage, ToolMessage

from app.schemas.orders import ComplaintAnalysis, Order
from app.services import order_analysis


class FakeLLM:
    """Simula o modelo sem chamar a API do Gemini."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.received_messages = []
        self.tools = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    def with_config(self, config):
        return self

    def with_structured_output(self, schema):
        self.output_schema = schema
        return self

    def invoke(self, messages):
        self.received_messages.append(list(messages))

        if not self.responses:
            raise AssertionError("Não há mais respostas simuladas.")

        return self.responses.pop(0)


class FakeTool:
    """Simula a ferramenta de consulta de pedidos."""

    name = "lookup_order_tool"

    def __init__(self):
        self.results = []

    def invoke(self, args):
        self.results.append(args)

        return {
            "order_id": "PED-1001",
            "customer_id": "CLI-001",
            "restaurant": "Cantina da Praça",
            "status": "delivered",
            "items": [
                {
                    "name": "Batata frita",
                    "quantity": 1,
                    "price": 12.00,
                }
            ],
            "total": 12.00,
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


def create_analysis(**overrides):
    """Cria uma análise estruturada válida para os testes."""

    data = {
        "confirmed_facts": [
            "O pedido está registrado como entregue."
        ],
        "evidence": [
            "O registro do pedido indica status delivered."
        ],
        "complaint_assessment": (
            "Os dados disponíveis não comprovam se o item "
            "chegou fisicamente ao cliente."
        ),
        "recommended_next_step": (
            "Verificar a reclamação e confirmar os itens recebidos."
        ),
        "missing_information": [
            "Confirmação dos itens efetivamente recebidos."
        ],
        "requires_human_review": True,
    }
    data.update(overrides)

    return ComplaintAnalysis(**data)


def configure_models(monkeypatch, tool_responses, analysis=None):
    """Configura modelos simulados para as duas etapas do serviço."""

    tool_llm = FakeLLM(tool_responses)
    structured_llm = FakeLLM([analysis or create_analysis()])

    get_llm_mock = Mock(
        side_effect=[tool_llm, structured_llm]
    )

    monkeypatch.setattr(
        order_analysis,
        "get_llm",
        get_llm_mock,
    )

    return tool_llm, structured_llm, get_llm_mock


def test_agent_uses_tool_and_returns_structured_analysis(monkeypatch):
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

    final_tool_response = AIMessage(
        content="Investigação concluída.",
    )

    tool_llm, structured_llm, get_llm_mock = configure_models(
        monkeypatch,
        [tool_response, final_tool_response],
    )

    fake_tool = FakeTool()
    monkeypatch.setattr(
        order_analysis,
        "lookup_order_tool",
        fake_tool,
    )

    result = order_analysis.analyze_order_issue(
        order=create_order(),
        customer_message="Meu pedido chegou sem as batatas fritas.",
    )

    assert isinstance(result, ComplaintAnalysis)
    assert result.requires_human_review is True
    assert "não comprovam" in result.complaint_assessment

    assert fake_tool.results == [
        {"order_id": "PED-1001"}
    ]

    assert len(tool_llm.received_messages) == 2
    assert len(structured_llm.received_messages) == 1
    assert get_llm_mock.call_count == 2

    second_call_messages = tool_llm.received_messages[1]

    assert any(
        isinstance(message, ToolMessage)
        and "PED-1001" in message.content
        for message in second_call_messages
    )


def test_agent_returns_structured_analysis_without_tool_call(
    monkeypatch,
):
    final_response = AIMessage(
        content="A reclamação precisa ser verificada.",
    )

    tool_llm, structured_llm, _ = configure_models(
        monkeypatch,
        [final_response],
    )

    result = order_analysis.analyze_order_issue(
        order=create_order(),
        customer_message="Meu pedido chegou atrasado.",
    )

    assert isinstance(result, ComplaintAnalysis)
    assert result.requires_human_review is True
    assert len(tool_llm.received_messages) == 1
    assert len(structured_llm.received_messages) == 1


def test_agent_rejects_lookup_for_different_order_id(monkeypatch):
    wrong_order_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "lookup_order_tool",
                "args": {"order_id": "PED-1002"},
                "id": "call_wrong_order",
            }
        ],
    )

    final_response = AIMessage(
        content="A consulta foi direcionada ao pedido correto.",
    )

    tool_llm, _, _ = configure_models(
        monkeypatch,
        [wrong_order_call, final_response],
    )

    fake_tool = FakeTool()
    monkeypatch.setattr(
        order_analysis,
        "lookup_order_tool",
        fake_tool,
    )

    result = order_analysis.analyze_order_issue(
        order=create_order(),
        customer_message="Meu pedido chegou incompleto.",
    )

    assert isinstance(result, ComplaintAnalysis)
    assert fake_tool.results == []

    second_call_messages = tool_llm.received_messages[1]

    assert any(
        isinstance(message, ToolMessage)
        and "só é permitido consultar" in message.content
        for message in second_call_messages
    )


def test_agent_rejects_empty_order_id(monkeypatch):
    invalid_tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "lookup_order_tool",
                "args": {"order_id": ""},
                "id": "call_empty_order",
            }
        ],
    )

    final_response = AIMessage(
        content="O ID do pedido precisa ser válido.",
    )

    configure_models(
        monkeypatch,
        [invalid_tool_call, final_response],
    )

    fake_tool = FakeTool()
    monkeypatch.setattr(
        order_analysis,
        "lookup_order_tool",
        fake_tool,
    )

    result = order_analysis.analyze_order_issue(
        order=create_order(),
        customer_message="Meu pedido chegou incompleto.",
    )

    assert isinstance(result, ComplaintAnalysis)
    assert fake_tool.results == []


def test_agent_rejects_non_string_order_id(monkeypatch):
    invalid_tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "lookup_order_tool",
                "args": {"order_id": 123},
                "id": "call_invalid_order_type",
            }
        ],
    )

    final_response = AIMessage(
        content="O ID do pedido precisa ser válido.",
    )

    configure_models(
        monkeypatch,
        [invalid_tool_call, final_response],
    )

    fake_tool = FakeTool()
    monkeypatch.setattr(
        order_analysis,
        "lookup_order_tool",
        fake_tool,
    )

    result = order_analysis.analyze_order_issue(
        order=create_order(),
        customer_message="Meu pedido chegou incompleto.",
    )

    assert isinstance(result, ComplaintAnalysis)
    assert fake_tool.results == []


def test_agent_requests_human_review_when_tool_limit_is_reached(
    monkeypatch,
):
    repeated_tool_calls = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "lookup_order_tool",
                    "args": {"order_id": "PED-1001"},
                    "id": f"call_{number}",
                }
            ],
        )
        for number in range(order_analysis.MAX_TOOL_ROUNDS)
    ]

    tool_llm = FakeLLM(repeated_tool_calls)

    monkeypatch.setattr(
        order_analysis,
        "get_llm",
        lambda: tool_llm,
    )

    fake_tool = FakeTool()
    monkeypatch.setattr(
        order_analysis,
        "lookup_order_tool",
        fake_tool,
    )

    result = order_analysis.analyze_order_issue(
        order=create_order(),
        customer_message="Meu pedido chegou incompleto.",
    )

    assert isinstance(result, ComplaintAnalysis)
    assert result.requires_human_review is True
    assert "limite de chamadas" in result.complaint_assessment
    assert len(tool_llm.received_messages) == (
        order_analysis.MAX_TOOL_ROUNDS
    )


def test_agent_returns_fallback_for_invalid_structured_output(
    monkeypatch,
):
    final_response = AIMessage(
        content="Investigação concluída.",
    )

    tool_llm = FakeLLM([final_response])
    structured_llm = FakeLLM(
        [
            {
                "confirmed_facts": [],
                "evidence": [],
                "complaint_assessment": "",
                "recommended_next_step": "Verificar manualmente.",
                "missing_information": [],
                "requires_human_review": True,
            }
        ]
    )

    get_llm_mock = Mock(
        side_effect=[tool_llm, structured_llm]
    )
    monkeypatch.setattr(
        order_analysis,
        "get_llm",
        get_llm_mock,
    )

    result = order_analysis.analyze_order_issue(
        order=create_order(),
        customer_message="Meu pedido chegou atrasado.",
    )

    assert isinstance(result, ComplaintAnalysis)
    assert result.requires_human_review is True
    assert result.recommended_next_step
