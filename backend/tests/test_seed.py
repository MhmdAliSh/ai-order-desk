import json
from collections import Counter

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app
from app.seed import SAMPLE_PRODUCTS, seed_products


def test_seed_catalog_and_preserve_edits(tmp_path):
    url = f"sqlite:///{(tmp_path / 'seed.sqlite3').as_posix()}"
    assert seed_products(url) == (50, 0)
    with TestClient(create_app(url)) as client:
        token = client.post('/auth/login', json={'email': 'owner@mobileandmore.demo', 'password': 'demo-owner-password'}).json()['token']
        client.headers.update({'Authorization': f'Bearer {token}'})
        records = client.get('/products', params={'limit': 100}).json()
        assert len(records) == 50
        assert Counter(row['category'] for row in records) == {
            'Chargers': 12, 'Cables': 14, 'Cases': 14, 'Headphones': 10,
        }
        changed = records[0].copy()
        product_id = changed.pop('id')
        changed.update(stock=1, price='0.10', name='Owner edited product')
        assert client.put(f'/products/{product_id}', json=changed).status_code == 200
        assert seed_products(url) == (0, 50)
        stored = client.get(f'/products/{product_id}').json()
        assert stored['stock'] == 1
        assert stored['price'] == '0.10'
        assert stored['name'] == 'Owner edited product'
        assert len(client.get('/products', params={'limit': 100}).json()) == 50


@pytest.mark.parametrize('invalid_kind', ['negative_stock', 'duplicate_sku'])
def test_invalid_seed_makes_no_partial_changes(tmp_path, invalid_kind):
    url = f"sqlite:///{(tmp_path / 'seed.sqlite3').as_posix()}"
    rows = json.loads(SAMPLE_PRODUCTS.read_text(encoding='utf-8'))
    if invalid_kind == 'negative_stock':
        rows[-1]['stock'] = -1
        error = ValidationError
    else:
        rows[-1]['sku'] = rows[0]['sku'].lower()
        error = ValueError
    source = tmp_path / 'invalid.json'
    source.write_text(json.dumps(rows), encoding='utf-8')
    with pytest.raises(error):
        seed_products(url, source)
    with TestClient(create_app(url)) as client:
        token = client.post('/auth/login', json={'email': 'owner@mobileandmore.demo', 'password': 'demo-owner-password'}).json()['token']
        client.headers.update({'Authorization': f'Bearer {token}'})
        assert client.get('/products').json() == []
