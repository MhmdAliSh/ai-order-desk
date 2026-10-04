# Sample catalog

products.json contains 50 fictional catalog records: 12 chargers, 14 cables, 14 cases, and 10 headphones. Product names illustrate compatibility and variants; they do not assert manufacturer affiliation. Prices and stock are synthetic demo values, not current market quotations. Prices use the application's single two-decimal currency convention.

customers.json contains 10 fictional wholesale customers. It uses `example` email addresses and no private data.

DEMO-prefixed SKUs separate these records from manually entered products. The catalog includes healthy, low, and zero stock for later UI and order-validation demos.

From the backend directory in Git Bash:

```bash
./.venv/Scripts/python.exe -m app.seed
```

The seed validates all records before writing, inserts them in one transaction, and skips existing SKUs without changing prices, names, or stock. It does not delete other products. It can be rerun safely.
