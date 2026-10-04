# Backend setup

Run these commands in PowerShell:

```powershell
cd C:\Users\PC\Documents\ai-order-desk\backend
Copy-Item .env.example .env
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1
```

Open http://127.0.0.1:8000/docs for interactive API documentation. Sign in at **POST /auth/login** and use the returned bearer token with the **Authorize** button before calling protected endpoints. The local demo accounts are listed in `backend/.env.example`. Admins can use **POST /products**, click **Try it out**, and submit:

```json
{
  "sku": "CHG-025",
  "name": "Samsung 25W charger",
  "category": "Chargers",
  "price": "12.99",
  "stock": 30
}
```

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /health | Check API is running |
| POST | /auth/login | Sign in as admin or staff and receive a role-bearing token |
| POST | /products | Create a product |
| GET | /products | List products; optional q, offset, limit |
| GET | /products/{id} | Read one product |
| PUT | /products/{id} | Replace all editable fields |
| POST | /customers | Create a customer |
| PUT | /customers/{id} | Replace editable customer fields |
| GET | /customers | List customers |
| POST | /orders | Create a manual order draft |
| GET | /orders | List order drafts, newest first |
| GET | /orders/{id} | Read one order draft |

Price is a decimal amount in the shop's single currency (two decimal places), returned as a JSON string to preserve precision. SQLite stores integer cents. Stock must be a nonnegative integer. SKUs are trimmed, uppercased, and unique; they support letters, digits, hyphens, and underscores. A duplicate SKU returns 409; invalid input returns 422; missing products return 404.

Except for `/health` and `/auth/login`, API endpoints require a valid bearer token. Admin tokens can create and edit products (including direct stock corrections) and customers. Staff tokens can read the catalog/customer list, analyze intake, create orders, and approve, dispatch, or cancel orders. Dispatch records its stock change as a stock movement. Staff cannot create or edit catalog/customer records.

The SQLite database is created automatically at backend/data/orders.sqlite3, independently of the working directory. It is excluded from Git. No sample products are inserted automatically. To add the 50 demo products, run the seed command below.

The lock file records the dependency versions tested on Windows with Python 3.14. The requirements files define the direct dependencies for future updates.

## Tests

From backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use temporary databases and do not modify the application database.

## Authentication setup

The backend reads `backend/.env` at startup and lets explicitly set shell variables override it. Copy `.env.example` to `.env` once, then replace both placeholder passwords and the signing secret. For the local demo configuration in the workspace, sign in as `owner@mobileandmore.demo` with password `demo-owner-password`; the staff account uses `staff@mobileandmore.demo` and `demo-staff-password`. These demo credentials are stored only in the ignored local `.env` file. Login returns a signed bearer token with an `admin` or `staff` role.

## Current limits

Order drafts snapshot the product SKU, name, and catalog unit price at creation. The API accepts only customer ID, product IDs, and quantities; it calculates totals in integer cents and checks quantities against stock on hand. A draft does not reserve stock.

An approved order reserves its item quantities. A second approval cannot claim stock already reserved by another approved order. Dispatch changes physical stock once and writes a `stock_movements` record. Cancelling an approved order releases its reservation; cancelled and dispatched orders cannot be approved again.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | /orders/{id}/approve | Approve a draft and reserve stock |
| POST | /orders/{id}/dispatch | Dispatch an approved order and deduct stock |
| POST | /orders/{id}/cancel | Cancel a draft or release an approved reservation |

Seed the 10 fictional wholesale customers with:

```bash
./.venv/Scripts/python.exe -m app.seed_customers
```

The seed is safe to rerun: it skips existing customer names and preserves records.

## Current limits

Local development API only. Admins can directly set catalog stock through product editing; dispatches performed by staff create stock movement records. Receiving workflows and schema migrations remain future work.

## References

- [FastAPI database guide](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [SQLAlchemy SQLite documentation](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)


## Git Bash: run and seed

```bash
cd /c/Users/PC/Documents/ai-order-desk/backend
./.venv/Scripts/python.exe -m app.seed
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Seeding skips existing SKUs and preserves edits. The sample catalog includes 12 chargers, 14 cables, 14 cases, and 10 headphones. Prices and quantities are fictional. View them at http://127.0.0.1:8000/products?limit=100 or execute GET /products in the interactive documentation.
