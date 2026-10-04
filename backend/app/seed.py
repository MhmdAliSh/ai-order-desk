"""Load the demo catalog without modifying existing SKUs."""
import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.dialects.sqlite import insert

from .main import DEFAULT_DATABASE
from .models import Base, Product
from .schemas import ProductInput

SAMPLE_PRODUCTS = Path(__file__).resolve().parents[2] / "sample-data" / "products.json"


def seed_products(database_url: str | None = None, source: Path = SAMPLE_PRODUCTS) -> tuple[int, int]:
    # Validate the entire input before opening a transaction or writing anything.
    rows = json.loads(source.read_text(encoding="utf-8-sig"))
    products = [ProductInput.model_validate(row) for row in rows]
    skus = [product.sku for product in products]
    if len(set(skus)) != len(skus):
        raise ValueError("Duplicate SKUs in seed data")
    if database_url is None:
        DEFAULT_DATABASE.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{DEFAULT_DATABASE.as_posix()}"
    engine = create_engine(database_url)
    added = 0
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            for product in products:
                statement = insert(Product).values(
                    sku=product.sku, name=product.name, category=product.category,
                    price_cents=int(product.price * 100), stock=product.stock,
                ).on_conflict_do_nothing(index_elements=["sku"])
                added += connection.execute(statement).rowcount
    finally:
        engine.dispose()
    return added, len(products) - added


if __name__ == "__main__":
    added, skipped = seed_products()
    print(f"Added {added} products; skipped {skipped} existing SKUs.")
