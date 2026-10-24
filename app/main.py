
from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(
    title="OrderMind",
    description=(
        "An AI agent for investigating delivery order issues "
        "using tools, evidence, and structured decisions."
    ),
    version="0.1.0",
)


@app.get("/", tags=["Home"])
def home() -> dict[str, str]:
    return {
        "application": "OrderMind",
        "message": "Welcome to OrderMind!",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "application": "OrderMind",
    }


app.include_router(
    router,
    prefix="/api/v1",
    tags=["Orders"],
)
