from fastapi import APIRouter, HTTPException

from app.schemas.orders import (
    AnalysisRequest,
    AnalysisResponse,
)
from app.services.order_analysis import analyze_order_issue
from app.tools.order_lookup import get_order_by_id


router = APIRouter()


@router.post(
    "/orders/analyze",
    response_model=AnalysisResponse,
    summary="Analyze a delivery order",
)
def analyze_order(request: AnalysisRequest) -> AnalysisResponse:
    """Retrieve an order and analyze the customer's complaint."""

    order = get_order_by_id(request.order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found in the demonstration database.",
        )

    try:
        analysis = analyze_order_issue(
            order=order,
            customer_message=request.customer_message,
        )

    except Exception as error:
        error_message = str(error).lower()

        # API quota or rate limit exceeded
        if any(
            term in error_message
            for term in (
                "resource_exhausted",
                "quota exceeded",
                "rate limit",
                "too many requests",
                "429",
            )
        ):
            raise HTTPException(
                status_code=503,
                detail=(
                    "O serviço de IA atingiu o limite de requisições. "
                    "Tente novamente mais tarde, quando a cota "
                    "estiver disponível."
                ),
            ) from error

        # Request exceeded the provider's time limit
        if any(
            term in error_message
            for term in (
                "deadline_exceeded",
                "deadline expired",
                "504",
                "timed out",
                "timeout",
            )
        ):
            raise HTTPException(
                status_code=504,
                detail=(
                    "A análise excedeu o tempo limite do serviço de IA. "
                    "Tente novamente mais tarde."
                ),
            ) from error

        # Provider temporarily unavailable
        if any(
            term in error_message
            for term in (
                "unavailable",
                "service unavailable",
                "503",
            )
        ):
            raise HTTPException(
                status_code=503,
                detail=(
                    "O serviço de IA está temporariamente indisponível. "
                    "Tente novamente mais tarde."
                ),
            ) from error

        # Unexpected internal error
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao analisar o pedido.",
        ) from error

    return AnalysisResponse(
        order=order,
        customer_message=request.customer_message,
        status="analyzed",
        message=analysis.complaint_assessment,
        analysis=analysis,
    )
