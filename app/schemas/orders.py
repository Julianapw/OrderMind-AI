
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


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: Order
    customer_message: str
    status: str
    message: str
