import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def database_url(tmp_path):
    return f"sqlite:///{(tmp_path / 'test.sqlite3').as_posix()}"


@pytest.fixture
def client(database_url):
    with TestClient(create_app(database_url)) as test_client:
        token = test_client.post('/auth/login', json={'email': 'owner@mobileandmore.demo', 'password': 'demo-owner-password'}).json()['token']
        test_client.headers.update({'Authorization': f'Bearer {token}'})
        yield test_client


@pytest.fixture
def product():
    return {"sku": "chg-025", "name": "Samsung 25W charger", "category": "Chargers", "price": "12.99", "stock": 30}


def test_create_read_and_persist(client, database_url, product):
    response = client.post("/products", json=product)
    assert response.status_code == 201
    created = response.json()
    assert created["sku"] == "CHG-025"
    assert created["price"] == "12.99"
    with TestClient(create_app(database_url)) as restarted:
        token = restarted.post('/auth/login', json={'email': 'owner@mobileandmore.demo', 'password': 'demo-owner-password'}).json()['token']
        restarted.headers.update({'Authorization': f'Bearer {token}'})
        assert restarted.get(f"/products/{created['id']}").json() == created


def test_duplicate_sku_does_not_change_original(client, product):
    client.post("/products", json=product)
    duplicate = dict(product, sku=" CHG-025 ", stock=99)
    assert client.post("/products", json=duplicate).status_code == 409
    records = client.get("/products").json()
    assert len(records) == 1
    assert records[0]["stock"] == 30


@pytest.mark.parametrize("field,value", [
    ("price", "-1.00"), ("price", "1.001"), ("price", "NaN"),
    ("stock", -1), ("stock", 1.5), ("stock", True),
    ("name", "   "), ("category", ""), ("sku", "bad sku"),
])
def test_invalid_input_does_not_write(client, product, field, value):
    assert client.post("/products", json=dict(product, **{field: value})).status_code == 422
    assert client.get("/products").json() == []


def test_replace_and_conflicting_update(client, product):
    first = client.post("/products", json=product).json()
    second = client.post("/products", json=dict(product, sku="CABLE-01")).json()
    path = f"/products/{first['id']}"
    response = client.put(path, json=dict(product, price="0.10", stock=0))
    assert response.status_code == 200
    assert response.json()["price"] == "0.10"
    assert response.json()["stock"] == 0
    assert client.put(path, json=dict(product, sku=second["sku"])).status_code == 409
    assert client.get(path).json()["price"] == "0.10"


def test_search_and_pagination(client, product):
    client.post("/products", json=dict(product, barcode="1234567890123"))
    client.post("/products", json=dict(product, sku="CBL-01", name="USB cable", category="Cables"))
    assert len(client.get("/products", params={"q": "charger"}).json()) == 1
    assert len(client.get("/products", params={"q": "1234567890123"}).json()) == 1
    assert client.get("/products", params={"q": "%"}).json() == []
    assert client.get("/products", params={"offset": 1, "limit": 1}).json()[0]["sku"] == "CBL-01"
    assert client.get("/products", params={"limit": 101}).status_code == 422


def test_missing_product(client, product):
    assert client.get("/products/999").status_code == 404
    assert client.put("/products/999", json=product).status_code == 404


def test_documentation_and_health(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    assert "/products" in client.get("/openapi.json").json()["paths"]
