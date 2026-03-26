"""Tests for restocking recommendation and order endpoints."""


def test_get_recommendations_basic(client):
    """Basic recommendation request returns expected structure."""
    response = client.get("/api/restocking/recommend?budget=10000")
    assert response.status_code == 200
    data = response.json()
    assert "budget" in data
    assert "total_cost" in data
    assert "remaining_budget" in data
    assert "items" in data
    assert data["budget"] == 10000
    assert data["total_cost"] + data["remaining_budget"] == data["budget"]
    assert len(data["items"]) > 0


def test_get_recommendations_item_structure(client):
    """Each recommended item has the expected fields."""
    response = client.get("/api/restocking/recommend?budget=50000")
    data = response.json()
    for item in data["items"]:
        assert "item_sku" in item
        assert "item_name" in item
        assert "demand_gap" in item
        assert "unit_cost" in item
        assert "quantity" in item
        assert "line_cost" in item
        assert item["quantity"] > 0
        assert item["demand_gap"] > 0


def test_get_recommendations_excludes_negative_gap(client):
    """MTR-304 has decreasing demand (gap = -15) and should never appear."""
    response = client.get("/api/restocking/recommend?budget=100000")
    data = response.json()
    skus = [item["item_sku"] for item in data["items"]]
    assert "MTR-304" not in skus


def test_get_recommendations_sorted_by_demand_gap(client):
    """Items should be sorted by demand gap descending."""
    response = client.get("/api/restocking/recommend?budget=100000")
    data = response.json()
    gaps = [item["demand_gap"] for item in data["items"]]
    assert gaps == sorted(gaps, reverse=True)


def test_get_recommendations_budget_constraint(client):
    """Total cost should not exceed the budget."""
    response = client.get("/api/restocking/recommend?budget=500")
    data = response.json()
    assert data["total_cost"] <= 500
    assert data["remaining_budget"] >= 0


def test_get_recommendations_zero_budget(client):
    """Zero budget should return no items."""
    response = client.get("/api/restocking/recommend?budget=0")
    data = response.json()
    assert len(data["items"]) == 0
    assert data["total_cost"] == 0
    assert data["remaining_budget"] == 0


def test_get_recommendations_large_budget(client):
    """Large budget should include all positive-gap items at full quantity."""
    response = client.get("/api/restocking/recommend?budget=100000")
    data = response.json()
    # There are 8 items with positive demand gap (all except MTR-304)
    assert len(data["items"]) == 8
    for item in data["items"]:
        # Each item should be filled to its full demand gap
        assert item["quantity"] == item["demand_gap"]


def test_get_recommendations_partial_fill(client):
    """Small budget forces partial fill on expensive items."""
    # GSK-203 has gap=100, unit_cost=8.75, full cost=875
    # Use a budget that can only partially fill it
    response = client.get("/api/restocking/recommend?budget=50")
    data = response.json()
    assert data["total_cost"] <= 50
    if len(data["items"]) > 0:
        for item in data["items"]:
            assert item["line_cost"] <= 50


def test_submit_restocking_order(client):
    """Submitting a restocking order creates a new order."""
    order_data = {
        "items": [
            {"item_sku": "WDG-001", "item_name": "Industrial Widget Type A", "quantity": 50, "unit_cost": 24.50},
            {"item_sku": "GSK-203", "item_name": "High-Temperature Gasket", "quantity": 30, "unit_cost": 8.75}
        ],
        "total_value": 1487.50
    }
    response = client.post("/api/restocking/order", json=order_data)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "Restocking"
    assert data["customer"] == "Internal Restocking"
    assert data["total_value"] == 1487.50
    assert len(data["items"]) == 2
    assert data["order_number"].startswith("ORD-2025-")
    assert data["expected_delivery"] is not None


def test_submit_order_appears_in_orders(client):
    """A submitted restocking order should appear in GET /api/orders."""
    order_data = {
        "items": [
            {"item_sku": "FLT-405", "item_name": "Oil Filter Cartridge", "quantity": 10, "unit_cost": 12.50}
        ],
        "total_value": 125.00
    }
    client.post("/api/restocking/order", json=order_data)

    response = client.get("/api/orders")
    assert response.status_code == 200
    orders = response.json()
    restocking_orders = [o for o in orders if o["status"] == "Restocking"]
    assert len(restocking_orders) >= 1


def test_submit_order_lead_time_short(client):
    """Orders with total quantity < 100 should have 7-day lead time."""
    order_data = {
        "items": [
            {"item_sku": "WDG-001", "item_name": "Widget", "quantity": 50, "unit_cost": 24.50}
        ],
        "total_value": 1225.00
    }
    response = client.post("/api/restocking/order", json=order_data)
    data = response.json()
    from datetime import datetime
    order_date = datetime.fromisoformat(data["order_date"])
    delivery_date = datetime.fromisoformat(data["expected_delivery"])
    delta = (delivery_date - order_date).days
    assert delta == 7


def test_submit_order_lead_time_medium(client):
    """Orders with total quantity 100-500 should have 14-day lead time."""
    order_data = {
        "items": [
            {"item_sku": "WDG-001", "item_name": "Widget", "quantity": 300, "unit_cost": 24.50}
        ],
        "total_value": 7350.00
    }
    response = client.post("/api/restocking/order", json=order_data)
    data = response.json()
    from datetime import datetime
    order_date = datetime.fromisoformat(data["order_date"])
    delivery_date = datetime.fromisoformat(data["expected_delivery"])
    delta = (delivery_date - order_date).days
    assert delta == 14


def test_submit_order_lead_time_long(client):
    """Orders with total quantity > 500 should have 21-day lead time."""
    order_data = {
        "items": [
            {"item_sku": "WDG-001", "item_name": "Widget", "quantity": 600, "unit_cost": 24.50}
        ],
        "total_value": 14700.00
    }
    response = client.post("/api/restocking/order", json=order_data)
    data = response.json()
    from datetime import datetime
    order_date = datetime.fromisoformat(data["order_date"])
    delivery_date = datetime.fromisoformat(data["expected_delivery"])
    delta = (delivery_date - order_date).days
    assert delta == 21
