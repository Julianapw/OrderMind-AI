
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.orders import ComplaintAnalysis


client = TestClient(app)


def test_home():
    response = client.get("/")

    assert response.status_code == 200


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200


def test_analyze_existing_order(monkeypatch):
    def fake_analysis(order, customer_message):
        return ComplaintAnalysis(
            confirmed_facts=[
                "O pedido consta como entregue."
            ],
            evidence=[
                "Status registrado do pedido: delivered."
            ],
            complaint_assessment=(
                "A ausência das batatas fritas foi relatada "
                "pelo cliente, mas precisa ser investigada."
            ),
            recommended_next_step=(
                "Verificar com o restaurante se todos os itens "
                "foram enviados."
            ),
            missing_information=[
                "Não há confirmação de quais itens foram entregues."
            ],
            requires_human_review=True,
        )

    monkeypatch.setattr(
        "app.api.routes.analyze_order_issue",
        fake_analysis,
    )

    response = client.post(
        "/api/v1/orders/analyze",
        json={
            "order_id": "PED-1001",
            "customer_message": (
                "My order arrived without the french fries."
            ),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "analyzed"
    assert data["order"]["order_id"] == "PED-1001"
    assert data["analysis"]["requires_human_review"] is True
    assert data["analysis"]["confirmed_facts"] == [
        "O pedido consta como entregue."
    ]
    assert "precisa ser investigada" in data["message"]


def test_analyze_unknown_order():
    response = client.post(
        "/api/v1/orders/analyze",
        json={
            "order_id": "PED-9999",
            "customer_message": "Where is my order?",
        },
    )

    assert response.status_code == 404


def test_reject_short_customer_message():
    response = client.post(
        "/api/v1/orders/analyze",
        json={
            "order_id": "PED-1001",
            "customer_message": "Oi",
        },
    )

    assert response.status_code == 422


def test_reject_extra_request_fields():
    response = client.post(
        "/api/v1/orders/analyze",
        json={
            "order_id": "PED-1001",
            "customer_message": "Where is my order?",
            "unexpected_field": "not allowed",
        },
    )

    assert response.status_code == 422
