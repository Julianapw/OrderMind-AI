
from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm
from app.schemas.orders import Order
from app.tools.order_lookup import lookup_order_tool


analysis_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are OrderMind, an assistant that investigates delivery
order complaints using tools and evidence.

Rules:
- Use the order lookup tool when you need to verify order data.
- Use only information returned by tools and the customer message.
- Never invent missing facts.
- Distinguish confirmed facts from possible explanations.
- Do not promise refunds, compensation, or other actions.
- If evidence is insufficient, explain what needs to be checked.
- Respond in the same language as the customer's message.
- Be concise, professional, and empathetic.
- Structure your response with:
  1. What the data confirms
  2. Assessment of the complaint
  3. Recommended next step
""",
        ),
        (
            "human",
            """
Order ID: {order_id}

Customer complaint:
{customer_message}

Investigate the complaint using the available tool when needed.
""",
        ),
    ]
)


def analyze_order_issue(order: Order, customer_message: str) -> str:
    """Analyze a complaint using the Gemini model and available tools."""
    llm = get_llm().bind_tools([lookup_order_tool])

    messages = analysis_prompt.format_messages(
        order_id=order.order_id,
        customer_message=customer_message,
    )

    # Allow the model to request a tool and then use its result.
    for _ in range(5):
        response = llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            if isinstance(response.content, str):
                return response.content

            if isinstance(response.content, list):
                text_parts = [
                    block["text"]
                    for block in response.content
                    if isinstance(block, dict)
                    and isinstance(block.get("text"), str)
                ]
                return "\n".join(text_parts)

            return str(response.content)

        for tool_call in response.tool_calls:
            if tool_call["name"] == lookup_order_tool.name:
                result = lookup_order_tool.invoke(tool_call["args"])
            else:
                result = f"Tool not available: {tool_call['name']}"

            messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                )
            )

    return (
        "Não foi possível concluir a análise dentro do limite "
        "de chamadas de ferramentas. A reclamação precisa ser "
        "verificada manualmente."
    )
