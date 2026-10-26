# OrderMind-AI

**A tool-using AI agent for delivery complaint analysis, built with LangChain, LangGraph, Pydantic, and Google Gemini.**

OrderMind-AI is a portfolio project exploring how to build more reliable LLM-based agents for delivery order support. It combines tool calling, structured outputs, workflow orchestration, evidence validation, and controlled execution to help analyze customer complaints without inventing facts or promising unverified actions.

> **Project status:** MVP under development. The core API, order schemas, agent workflow, and automated tests are implemented. End-to-end validation with the live Gemini API is still in progress.

## Key Features

- **Order lookup:** Retrieves order information from a fictional dataset.
- **LLM-based complaint analysis:** Uses Google Gemini to analyze customer messages in the context of order data.
- **Tool calling:** Allows the model to request order lookup when additional information is needed.
- **Structured outputs:** Represents the analysis using validated Pydantic models.
- **Workflow orchestration:** Uses LangGraph to coordinate order lookup, complaint analysis, evidence validation, and next-step decisions.
- **Execution controls:** Limits tool-calling iterations and configures model timeouts.
- **Failure handling:** Provides controlled fallback behavior and flags cases that require human review.
- **Automated tests:** Tests API behavior, validation, and agent logic using simulated model responses.
- **Evaluation scenarios:** Includes example complaints for exploring uncertainty handling and recommended next steps.

## Tech Stack

| Technology | Role in the Project |
|---|---|
| Python | Main programming language |
| FastAPI | REST API and interactive API documentation |
| LangChain | LLM integration, prompts, tool calling, and structured output |
| LangGraph | State-based workflow orchestration |
| Pydantic | Data schemas and input/output validation |
| Google Gemini | Language model for complaint analysis |
| Streamlit | User interface |
| Pytest | Automated tests |
| HTTPX | API testing support |

## Agentic Harness

OrderMind-AI explores an **agentic harness**: the application layer that governs how an AI agent executes a task, interacts with tools, validates results, and handles failure conditions.

The current implementation includes:

- **Orchestration:** Coordinates lookup, analysis, evidence validation, and next-step decisions.
- **Tool execution:** Exposes an order lookup tool to the model.
- **Execution bounds:** Limits tool-calling rounds and configures request timeouts.
- **Output validation:** Uses Pydantic to validate structured complaint analyses.
- **Evidence-aware behavior:** Instructs the model to distinguish confirmed facts from assumptions and avoid inventing information.
- **Failure handling:** Supports fallback analysis and human-review flags for cases that cannot be safely completed.
- **Testing and evaluation:** Provides automated tests and example evaluation scenarios.

The harness is being developed iteratively. Further work includes strengthening provider-error recovery, improving execution observability, and expanding systematic agent evaluations.

## Architecture

```text
Customer Complaint
        |
        v
FastAPI Request Validation
        |
        v
LangGraph Workflow
        |
        v
Order Lookup
        |
        v
Complaint Analysis with Gemini
        |
        +---- Tool Call When Needed
        |
        v
Evidence and Output Validation
        |
        v
Next-Step Decision
        |
        +---- Analysis Result
        |
        +---- Human Review When Needed
```

LangChain handles model interactions and tool calling, while LangGraph organizes the application workflow. Pydantic defines the data contracts shared across the application.

## Project Structure

```text
OrderMind-AI/
├── app/
│   ├── agent/
│   │   └── order_graph.py
│   ├── core/
│   │   ├── config.py
│   │   └── llm.py
│   ├── evaluation/
│   │   └── evaluate_agent.py
│   ├── routes/
│   ├── schemas/
│   │   └── orders.py
│   ├── services/
│   │   └── order_analysis.py
│   ├── tools/
│   │   └── order_lookup.py
│   └── main.py
├── frontend/
│   └── app.py
├── tests/
├── .env.example
├── pyproject.toml
└── README.md
```

## Getting Started

### Requirements

- Python 3.11 or newer
- A Google Gemini API key
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Julianapw/OrderMind-AI.git
cd OrderMind-AI
```

### 2. Create and Activate a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install -e ".[dev]"
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and configure the Gemini API key and model according to the application's settings.

Never commit `.env` or expose API credentials in logs, screenshots, or source code.

### 5. Start the API

```bash
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to explore the API.

### 6. Start the Frontend

In a separate terminal, activate the virtual environment and run:

```bash
streamlit run frontend/app.py
```

The frontend uses `http://127.0.0.1:8000/api/v1` by default. Configure `API_URL` if the backend runs elsewhere.

## Example API Request

**Endpoint:** `POST /api/v1/orders/analyze`

```json
{
  "order_id": "PED-1001",
  "customer_message": "My order arrived without the french fries."
}
```

The application retrieves the order, investigates the complaint, and returns a structured analysis when execution succeeds. The analysis schema includes:

- `confirmed_facts`
- `evidence`
- `complaint_assessment`
- `recommended_next_step`
- `missing_information`
- `requires_human_review`

The result depends on the available order data and successful execution of the model workflow. An unresolved provider error should not be interpreted as a successful analysis.

## Running Tests

Run the automated test suite:

```bash
pytest -v
```

The automated tests use simulated model responses for relevant scenarios, so they can validate application logic without requiring a successful live Gemini request.

Live integration tests should be run separately when the model API is available.

## Reliability and Safety Principles

1. **Evidence over assumptions:** Do not present unverified events as facts.
2. **Bounded execution:** Limit tool-calling iterations.
3. **Validated outputs:** Use explicit schemas for structured analysis.
4. **Controlled failure:** Flag cases that cannot be safely completed.
5. **Human oversight:** Identify cases that need additional review.
6. **Separation of concerns:** Keep API routes, schemas, tools, orchestration, and model integration in separate modules.

## Limitations

- The order dataset is fictional and intended for demonstration.
- The