# AI Order Desk — Agent Instructions

## Model selection

Do not switch models or delegate work unless the user explicitly requests it.

When the user explicitly asks for delegation, use these settings:

| Work type | Model | Reasoning effort |
| --- | --- | --- |
| Complex planning | Sol 6 | xhigh |
| Code review or smart reasoning | Sol 6 | high or medium |
| Implementation and code writing | Luna 6 | xhigh only |

Do not use Luna 6 below xhigh.

## Product principles

- AI interprets customer messages and suggests product matches.
- Deterministic backend code calculates money, validates stock, and changes order state.
- An employee reviews ambiguous product matches before creating an order.
- AI must never approve, dispatch, cancel, or otherwise execute a business action.
- Preserve order history and stock movement records.

## Development standards

- Use fictional sample data only; never add private customer data.
- Keep prices as integer cents in backend calculations.
- Add meaningful tests for business rules and regression cases.
- Verify the backend test suite and frontend build after changes.
- Keep credentials out of Git and document required environment variables in `.env.example`.
