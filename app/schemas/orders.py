
from pydantic import BaseModel, ConfigDict, Field


class OrderItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    price: float = Field(ge=0)


class Order(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    restaurant: str = Field(min_length=1)
    status: str = Field(
        pattern="^(preparing|delivered|cancelled)$"
    )
    items: list[OrderItem] = Field(min_length=1)
    total: float = Field(ge=0)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(min_length=1, max_length=30)
    customer_message: str = Field(
        min_length=5,
        max_length=2000,
    )


class ComplaintAnalysis(BaseModel):
    """Structured analysis of a customer's delivery complaint."""

    model_config = ConfigDict(extra="forbid")

    confirmed_facts: list[str] = Field(
        description=(
            "Facts supported by the order data or customer message."
        )
    )
    evidence: list[str] = Field(
        description="Evidence used to support the analysis."
    )
    complaint_assessment: str = Field(
        min_length=1,
        description=(
            "Assessment of the customer's complaint based on "
            "available evidence."
        ),
    )
    recommended_next_step: str = Field(
        min_length=1,
        description=(
            "Practical next step, without promising compensation."
        ),
    )
    missing_information: list[str] = Field(
        description=(
            "Information that is still missing to reach a conclusion."
        )
    )
    requires_human_review: bool = Field(
        description="Whether a person needs to review the case."
    )


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: Order
    customer_message: str
    status: str
    message: str
    analysis: ComplaintAnalysis | None = None
