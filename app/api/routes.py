
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

    analysis = analyze_order_issue(
        order=order,
        customer_message=request.customer_message,
    )

    return AnalysisResponse(
        order=order,
        customer_message=request.customer_message,
        status="analyzed",
        message=analysis,
    )
