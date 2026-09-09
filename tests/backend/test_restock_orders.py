"""
Tests for the restocking order endpoints (GET/POST /api/restock-orders).
"""
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def sample_restock_payload():
    """A valid create-restock-order request body."""
    return {
        "items": [
            {
                "sku": "MTR-304",
                "name": "Electric Motor 5HP",
                "quantity": 10,
                "unit_price": 450.0,
            }
        ],
        "total_value": 4500.0,
        "budget": 100000,
    }


class TestRestockOrderEndpoints:
    """Test suite for the restocking order endpoints."""

    def test_get_restock_orders_returns_list(self, client):
        """GET /api/restock-orders returns a list."""
        response = client.get("/api/restock-orders")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_restock_order(self, client, sample_restock_payload):
        """POST creates a Submitted order with a 7-day lead time."""
        response = client.post("/api/restock-orders", json=sample_restock_payload)
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"].startswith("RSO-")
        assert order["status"] == "Submitted"
        assert order["lead_time_days"] == 7
        assert order["total_value"] == 4500.0
        assert len(order["items"]) == 1

        order_date = datetime.fromisoformat(order["order_date"])
        expected_delivery = datetime.fromisoformat(order["expected_delivery"])
        assert expected_delivery - order_date == timedelta(days=7)

    def test_created_order_appears_in_list(self, client, sample_restock_payload):
        """An order submitted via POST is then visible via GET."""
        created = client.post("/api/restock-orders", json=sample_restock_payload).json()

        listed = client.get("/api/restock-orders").json()
        assert any(o["order_number"] == created["order_number"] for o in listed)

    def test_create_restock_order_missing_total_value(self, client):
        """POST without total_value fails validation with 422."""
        response = client.post("/api/restock-orders", json={"items": []})
        assert response.status_code == 422
