"""Load fictional wholesale customers without modifying existing customer records."""

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.dialects.sqlite import insert

from .main import DEFAULT_DATABASE
from .models import Base, Customer
from .schemas import CustomerInput

SAMPLE_CUSTOMERS = Path(__file__).resolve().parents[2] / "sample-data" / "customers.json"


def seed_customers(database_url: str | None = None, source: Path = SAMPLE_CUSTOMERS) -> tuple[int, int]:
    rows = json.loads(source.read_text(encoding="utf-8-sig"))
    customers = [CustomerInput.model_validate(row) for row in rows]
    names = [customer.name.casefold() for customer in customers]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate customer names in seed data")
    if database_url is None:
        DEFAULT_DATABASE.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{DEFAULT_DATABASE.as_posix()}"
    engine = create_engine(database_url)
    added = 0
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            for customer in customers:
                statement = insert(Customer).values(**customer.model_dump()).on_conflict_do_nothing(
                    index_elements=["name"]
                )
                added += connection.execute(statement).rowcount
    finally:
        engine.dispose()
    return added, len(customers) - added


if __name__ == "__main__":
    added, skipped = seed_customers()
    print(f"Added {added} customers; skipped {skipped} existing customers.")
