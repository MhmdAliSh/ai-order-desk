# Enhancement backlog

Use this file as the source for GitHub issues. Create one issue for each unchecked item; do not create issues for completed work.

## Completed foundation

- [x] Product catalog, SQLite storage, and 50 fictional products
- [x] Searchable React dashboard and Products screen
- [x] Fictional customers and manual order drafts
- [x] Exact totals, stock checks, approval, reservation, dispatch, and cancellation
- [x] Local structured message extraction with catalog suggestions and ambiguity flags
- [x] Optional live LLM extraction provider with validated structured output; demo mode remains the default
- [x] Intake review controls for replacing suggested products, editing quantities, and dismissing unwanted items
- [x] Admin/staff sign-in with API-enforced roles; admins manage products, stock, and customers, while staff can create and process orders
- [x] Database owner onboarding with securely hashed passwords and admin-created staff accounts
- [x] Separate customer contact message and team workspace entry points; customers do not need a portal login
- [x] Local backend auth loads ignored `backend/.env` configuration while honoring shell overrides
- [x] Labeled 25-message intake evaluation dataset and automated checks for quantity, SKU, status, and item count
- [x] Initial low-stock calculations, restock suggestions, and Operations screen
- [x] Owner review records for accepting or dismissing restock suggestions; decisions never change stock or place orders
- [x] Stock movement history with dispatch reference, quantity change, reason, and timestamp

## Ready for GitHub issues

| Priority | Issue title | Labels | Completion criteria |
| --- | --- | --- | --- |
| ~~P0~~ | ~~Let employees resolve AI matches in the intake screen~~ | `enhancement`, `ai`, `frontend` | Complete: reviewers can replace a suggested product, set its quantity, or dismiss the item before saving. |
| ~~P0~~ | ~~Add role-based data management~~ | `enhancement`, `security`, `frontend`, `backend` | Complete: API routes enforce admin/staff roles; admins manage products, stock, and customers, while staff can create and process orders. |
| ~~P1~~ | ~~Add staff account UI in Admin~~ | `enhancement`, `security`, `frontend` | Complete: Admin now has a Team Accounts section to create staff or admin logins and activate or deactivate accounts. Password reset remains a separate future improvement. |
| ~~P1~~ | ~~Build a customer portal~~ | `customer`, `frontend`, `backend` | Replaced by message-channel ordering: customers should contact the shop through WhatsApp or social media without creating an account. |
| P1 | Build a message-channel order inbox | `enhancement`, `whatsapp`, `social-media`, `frontend`, `backend` | In progress: the team inbox lists stored WhatsApp messages and sends a selected message into AI review. Next: connect real channels, add social-media adapters, and record safe draft replies. No channel may approve, dispatch, or change stock automatically. |
| ~~P1~~ | ~~Add stock movement history~~ | `enhancement`, `backend`, `frontend` | Complete: dispatch movements appear in the admin Stock history screen with product, delta, reason, reference order, and timestamp. |
| ~~P1~~ | ~~Configure low-stock thresholds~~ | `enhancement`, `inventory` | Complete: admins can set per-product thresholds through the Operations API; suggestions use those values. |
| ~~P1~~ | ~~Add optional AI explanation to daily owner reports~~ | `enhancement`, `automation`, `ai` | Complete: deterministic facts remain the safe default; an optional live AI writer can explain them without changing stock. |
| P1 | Send verified stock replies through WhatsApp | `enhancement`, `whatsapp`, `automation` | For clear matched requests only, send a template-style reply based on current stock. Out-of-stock and unclear requests receive safe availability or staff-review messages. Replies stay disabled until Meta credentials are configured. |
| P1 | Manage WhatsApp connection settings in Admin | `enhancement`, `whatsapp`, `settings`, `frontend`, `backend` | Admin can edit the customer-facing WhatsApp introduction and business number in the website. Keep Meta secrets out of the browser; add connection testing and phone-number ID mapping. |
| P2 | Add CSV product and stock import | `enhancement`, `import` | In progress: admins can upload a CSV, preview valid rows and errors, then confirm a catalog update. Next: save an auditable import-history record. |
| P2 | Add GitHub Actions checks | `good first issue`, `ci` | Pull requests run backend tests and the frontend build. |
| P1 | Build a complete guided demo journey | `enhancement`, `portfolio`, `frontend` | Walk from a fictional incoming message through AI review, draft, approval, dispatch, and stock history. |
| P1 | Add import history | `enhancement`, `import`, `backend` | Record the admin, time, source filename, and created/updated row counts for every confirmed CSV import. |
| P1 | Add ready-to-order restock queue | `enhancement`, `inventory`, `frontend` | Accepted restock suggestions appear separately for supplier follow-up, without placing purchases automatically. |
| P1 | Add sales analytics | `enhancement`, `analytics`, `backend`, `frontend` | Show best sellers, slow movers, no-sale products, and category revenue for 7- and 30-day periods. |
| ~~P1~~ | ~~Add supplier records~~ | `enhancement`, `inventory`, `backend`, `frontend` | Complete: admins can add and view fictional supplier contacts, supplied SKUs, and expected lead time through the Suppliers screen. |
| P1 | Add barcode and IMEI product entry | `enhancement`, `inventory`, `frontend`, `backend` | Admins can scan or type a barcode and optionally record one IMEI for a single tracked phone unit. Barcode and IMEI values must remain unique. |
| P1 | Add in-app operational alerts | `enhancement`, `frontend`, `backend` | Surface low stock, out-of-stock products, pending orders, and failed import outcomes. |
| P2 | Add portfolio screenshots and demo video | `documentation`, `portfolio` | README contains current screenshots and a short walkthrough from customer message through review, draft, approval, and dispatch. |

## Latest verification

- Backend `pytest -q`: 70 passed, including all 25 intake evaluation cases, role permission tests, restock rules, and daily reports.
- Frontend: `npm run build` passed; `npm test -- --reporter=line`: 9 passed.

## Main branch workflow

1. Keep `main` deployable and tested.
2. Create one branch per issue: `feature/<issue-number>-short-description` or `fix/<issue-number>-short-description`.
3. Link the pull request to its issue and include validation results.
4. Merge only after backend tests and the frontend build pass.
5. Delete the feature branch after merging.

## Initial repository setup

Before creating GitHub issues:

1. Review the current files and create the first commit on `main`.
2. Create an empty GitHub repository named `ai-order-desk`.
3. Add it as `origin` and push `main`.
4. Create GitHub labels from the table above.
5. Create the P0 issues first, then use branches for implementation.
