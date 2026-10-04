import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(f"sqlite:///{(tmp_path / 'intake.sqlite3').as_posix()}")) as test_client:
        token = test_client.post('/auth/login', json={'email': 'owner@mobileandmore.demo', 'password': 'demo-owner-password'}).json()['token']
        test_client.headers.update({'Authorization': f'Bearer {token}'})
        yield test_client


def add_product(client, sku, name, stock):
    return client.post("/products", json={"sku": sku, "name": name, "category": "Accessories", "price": "10.00", "stock": stock}).json()


def test_intake_extracts_items_and_flags_review(client):
    charger = add_product(client, "CHG-25", "USB-C wall charger 25W - Black", 20)
    cable = add_product(client, "CBL-01", "USB-C to USB-C cable 1m - Black", 4)
    response = client.post("/order-intake/analyze", json={"message": "Please send 10 25W chargers and 8 USB-C cables."})
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "demo"
    assert [(item["quantity"], item["suggested_product"]["id"]) for item in payload["items"]] == [(10, charger["id"]), (8, cable["id"])]
    assert payload["items"][0]["match_status"] in {"matched", "needs_review"}
    assert payload["items"][1]["match_status"] == "unavailable"
    assert payload["notes"]


def test_intake_never_invents_missing_quantity_or_product(client):
    add_product(client, "CHG-25", "USB-C wall charger 25W - Black", 20)
    response = client.post("/order-intake/analyze", json={"message": "Please send mystery widgets and chargers."})
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["quantity"] is None for item in items)
    assert all(item["match_status"] == "needs_review" for item in items)


def test_live_mode_uses_provider_only_for_extraction(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_INTAKE_MODE", "live")
    extracted = []

    def provider(message):
        extracted.append(message)
        from app.intake import RequestedItem
        return [RequestedItem(description="25W charger", quantity=2)]

    with TestClient(create_app(f"sqlite:///{(tmp_path / 'live.sqlite3').as_posix()}", intake_extractor=provider)) as live_client:
        token = live_client.post('/auth/login', json={'email': 'owner@mobileandmore.demo', 'password': 'demo-owner-password'}).json()['token']
        live_client.headers.update({'Authorization': f'Bearer {token}'})
        charger = add_product(live_client, "CHG-25", "USB-C wall charger 25W - Black", 20)
        response = live_client.post("/order-intake/analyze", json={"message": "Send two chargers"})

    assert response.status_code == 200
    assert extracted == ["Send two chargers"]
    assert response.json()["mode"] == "live"
    assert response.json()["items"][0]["suggested_product"]["id"] == charger["id"]


@pytest.mark.parametrize("message", ["", " ", "x" * 4001])
def test_intake_validates_message(client, message):
    assert client.post("/order-intake/analyze", json={"message": message}).status_code == 422


def test_intake_ignores_greetings_and_polite_closings(client):
    charger = add_product(client, "CHG-20", "USB-C wall charger 20W - White", 20)
    response = client.post("/order-intake/analyze", json={"message": "Hello, I need 2 USB-C wall charger 20W - White, please."})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 2
    assert items[0]["suggested_product"]["id"] == charger["id"]
