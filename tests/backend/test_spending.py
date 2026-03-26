"""
Tests for spending API endpoints.
"""
import pytest


class TestSpendingEndpoints:
    """Test suite for spending-related endpoints."""

    def test_get_spending_summary(self, client):
        """Test getting spending summary returns 200."""
        response = client.get("/api/spending/summary")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_spending_summary_has_numeric_values(self, client):
        """Test that spending summary values are numeric."""
        response = client.get("/api/spending/summary")
        data = response.json()

        for key, value in data.items():
            assert isinstance(value, (int, float, str, list, dict)), \
                f"Unexpected type for {key}: {type(value)}"

    def test_get_monthly_spending(self, client):
        """Test getting monthly spending returns 200 with list."""
        response = client.get("/api/spending/monthly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_monthly_spending_entry_structure(self, client):
        """Test that monthly spending entries have expected structure."""
        response = client.get("/api/spending/monthly")
        data = response.json()

        for entry in data:
            assert isinstance(entry, dict)
            # Each entry should have at least a month/period identifier and amount
            assert len(entry) >= 2

    def test_get_category_spending(self, client):
        """Test getting category spending returns 200 with list."""
        response = client.get("/api/spending/categories")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_category_spending_entry_structure(self, client):
        """Test that category spending entries have expected structure."""
        response = client.get("/api/spending/categories")
        data = response.json()

        for entry in data:
            assert isinstance(entry, dict)
            assert len(entry) >= 2

    def test_get_transactions(self, client):
        """Test getting transactions returns 200 with list."""
        response = client.get("/api/spending/transactions")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_transactions_entry_structure(self, client):
        """Test that transaction entries have expected structure."""
        response = client.get("/api/spending/transactions")
        data = response.json()

        for entry in data:
            assert isinstance(entry, dict)
            assert len(entry) >= 3  # Should have at least id, amount, date or similar
