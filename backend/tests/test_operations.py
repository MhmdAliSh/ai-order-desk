from fastapi.testclient import TestClient
from app.main import create_app

def test_daily_summary_recommends_low_stock_for_owner(tmp_path):
    with TestClient(create_app(f"sqlite:///{(tmp_path / 'operations.sqlite3').as_posix()}")) as client:
        login = client.post('/auth/login', json={'email':'owner@mobileandmore.demo','password':'demo-owner-password'}).json()
        client.headers['Authorization'] = f"Bearer {login['token']}"
        product = client.post('/products', json={'sku':'OP-001','name':'Demo Cable','category':'Cables','price':'5.00','stock':3}).json()
        result = client.get('/operations/daily-summary')
    assert result.status_code == 200
    item = result.json()['recommendations'][0]
    assert item['product_id'] == product['id']
    assert item['reorder_quantity'] == 7

def test_daily_report_run_saves_one_report_per_day(tmp_path):
    with TestClient(create_app(f"sqlite:///{(tmp_path / 'reports.sqlite3').as_posix()}")) as client:
        login = client.post('/auth/login', json={'email':'owner@mobileandmore.demo','password':'demo-owner-password'}).json()
        client.headers['Authorization'] = f"Bearer {login['token']}"
        first = client.post('/operations/daily-reports/run')
        second = client.post('/operations/daily-reports/run')
        history = client.get('/operations/daily-reports')
    assert first.status_code == 200
    assert second.json()['id'] == first.json()['id']
    assert len(history.json()) == 1

def test_admin_can_configure_restock_threshold(tmp_path):
    with TestClient(create_app(f"sqlite:///{(tmp_path / 'threshold.sqlite3').as_posix()}")) as client:
        login = client.post('/auth/login', json={'email':'owner@mobileandmore.demo','password':'demo-owner-password'}).json()
        client.headers['Authorization'] = f"Bearer {login['token']}"
        product = client.post('/products', json={'sku':'RULE-001','name':'Demo case','category':'Cases','price':'10.00','stock':8}).json()
        rule = client.put(f"/operations/restock-rules/{product['id']}", json={'threshold':8})
        summary = client.get('/operations/daily-summary').json()
    assert rule.status_code == 200
    assert summary['recommendations'][0]['product_id'] == product['id']
