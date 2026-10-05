from fastapi.testclient import TestClient

from app.main import create_app


def login(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": "owner@mobileandmore.demo", "password": "demo-owner-password"})
    client.headers["Authorization"] = f"Bearer {response.json()['token']}"


def test_imports_barcode_and_creates_individual_phone_units(tmp_path):
    with TestClient(create_app(f"sqlite:///{(tmp_path / 'imports.sqlite3').as_posix()}")) as client:
        login(client)
        csv_text = """SKU,Product Name,Category,Price,Stock Quantity,Barcode,IMEI,Colour,Storage,Supplier,Purchase Cost,Warranty Status
ACC-001,USB-C Charger,Chargers,19.99,7,8501234567890,,,,,,
PHONE-001,Demo Phone,Phones,899.00,1,194253000001,356938035643809,Black,128GB,Demo Supply,720.00,12 months
PHONE-001,Demo Phone,Phones,899.00,1,194253000001,356938035643817,Black,128GB,Demo Supply,720.00,12 months
"""
        preview = client.post("/imports/products/preview", files={"file": ("inventory.csv", csv_text, "text/csv")})
        assert preview.status_code == 200
        assert preview.json()["errors"] == []
        assert preview.json()["rows"][1]["phone_unit_action"] == "add"
        applied = client.post("/imports/products/apply?confirm=true", files={"file": ("inventory.csv", csv_text, "text/csv")})
        assert applied.status_code == 200
        products = {product["sku"]: product for product in client.get("/products?limit=100").json()}
        assert products["ACC-001"]["barcode"] == "8501234567890"
        assert products["PHONE-001"]["stock"] == 2
        units = client.get(f"/phone-units?product_id={products['PHONE-001']['id']}").json()
        assert {unit["imei"] for unit in units} == {"356938035643809", "356938035643817"}


def test_rejects_in_stock_phone_without_imei(tmp_path):
    with TestClient(create_app(f"sqlite:///{(tmp_path / 'invalid-import.sqlite3').as_posix()}")) as client:
        login(client)
        csv_text = "SKU,Product Name,Category,Price,Stock Quantity\nPHONE-001,Demo Phone,Phones,899.00,2\n"
        preview = client.post("/imports/products/preview", files={"file": ("inventory.csv", csv_text, "text/csv")})
        assert preview.status_code == 200
        assert "IMEI" in preview.json()["errors"][0]
