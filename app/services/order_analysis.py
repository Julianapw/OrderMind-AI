
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_llm
from app.schemas.orders import Order


analysis_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are OrderMind, an assistant that investigates delivery
order complaints using the provided order data.

Rules:
- Use only the information provided in the order data and
  customer message.
- Never invent missing facts.
- Distinguish confirmed facts from possible explanations.
- Do not promise refunds, compensation, or other actions.
- If the evidence is insufficient, say what needs to be checked.
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
Order data:
{order_data}

Customer complaint:
{customer_message}

Analyze this case using the rules above.
            """,
        ),
    ]
)


def analyze_order_issue(
    order: Order,
    customer_message: str,
) -> str:
    "Analyze a customer complaint against the order data."
    chain = analysis_prompt | get_llm() | StrOutputParser()

    return chain.invoke(
        {
            "order_data": order.model_dump_json(indent=2),
            "customer_message": customer_message,
        }
    )
