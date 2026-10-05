from fastapi.testclient import TestClient
import pytest

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(f"sqlite:///{(tmp_path / 'phones.sqlite3').as_posix()}")) as test_client:
        token = test_client.post('/auth/login', json={'email': 'owner@mobileandmore.demo', 'password': 'demo-owner-password'}).json()['token']
        test_client.headers.update({'Authorization': f'Bearer {token}'})
        yield test_client


def create_phone_product(client):
    response = client.post('/products', json={'sku': 'IPH-15-128', 'name': 'iPhone 15', 'category': 'Phones', 'price': '799.00', 'stock': 0})
    assert response.status_code == 201
    return response.json()


def create_customer(client):
    response = client.post('/customers', json={'name': 'Phone Buyer', 'contact_name': 'Mira Saleh', 'phone': '+9613000000', 'email': 'mira@example.test'})
    assert response.status_code == 201
    return response.json()


def add_unit(client, product_id, imei='356938035643809'):
    return client.post('/phone-units', json={'product_id': product_id, 'imei': imei, 'colour': 'Black', 'storage': '128GB', 'supplier_name': 'Demo supplier', 'purchase_cost': '650.00', 'warranty_status': '12-month warranty'})


def test_phone_unit_has_unique_imei_and_increases_phone_stock(client):
    product = create_phone_product(client)
    created = add_unit(client, product['id'])
    assert created.status_code == 201
    assert created.json()['status'] == 'available'
    assert created.json()['purchase_cost'] == '650.00'
    assert client.get(f"/products/{product['id']}").json()['stock'] == 1
    assert add_unit(client, product['id']).status_code == 409


def test_phone_unit_is_reserved_then_dispatched_with_its_order(client):
    product = create_phone_product(client)
    unit = add_unit(client, product['id']).json()
    customer = create_customer(client)
    order = client.post('/orders', json={'customer_id': customer['id'], 'items': [{'product_id': product['id'], 'quantity': 1, 'phone_unit_id': unit['id']}]}).json()
    assert client.post(f"/orders/{order['id']}/approve").status_code == 200
    assert client.get('/phone-units').json()[0]['status'] == 'reserved'
    assert client.post(f"/orders/{order['id']}/dispatch").status_code == 200
    assert client.get('/phone-units').json()[0]['status'] == 'dispatched'
    assert client.get(f"/products/{product['id']}").json()['stock'] == 0


def test_phone_order_requires_an_individual_unit(client):
    product = create_phone_product(client)
    add_unit(client, product['id'])
    customer = create_customer(client)
    response = client.post('/orders', json={'customer_id': customer['id'], 'items': [{'product_id': product['id'], 'quantity': 1}]})
    assert response.status_code == 422
    assert response.json()['detail'] == 'Select an individual phone unit for phone orders'


def test_cancelling_an_approved_phone_order_releases_the_unit(client):
    product = create_phone_product(client)
    unit = add_unit(client, product['id']).json()
    customer = create_customer(client)
    order = client.post('/orders', json={'customer_id': customer['id'], 'items': [{'product_id': product['id'], 'quantity': 1, 'phone_unit_id': unit['id']}]}).json()
    assert client.post(f"/orders/{order['id']}/approve").status_code == 200
    assert client.post(f"/orders/{order['id']}/cancel").status_code == 200
    assert client.get('/phone-units').json()[0]['status'] == 'available'
