import pytest


@pytest.fixture(autouse=True)
def demo_auth_environment(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "owner@mobileandmore.demo")
    monkeypatch.setenv("ADMIN_PASSWORD", "demo-owner-password")
    monkeypatch.setenv("STAFF_EMAIL", "staff@mobileandmore.demo")
    monkeypatch.setenv("STAFF_PASSWORD", "demo-staff-password")
    monkeypatch.setenv("ADMIN_TOKEN_SECRET", "test-only-order-desk-token-secret")
