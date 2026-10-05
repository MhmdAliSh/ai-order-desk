import os

from fastapi.testclient import TestClient

from app.auth import load_local_environment
from app.main import create_app


def login(client, email, password):
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    client.headers["Authorization"] = f"Bearer {response.json()['token']}"
    return response.json()


def product_body():
    return {"sku": "ROLE-001", "name": "Demo charger", "category": "Chargers", "price": "10.00", "stock": 12}


def customer_body():
    return {"name": "Fictional Mobile", "contact_name": "Sam Example", "phone": "000-0000", "email": "sam@example.test"}


def test_local_environment_file_fills_missing_values_without_overriding_shell(monkeypatch, tmp_path):
    local_env = tmp_path / ".env"
    local_env.write_text("ORDERDESK_TEST_FILE_VALUE=from-file\nORDERDESK_TEST_OVERRIDE=file-value\n", encoding="utf-8")
    monkeypatch.delenv("ORDERDESK_TEST_FILE_VALUE", raising=False)
    monkeypatch.setenv("ORDERDESK_TEST_OVERRIDE", "from-shell")

    load_local_environment(local_env)

    assert os.environ["ORDERDESK_TEST_FILE_VALUE"] == "from-file"
    assert os.environ["ORDERDESK_TEST_OVERRIDE"] == "from-shell"


def test_login_fails_safely_when_credentials_or_signing_secret_are_missing(monkeypatch, tmp_path):
    for name in ("ADMIN_EMAIL", "ADMIN_PASSWORD", "STAFF_EMAIL", "STAFF_PASSWORD", "ADMIN_TOKEN_SECRET"):
        monkeypatch.delenv(name, raising=False)
    with TestClient(create_app(f"sqlite:///{(tmp_path / 'unconfigured.sqlite3').as_posix()}")) as client:
        response = client.post("/auth/login", json={"email": "owner@example.test", "password": "owner-test-password"})
        assert response.status_code == 503
        assert response.json()["detail"].startswith("Authentication is not configured")


def test_role_login_and_admin_only_catalog_and_customer_management(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_TOKEN_SECRET", "test-secret")
    monkeypatch.setenv("ADMIN_EMAIL", "owner@example.test")
    monkeypatch.setenv("ADMIN_PASSWORD", "owner-test-password")
    monkeypatch.setenv("STAFF_EMAIL", "staff@example.test")
    monkeypatch.setenv("STAFF_PASSWORD", "staff-test-password")
    with TestClient(create_app(f"sqlite:///{(tmp_path / 'roles.sqlite3').as_posix()}")) as client:
        assert client.get("/products").status_code == 401
        staff = login(client, "staff@example.test", "staff-test-password")
        assert staff["role"] == "staff"
        assert client.post("/products", json=product_body()).status_code == 403
        assert client.post("/customers", json=customer_body()).status_code == 403

        client.headers.pop("Authorization")
        admin = login(client, "owner@example.test", "owner-test-password")
        assert admin["role"] == "admin"
        product = client.post("/products", json=product_body()).json()
        customer = client.post("/customers", json=customer_body()).json()
        changed_product = {**product_body(), "stock": 9}
        assert client.put(f"/products/{product['id']}", json=changed_product).json()["stock"] == 9
        changed_customer = {**customer_body(), "contact_name": "Updated Example"}
        assert client.put(f"/customers/{customer['id']}", json=changed_customer).json()["contact_name"] == "Updated Example"
        accepted = client.put(f"/operations/restock-decisions/{product['id']}", json={"decision": "accepted", "suggested_quantity": 8})
        assert accepted.status_code == 200
        assert accepted.json()["decision"] == "accepted"
        dismissed = client.put(f"/operations/restock-decisions/{product['id']}", json={"decision": "dismissed", "suggested_quantity": 8})
        assert dismissed.status_code == 200
        assert dismissed.json()["id"] == accepted.json()["id"]
        assert dismissed.json()["decision"] == "dismissed"
        csv_text = "SKU,Product Name,Category,Price,Stock Quantity,Barcode,IMEI\nIMPORT-001,Imported cable,Cables,8.50,6,8501234567890,\n"
        preview = client.post("/imports/products/preview", files={"file": ("products.csv", csv_text, "text/csv")})
        assert preview.status_code == 200
        assert preview.json()["rows"][0]["action"] == "create"
        applied = client.post("/imports/products/apply?confirm=true", files={"file": ("products.csv", csv_text, "text/csv")})
        assert applied.status_code == 200
        assert client.get("/products").json()[-1]["sku"] == "IMPORT-001"


def test_staff_can_create_and_process_orders_but_cannot_edit_catalog(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_TOKEN_SECRET", "test-secret")
    monkeypatch.setenv("ADMIN_EMAIL", "owner@example.test")
    monkeypatch.setenv("ADMIN_PASSWORD", "owner-test-password")
    monkeypatch.setenv("STAFF_EMAIL", "staff@example.test")
    monkeypatch.setenv("STAFF_PASSWORD", "staff-test-password")
    with TestClient(create_app(f"sqlite:///{(tmp_path / 'staff.sqlite3').as_posix()}")) as client:
        login(client, "owner@example.test", "owner-test-password")
        product = client.post("/products", json=product_body()).json()
        customer = client.post("/customers", json=customer_body()).json()
        client.headers.pop("Authorization")
        login(client, "staff@example.test", "staff-test-password")

        assert client.get("/products").status_code == 200
        assert client.get("/customers").status_code == 200
        assert client.get("/integrations/whatsapp/messages").status_code == 200
        assert client.put(f"/products/{product['id']}", json={**product_body(), "stock": 0}).status_code == 403
        assert client.put(f"/customers/{customer['id']}", json=customer_body()).status_code == 403
        order = client.post("/orders", json={"customer_id": customer["id"], "items": [{"product_id": product["id"], "quantity": 2}]}).json()
        assert client.get("/orders").status_code == 200
        assert client.post(f"/orders/{order['id']}/approve").status_code == 200
        assert client.post(f"/orders/{order['id']}/dispatch").status_code == 200
        assert client.get(f"/products/{product['id']}").json()["stock"] == 10


def test_database_owner_setup_and_staff_access(monkeypatch, tmp_path):
    monkeypatch.setenv("ADMIN_TOKEN_SECRET", "database-test-secret")
    with TestClient(create_app(f"sqlite:///{(tmp_path / 'accounts.sqlite3').as_posix()}")) as client:
        assert client.get("/auth/setup-status").json() == {"needs_owner_setup": True}
        owner = client.post("/auth/setup-owner", json={"name": "Owner Example", "email": "owner@example.test", "password": "secure-owner-password"})
        assert owner.status_code == 201
        client.headers["Authorization"] = f"Bearer {owner.json()['token']}"
        staff = client.post("/users", json={"name": "Staff Example", "email": "staff@example.test", "password": "secure-staff-password", "role": "staff"})
        assert staff.status_code == 201
        assert client.get("/auth/setup-status").json() == {"needs_owner_setup": False}
        client.headers["Authorization"] = f"Bearer {client.post('/auth/login', json={'email': 'staff@example.test', 'password': 'secure-staff-password'}).json()['token']}"
        assert client.get("/products").status_code == 200
        assert client.post("/products", json=product_body()).status_code == 403
