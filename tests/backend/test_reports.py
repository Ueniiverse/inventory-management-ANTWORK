"""
Tests for report API endpoints (/api/reports/quarterly, /api/reports/monthly-trends).
"""
import pytest


class TestQuarterlyReports:
    """Test suite for quarterly report endpoint."""

    def test_get_quarterly_reports(self, client):
        """Test getting quarterly reports returns 200 with list."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_quarterly_report_structure(self, client):
        """Test that each quarterly report has required fields."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        required_fields = [
            "quarter", "total_orders", "total_revenue",
            "delivered_orders", "avg_order_value", "fulfillment_rate"
        ]

        for report in data:
            for field in required_fields:
                assert field in report, f"Missing field: {field}"

    def test_quarterly_report_data_types(self, client):
        """Test that quarterly report fields have correct data types."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for report in data:
            assert isinstance(report["quarter"], str)
            assert isinstance(report["total_orders"], int)
            assert isinstance(report["total_revenue"], (int, float))
            assert isinstance(report["delivered_orders"], int)
            assert isinstance(report["avg_order_value"], (int, float))
            assert isinstance(report["fulfillment_rate"], (int, float))

    def test_quarterly_report_sorted_by_quarter(self, client):
        """Test that quarterly reports are sorted chronologically."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        quarters = [report["quarter"] for report in data]
        assert quarters == sorted(quarters)

    def test_quarterly_fulfillment_rate_range(self, client):
        """Test that fulfillment rate is between 0 and 100."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for report in data:
            assert 0 <= report["fulfillment_rate"] <= 100

    def test_quarterly_delivered_not_exceeds_total(self, client):
        """Test that delivered orders never exceed total orders."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for report in data:
            assert report["delivered_orders"] <= report["total_orders"]

    def test_quarterly_avg_order_value_calculation(self, client):
        """Test that avg_order_value = total_revenue / total_orders."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for report in data:
            if report["total_orders"] > 0:
                expected_avg = round(report["total_revenue"] / report["total_orders"], 2)
                assert abs(report["avg_order_value"] - expected_avg) < 0.01

    def test_quarterly_report_quarter_format(self, client):
        """Test that quarter names follow Q#-YYYY format."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        import re
        for report in data:
            assert re.match(r'^Q[1-4]-\d{4}$', report["quarter"])


class TestMonthlyTrends:
    """Test suite for monthly trends endpoint."""

    def test_get_monthly_trends(self, client):
        """Test getting monthly trends returns 200 with list."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_monthly_trends_structure(self, client):
        """Test that each month entry has required fields."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        required_fields = ["month", "order_count", "revenue", "delivered_count"]

        for entry in data:
            for field in required_fields:
                assert field in entry, f"Missing field: {field}"

    def test_monthly_trends_data_types(self, client):
        """Test that monthly trends fields have correct data types."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        for entry in data:
            assert isinstance(entry["month"], str)
            assert isinstance(entry["order_count"], int)
            assert isinstance(entry["revenue"], (int, float))
            assert isinstance(entry["delivered_count"], int)

    def test_monthly_trends_sorted_chronologically(self, client):
        """Test that monthly trends are sorted by month."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        months = [entry["month"] for entry in data]
        assert months == sorted(months)

    def test_monthly_trends_month_format(self, client):
        """Test that month follows YYYY-MM format."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        import re
        for entry in data:
            assert re.match(r'^\d{4}-\d{2}$', entry["month"])

    def test_monthly_delivered_not_exceeds_total(self, client):
        """Test that delivered_count never exceeds order_count."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        for entry in data:
            assert entry["delivered_count"] <= entry["order_count"]

    def test_monthly_non_negative_values(self, client):
        """Test that all numeric values are non-negative."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        for entry in data:
            assert entry["order_count"] >= 0
            assert entry["revenue"] >= 0
            assert entry["delivered_count"] >= 0
