# Frontend setup

The React interface has two views:

- **Overview** shows catalog totals, stock value, product categories, and items that need attention.
- **Products** supports search, category and stock filters, sorting, pagination, and a product-details panel.
- **New Order** lets you select a customer, add catalog products, change quantities, see backend-aligned totals, and save a draft.
- **Orders** lists the saved drafts.

Sign in to use the workspace. Admins can add/edit products, update stock, and add/edit customers. Staff can use AI intake and order drafting and process orders, but cannot edit product, stock, or customer records. Configure both accounts and the token signing secret in the backend environment; see [backend setup](backend-setup.md).

It reads products from the FastAPI backend through Vite's local `/api` proxy. The browser only needs the frontend at port 5173; the proxy sends catalog calls to the backend at port 8000.

## Run locally in Git Bash

Use two terminals.

Terminal 1 — backend:

```bash
cd /c/Users/PC/Documents/ai-order-desk/backend
./.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Terminal 2 — frontend:

```bash
cd /c/Users/PC/Documents/ai-order-desk/frontend
npm run dev
```

Open http://127.0.0.1:5173. If the catalog is empty, seed it from the backend directory:

```bash
./.venv/Scripts/python.exe -m app.seed
```

## Validation

From `frontend`:

```bash
npm run build
npm test
```

The browser tests use the fictional sample catalog. They check catalog summaries, product search and filters, sorting, pagination, the details panel, error recovery, empty states, multi-page API loading, and mobile navigation.

`npm run build` produces `frontend/dist/`, which is ignored by Git.
