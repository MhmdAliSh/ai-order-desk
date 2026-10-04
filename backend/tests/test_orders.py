import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'orders.sqlite3').as_posix()}"
    with TestClient(create_app(database_url)) as test_client:
        token = test_client.post('/auth/login', json={'email': 'owner@mobileandmore.demo', 'password': 'demo-owner-password'}).json()['token']
        test_client.headers.update({'Authorization': f'Bearer {token}'})
        yield test_client


def add_customer(client):
    response = client.post(
        "/customers",
        json={
            "name": "Cedar Mobile",
            "contact_name": "Rami Haddad",
            "phone": "+961 3 456 201",
            "email": "rami@cedarmobile.example",
        },
    )
    assert response.status_code == 201
    return response.json()


def add_product(client, sku="CHG-025", price="12.99", stock=30):
    response = client.post(
        "/products",
        json={"sku": sku, "name": "Samsung 25W charger", "category": "Chargers", "price": price, "stock": stock},
    )
    assert response.status_code == 201
    return response.json()


def test_customer_create_list_and_duplicate(client):
    customer = add_customer(client)
    assert client.get("/customers").json() == [customer]
    assert client.post("/customers", json={**customer, "name": "Cedar Mobile"}).status_code == 422
    duplicate = {key: value for key, value in customer.items() if key != "id"}
    assert client.post("/customers", json=duplicate).status_code == 409


def test_create_draft_uses_catalog_price_and_snapshots_items(client):
    customer = add_customer(client)
    charger = add_product(client, price="12.99", stock=30)
    cable = add_product(client, sku="CBL-001", price="3.50", stock=12)
    response = client.post(
        "/orders",
        json={"customer_id": customer["id"], "items": [
            {"product_id": charger["id"], "quantity": 2},
            {"product_id": cable["id"], "quantity": 5},
        ]},
    )
    assert response.status_code == 201
    order = response.json()
    assert order["status"] == "draft"
    assert order["total"] == "43.48"
    assert [(item["sku"], item["line_total"]) for item in order["items"]] == [
        ("CHG-025", "25.98"), ("CBL-001", "17.50"),
    ]
    assert client.get(f"/orders/{order['id']}").json() == order
    assert client.get("/orders").json() == [order]
    assert client.get(f"/products/{charger['id']}").json()["stock"] == 30


@pytest.mark.parametrize(
    "body, status_code, detail",
    [
        ({"customer_id": 99, "items": [{"product_id": 1, "quantity": 1}]}, 404, "Customer not found"),
        ({"customer_id": 1, "items": [{"product_id": 99, "quantity": 1}]}, 422, "One or more products do not exist"),
        ({"customer_id": 1, "items": [{"product_id": 1, "quantity": 31}]}, 422, "One or more quantities exceed stock on hand"),
        ({"customer_id": 1, "items": [{"product_id": 1, "quantity": 1}, {"product_id": 1, "quantity": 1}]}, 422, "Each product may appear only once in an order"),
    ],
)
def test_invalid_order_drafts_do_not_persist(client, body, status_code, detail):
    add_customer(client)
    add_product(client)
    response = client.post("/orders", json=body)
    assert response.status_code == status_code
    payload = response.json()["detail"]
    assert (payload["message"] if isinstance(payload, dict) else payload) == detail
    assert client.get("/orders").json() == []


def test_orders_are_newest_first_and_missing_order_is_404(client):
    customer = add_customer(client)
    product = add_product(client)
    first = client.post("/orders", json={"customer_id": customer["id"], "items": [{"product_id": product["id"], "quantity": 1}]}).json()
    second = client.post("/orders", json={"customer_id": customer["id"], "items": [{"product_id": product["id"], "quantity": 2}]}).json()
    assert [order["id"] for order in client.get("/orders").json()] == [second["id"], first["id"]]
    assert client.get("/orders/999").status_code == 404


def create_draft(client, customer_id, product_id, quantity):
    response = client.post("/orders", json={"customer_id": customer_id, "items": [{"product_id": product_id, "quantity": quantity}]})
    assert response.status_code == 201
    return response.json()


def test_approval_reserves_stock_then_dispatch_deducts_it(client):
    customer = add_customer(client)
    product = add_product(client, stock=5)
    order = create_draft(client, customer["id"], product["id"], 3)
    approved = client.post(f"/orders/{order['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["message"] == "Stock reserved for this order"
    assert client.get(f"/products/{product['id']}").json()["stock"] == 5
    dispatched = client.post(f"/orders/{order['id']}/dispatch")
    assert dispatched.status_code == 200
    assert dispatched.json()["status"] == "dispatched"
    assert client.get(f"/products/{product['id']}").json()["stock"] == 2
    assert client.post(f"/orders/{order['id']}/dispatch").status_code == 409
    assert client.post(f"/orders/{order['id']}/cancel").status_code == 409


def test_approval_rechecks_stock_reserved_by_another_order(client):
    customer = add_customer(client)
    product = add_product(client, stock=5)
    first = create_draft(client, customer["id"], product["id"], 3)
    second = create_draft(client, customer["id"], product["id"], 3)
    assert client.post(f"/orders/{first['id']}/approve").status_code == 200
    response = client.post(f"/orders/{second['id']}/approve")
    assert response.status_code == 422
    assert response.json()["detail"]["product_ids"] == [product["id"]]
    cancelled = client.post(f"/orders/{first['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["message"] == "Reservation released"
    assert client.post(f"/orders/{second['id']}/approve").status_code == 200


def test_invalid_order_actions_leave_stock_and_status_unchanged(client):
    customer = add_customer(client)
    product = add_product(client, stock=4)
    draft = create_draft(client, customer["id"], product["id"], 2)
    assert client.post(f"/orders/{draft['id']}/dispatch").status_code == 409
    assert client.post(f"/orders/{draft['id']}/cancel").status_code == 200
    assert client.get(f"/products/{product['id']}").json()["stock"] == 4
    assert client.get(f"/orders/{draft['id']}").json()["status"] == "cancelled"
    assert client.post(f"/orders/{draft['id']}/approve").status_code == 409
