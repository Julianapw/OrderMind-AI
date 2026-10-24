
# OrderMind

OrderMind is a Python project exploring reliable AI agents
for delivery order support and operational decision-making.

## Current features

- FastAPI application with interactive API documentation.
- Pydantic schemas for request and order validation.
- Fictional order database.
- Order lookup functionality.
- Automated API and validation tests.

## Tech stack

- Python
- FastAPI
- Pydantic
- LangChain
- LangGraph
- Google Gemini
- Pytest

## Getting started

### Requirements

Python 3.11 or newer.

### Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### Run the API

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs to explore the API.

### Run tests

```bash
pytest -v
```

## Example request

POST `/api/v1/orders/analyze`

```json
{
  "order_id": "PED-1001",
  "customer_message": "My order arrived incomplete."
}
```

## Roadmap

- Gemini integration and tool calling.
- LangGraph orchestration.
- Policy retrieval with evidence.
- Agent execution controls and evaluation benchmarks.

## Data and safety

This project uses fictional demonstration data and is
not connected to iFood's internal systems.
