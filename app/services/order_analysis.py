import logging

from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from app.agent.order_graph import build_order_analysis_graph
from app.core.llm import get_llm
from app.schemas.orders import ComplaintAnalysis, Order
from app.tools.order_lookup import lookup_order_tool


logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 3
MODEL_TIMEOUT_SECONDS = 20


PROVIDER_ERROR_TERMS = (
    "resource_exhausted",
    "quota exceeded",
    "rate limit",
    "too many requests",
    "429",
    "unavailable",
    "service unavailable",
    "503",
    "deadline_exceeded",
    "deadline expired",
    "504",
    "timed out",
    "timeout",
)


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
- Never claim that an action was completed unless evidence confirms it.
- Request human review when the available evidence is insufficient
  or the case requires a decision beyond the available information.
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


def _fallback_analysis(reason: str) -> ComplaintAnalysis:
    """Return a safe structured result when analysis cannot be completed."""
    return ComplaintAnalysis(
        confirmed_facts=[],
        evidence=[],
        complaint_assessment=reason,
        recommended_next_step=(
            "Verificar os dados do pedido e a reclamação manualmente "
            "antes de tomar qualquer decisão."
        ),
        missing_information=[
            "Não foi possível confirmar todos os dados necessários "
            "para concluir a análise."
        ],
        requires_human_review=True,
    )


def _analyze_order_issue_impl(
    order: Order,
    customer_message: str,
) -> ComplaintAnalysis:
    """Execute the analysis and bounded tool-calling loop."""
    llm = get_llm().bind_tools([lookup_order_tool])

    messages = analysis_prompt.format_messages(
        order_id=order.order_id,
        customer_message=customer_message,
    )

    for round_number in range(1, MAX_TOOL_ROUNDS + 1):
        logger.info(
            "OrderMind model call %s/%s for order %s",
            round_number,
            MAX_TOOL_ROUNDS,
            order.order_id,
        )

        response = llm.with_config(
            {
                "timeout": MODEL_TIMEOUT_SECONDS,
                "max_retries": 0,
            }
        ).invoke(messages)

        tool_calls = response.tool_calls or []

        if not tool_calls:
            logger.info(
                "Generating structured analysis for order %s",
                order.order_id,
            )

            structured_llm = get_llm().with_structured_output(
                ComplaintAnalysis
            )

            structured_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """
You are OrderMind, a delivery complaint analysis assistant.

Return a structured analysis that follows the requested schema.

Rules:
- Use only the supplied order data, customer message, and tool evidence.
- Never invent facts or claim that an unverified event occurred.
- Separate confirmed facts from allegations and assumptions.
- If evidence is insufficient, explain what remains unknown.
- Never promise refunds, compensation, or other actions.
- Recommend a practical next step.
- Set requires_human_review to true when evidence is insufficient
  or a human decision is needed.
- Respond in the same language as the customer's message.
- Keep each field concise and specific.
""",
                    ),
                    (
                        "human",
                        """
Order data:
{order_data}

Customer complaint:
{customer_message}

Evidence from the investigation:
{investigation}

Produce the structured complaint analysis.
""",
                    ),
                ]
            )

            investigation = "\n".join(
                str(message.content)
                for message in messages
                if isinstance(message, ToolMessage)
            )

            try:
                result = structured_llm.with_config(
                    {
                        "timeout": MODEL_TIMEOUT_SECONDS,
                        "max_retries": 0,
                    }
                ).invoke(
                    structured_prompt.format_messages(
                        order_data=order.model_dump_json(indent=2),
                        customer_message=customer_message,
                        investigation=(
                            investigation
                            if investigation
                            else "Nenhuma consulta adicional foi realizada."
                        ),
                    )
                )

                if isinstance(result, ComplaintAnalysis):
                    return result

                return ComplaintAnalysis.model_validate(result)

            except (ValidationError, ValueError, TypeError):
                logger.exception(
                    "Invalid structured analysis for order %s",
                    order.order_id,
                )
                return _fallback_analysis(
                    "Não foi possível validar a análise gerada."
                )

        messages.append(response)

        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            tool_call_id = tool_call.get("id", "")
            tool_args = tool_call.get("args", {})

            logger.info("OrderMind requested tool: %s", tool_name)

            if tool_name != lookup_order_tool.name:
                result = f"Ferramenta não disponível: {tool_name}"

            elif not isinstance(tool_args, dict):
                result = "Consulta não realizada: argumentos inválidos."

            else:
                requested_order_id = tool_args.get("order_id")

                if requested_order_id != order.order_id:
                    result = (
                        "Consulta não realizada: só é permitido consultar "
                        f"o pedido {order.order_id} nesta análise."
                    )
                else:
                    try:
                        result = lookup_order_tool.invoke(tool_args)
                    except Exception:
                        logger.exception("Order lookup tool failed")
                        result = (
                            "Não foi possível consultar os dados do pedido. "
                            "A reclamação precisa ser verificada manualmente."
                        )

            messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call_id,
                )
            )

    logger.warning(
        "OrderMind reached the tool-call limit for order %s",
        order.order_id,
    )

    return _fallback_analysis(
        "A investigação atingiu o limite de chamadas antes de ser concluída."
    )


def _run_analysis_node(state: dict) -> dict:
    """Run analysis while preserving provider errors for the API."""
    order = state.get("order")
    customer_message = state.get("customer_message", "")

    if order is None:
        return {
            "analysis": _fallback_analysis(
                "O pedido não foi encontrado para análise."
            ),
            "error": "order_not_found",
            "requires_human_review": True,
        }

    try:
        analysis = _analyze_order_issue_impl(
            order=order,
            customer_message=customer_message,
        )
        return {"analysis": analysis}

    except Exception as error:
        error_message = str(error).lower()

        logger.exception(
            "OrderMind graph failed while analyzing order %s",
            order.order_id,
        )

        if any(term in error_message for term in PROVIDER_ERROR_TERMS):
            return {
                "error": f"llm_provider_error: {error}",
                "requires_human_review": True,
            }

        return {
            "analysis": _fallback_analysis(
                "Não foi possível concluir a análise automaticamente."
            ),
            "error": "analysis_execution_failed",
            "requires_human_review": True,
        }


_order_analysis_graph = build_order_analysis_graph(_run_analysis_node)


def analyze_order_issue(
    order: Order,
    customer_message: str,
) -> ComplaintAnalysis:
    """Run the complaint analysis through the LangGraph workflow."""
    result = _order_analysis_graph.invoke(
        {
            "order_id": order.order_id,
            "customer_message": customer_message,
        }
    )

    error = result.get("error") or ""

    if error.startswith("llm_provider_error:"):
        raise RuntimeError(error)

    analysis = result.get("analysis")

    if not isinstance(analysis, ComplaintAnalysis):
        return _fallback_analysis(
            error or "Não foi possível validar o resultado do fluxo de análise."
        )

    if (
        result.get("requires_human_review")
        and not analysis.requires_human_review
    ):
        analysis = analysis.model_copy(
            update={"requires_human_review": True}
        )

    return analysis
