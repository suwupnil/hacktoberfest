"""Tests for FastAPI Web Server & API Endpoints."""

import pytest
from fastapi.testclient import TestClient
from claim_sentry.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_status_endpoint(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["sandbox_isolated"] is True
    assert data["network_usage_mbps"] == 0.00
    assert data["secrets_exposed"] == 0
    assert "Apple Silicon" in data["active_model"] or "Synthesis" in data["active_model"]


def test_issues_endpoint(client):
    response = client.get("/api/issues")
    assert response.status_code == 200
    issues = response.json()
    assert len(issues) >= 10
    # Check that core scenarios exist
    titles = [i["title"] for i in issues]
    assert any("Crash on long URLs" in t for t in titles)
    assert any("RCE in parse_url_v2()" in t for t in titles)
    assert any("Fixes #120, adds tests" in t for t in titles)


def test_telemetry_endpoint(client):
    response = client.get("/api/telemetry")
    assert response.status_code == 200
    tel = response.json()
    assert tel["network_usage_mbps"] == 0.00
    assert tel["secrets_exposed"] == 0


def test_index_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "CLAIM-SENTRY" in response.text
    assert "0.00 MBPS" in response.text
