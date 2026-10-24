
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["application"] == "OrderMind"


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_existing_order():
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
    assert data["order"]["order_id"] == "PED-1001"
    assert data["order"]["restaurant"] == "Cantina da Praça"
    assert data["status"] == "received"
    assert len(data["order"]["items"]) == 3


def test_analyze_unknown_order():
    response = client.post(
        "/api/v1/orders/analyze",
        json={
            "order_id": "PED-9999",
            "customer_message": "My order never arrived.",
        },
    )

    assert response.status_code == 404
    assert "Order not found" in response.json()["detail"]


def test_reject_short_customer_message():
    response = client.post(
        "/api/v1/orders/analyze",
        json={
            "order_id": "PED-1001",
            "customer_message": "Hi",
        },
    )

    assert response.status_code == 422


def test_reject_extra_request_fields():
    response = client.post(
        "/api/v1/orders/analyze",
        json={
            "order_id": "PED-1001",
            "customer_message": "My order arrived incomplete.",
            "refund_approved": True,
        },
    )

    assert response.status_code == 422
