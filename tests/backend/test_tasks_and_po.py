"""
Tests for task and purchase order API endpoints.
"""
import pytest


class TestTaskEndpoints:
    """Test suite for task CRUD endpoints."""

    def test_get_tasks_empty(self, client):
        """Test getting tasks returns 200 with list."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_task(self, client):
        """Test creating a new task."""
        task_data = {"title": "Test task", "priority": "high", "status": "pending"}
        response = client.post("/api/tasks", json=task_data)
        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "Test task"
        assert data["priority"] == "high"
        assert data["status"] == "pending"
        assert "id" in data

    def test_create_task_minimal(self, client):
        """Test creating a task with only required fields."""
        task_data = {"title": "Minimal task"}
        response = client.post("/api/tasks", json=task_data)
        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "Minimal task"
        assert data["priority"] == "medium"  # default
        assert data["status"] == "pending"  # default

    def test_create_task_empty_title_rejected(self, client):
        """Test that empty title is rejected."""
        task_data = {"title": ""}
        response = client.post("/api/tasks", json=task_data)
        assert response.status_code == 422

    def test_toggle_task(self, client):
        """Test toggling a task's status."""
        # Create a task first
        task_data = {"title": "Toggle me"}
        create_resp = client.post("/api/tasks", json=task_data)
        task_id = create_resp.json()["id"]

        # Toggle to completed
        response = client.patch(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

        # Toggle back to pending
        response = client.patch(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    def test_delete_task(self, client):
        """Test deleting a task."""
        # Create a task first
        task_data = {"title": "Delete me"}
        create_resp = client.post("/api/tasks", json=task_data)
        task_id = create_resp.json()["id"]

        # Delete it
        response = client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 200

    def test_delete_nonexistent_task(self, client):
        """Test deleting a task that doesn't exist returns 404."""
        response = client.delete("/api/tasks/nonexistent-id")
        assert response.status_code == 404

    def test_toggle_nonexistent_task(self, client):
        """Test toggling a task that doesn't exist returns 404."""
        response = client.patch("/api/tasks/nonexistent-id")
        assert response.status_code == 404


class TestPurchaseOrderEndpoints:
    """Test suite for purchase order endpoints."""

    def test_get_purchase_order_by_backlog_item(self, client):
        """Test getting a purchase order by backlog item ID."""
        # First get backlog items to find one with a PO
        backlog_resp = client.get("/api/backlog")
        backlog_items = backlog_resp.json()

        items_with_po = [item for item in backlog_items if item.get("has_purchase_order")]
        if items_with_po:
            item_id = items_with_po[0]["id"]
            response = client.get(f"/api/purchase-orders/{item_id}")
            assert response.status_code == 200

            data = response.json()
            assert data["backlog_item_id"] == item_id
            assert "supplier_name" in data
            assert "quantity" in data

    def test_get_nonexistent_purchase_order(self, client):
        """Test getting PO for non-existent backlog item returns 404."""
        response = client.get("/api/purchase-orders/nonexistent-id")
        assert response.status_code == 404

    def test_create_purchase_order(self, client):
        """Test creating a purchase order."""
        # Get a backlog item to reference
        backlog_resp = client.get("/api/backlog")
        backlog_items = backlog_resp.json()
        assert len(backlog_items) > 0

        # Find one without a PO
        items_without_po = [item for item in backlog_items if not item.get("has_purchase_order")]
        if not items_without_po:
            pytest.skip("All backlog items already have purchase orders")

        target = items_without_po[0]
        po_data = {
            "backlog_item_id": target["id"],
            "supplier_name": "Test Supplier Co",
            "quantity": 100,
            "unit_cost": 25.50,
            "expected_delivery_date": "2025-12-01T00:00:00",
            "notes": "Test purchase order"
        }

        response = client.post("/api/purchase-orders", json=po_data)
        assert response.status_code == 201

        data = response.json()
        assert data["backlog_item_id"] == target["id"]
        assert data["supplier_name"] == "Test Supplier Co"
        assert data["status"] == "Pending"

    def test_create_purchase_order_invalid_backlog_item(self, client):
        """Test creating PO with non-existent backlog item returns 404."""
        po_data = {
            "backlog_item_id": "nonexistent-id",
            "supplier_name": "Test Supplier",
            "quantity": 100,
            "unit_cost": 25.50,
            "expected_delivery_date": "2025-12-01T00:00:00"
        }

        response = client.post("/api/purchase-orders", json=po_data)
        assert response.status_code == 404


class TestOrderEndpoint:
    """Test suite for individual order retrieval."""

    def test_get_order_by_id(self, client):
        """Test getting a specific order by ID."""
        # Get all orders first
        all_resp = client.get("/api/orders")
        all_orders = all_resp.json()
        assert len(all_orders) > 0

        first_order = all_orders[0]
        response = client.get(f"/api/orders/{first_order['id']}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == first_order["id"]
        assert "items" in data
        assert "status" in data

    def test_get_nonexistent_order(self, client):
        """Test getting non-existent order returns 404."""
        response = client.get("/api/orders/nonexistent-999")
        assert response.status_code == 404


class TestInputValidation:
    """Test suite for input validation on endpoints."""

    def test_negative_budget_rejected(self, client):
        """Test that negative budget is rejected with 422."""
        response = client.get("/api/restocking/recommend?budget=-1000")
        assert response.status_code == 422

    def test_zero_budget_rejected(self, client):
        """Test that zero budget is rejected with 422."""
        response = client.get("/api/restocking/recommend?budget=0")
        assert response.status_code == 422

    def test_excessive_budget_rejected(self, client):
        """Test that budget exceeding max is rejected."""
        response = client.get("/api/restocking/recommend?budget=9999999")
        assert response.status_code == 422

    def test_valid_budget_accepted(self, client):
        """Test that valid budget works."""
        response = client.get("/api/restocking/recommend?budget=5000")
        assert response.status_code == 200

    def test_nonexistent_warehouse_filter_returns_empty(self, client):
        """Test that filtering by non-existent warehouse returns empty list."""
        response = client.get("/api/inventory?warehouse=NonExistent")
        assert response.status_code == 200
        assert response.json() == []

    def test_nonexistent_category_filter_returns_empty(self, client):
        """Test that filtering by non-existent category returns empty list."""
        response = client.get("/api/orders?category=NonExistent")
        assert response.status_code == 200
        assert response.json() == []

    def test_restocking_order_negative_quantity_rejected(self, client):
        """Test that negative quantity in restocking order is rejected."""
        order_data = {
            "items": [{"item_sku": "TEST", "item_name": "Test", "quantity": -10, "unit_cost": 5.0}],
            "total_value": 50.0
        }
        response = client.post("/api/restocking/order", json=order_data)
        assert response.status_code == 422

    def test_restocking_order_zero_total_rejected(self, client):
        """Test that zero total_value in restocking order is rejected."""
        order_data = {
            "items": [{"item_sku": "TEST", "item_name": "Test", "quantity": 10, "unit_cost": 5.0}],
            "total_value": 0
        }
        response = client.post("/api/restocking/order", json=order_data)
        assert response.status_code == 422

    def test_restocking_order_empty_items_rejected(self, client):
        """Test that empty items list is rejected."""
        order_data = {
            "items": [],
            "total_value": 100
        }
        response = client.post("/api/restocking/order", json=order_data)
        assert response.status_code == 422
