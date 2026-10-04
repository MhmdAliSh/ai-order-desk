"""Regression evaluation for the local intake extractor and catalog matcher."""

import json
from pathlib import Path

import pytest

from app.intake import analyze_message
from app.models import Product

ROOT = Path(__file__).resolve().parents[2]
PRODUCTS_PATH = ROOT / "sample-data" / "products.json"
CASES_PATH = ROOT / "sample-data" / "intake-evaluation.json"


def load_products() -> list[Product]:
    rows = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    return [
        Product(
            id=index,
            sku=row["sku"],
            name=row["name"],
            category=row["category"],
            price_cents=round(float(row["price"]) * 100),
            stock=row["stock"],
        )
        for index, row in enumerate(rows, start=1)
    ]


CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))
PRODUCTS = load_products()


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_intake_evaluation_case(case):
    actual, _notes = analyze_message(case["message"], PRODUCTS)
    expected = case["expected"]

    assert len(actual) == len(expected), f"Unexpected item count for {case['id']}"
    for actual_item, expected_item in zip(actual, expected, strict=True):
        product = actual_item["suggested_product"]
        actual_sku = product["sku"] if product else None
        assert actual_item["quantity"] == expected_item["quantity"]
        assert actual_sku == expected_item["sku"]
        assert actual_item["match_status"] == expected_item["match_status"]


def test_intake_evaluation_dataset_has_at_least_25_fictional_cases():
    assert len(CASES) >= 25
    assert len({case["id"] for case in CASES}) == len(CASES)
