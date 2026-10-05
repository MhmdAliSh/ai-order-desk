# AGENTS.md

Guidance for anyone (people or AI agents) changing this repository. Read it before writing code.

## Project

AI Order Desk turns customer messages into staff-reviewed order drafts for a small phone shop. The backend is FastAPI + SQLAlchemy + Pydantic (`backend/app`). The frontend is React + TypeScript + Vite (`frontend/src`). Tests use pytest (`backend/tests`) and Playwright (`frontend/tests`).

The priority is a working, maintainable portfolio app. This is not an enterprise system, so prefer the simplest solution that works for a small shop.

## Where things live

- Open work (bugs, planned features, accepted risks) lives in GitHub issues in `MhmdAliSh/ai-order-desk`. Do not keep lists of open work in this file or in local notes.
- Milestones set the delivery order: Foundation, Live demo, Operations, Messaging.
- User-facing setup and usage live in `README.md`. Extra technical notes live in `docs/`.

## Non-negotiable rules

- AI suggests, people decide. Code must never approve, dispatch, cancel, buy, or send anything to a customer without an explicit human action, unless an issue explicitly asks for an opt-in setting.
- Stock, money, and order status changes live in deterministic backend code, never in AI output or browser-only logic.
- Money is stored and calculated as integer cents. Never use floats for money.
- Every stock change writes a stock movement record.
- Never silently change pricing, totals, stock, order status, or reporting behavior. Call out any such change in the issue and the pull request.
- Secrets come from environment variables. Never commit `.env` files, database files, or API keys, and never send secrets to the browser.
- Document every required environment variable in `backend/.env.example`.
- Use fictional sample data only. Never add real customer data to the repository, tests, or seed files.

## Commands

```bash
# Backend
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run build      # type check + production build
npm run test       # Playwright

# Full stack
docker compose up -d --build

# Every open issue with its labels
gh issue list --state open --limit 200 --json number,title,labels --jq '.[] | "\(.number)\t\(.title)\t\([.labels[].name]|join(","))"'

# Read one issue in full, including comments
gh issue view <number> --json title,body,labels,state,comments

# Search before opening an issue
gh issue list --state all --search "<words>"

# New branch for an issue, from the latest main
git fetch origin && git switch -c feat/<topic> origin/main
```

Run the backend tests and the frontend build before you say a change is done.

## Shell commands and RTK

- RTK (Rust Token Killer) is recommended but optional. It shortens command output before it reaches the AI model, which saves tokens and keeps the context focused.
- Install it from [rtk-ai/rtk](https://github.com/rtk-ai/rtk), then check it with `rtk --version` and `rtk gain`. If `rtk gain` fails, a different tool also named `rtk` is installed instead.
- If you use it, set it up once for your tool:
  - Codex: `rtk init -g --codex`. Codex has no rewrite hook, so prefix shell commands with `rtk` yourself (`rtk git status`, `rtk pytest -q`, `rtk npm run build`).
  - Claude Code: `rtk init -g`. A hook rewrites commands to `rtk <cmd>` automatically, so do not add the prefix by hand.
  - Other tools: `rtk init --help` lists the supported agents.
- RTK can hide output that is needed in full. When output is empty or cut short, run the command again as `rtk proxy <cmd>`. `gh issue view` has returned empty output through RTK before.
- `rtk gain` shows how much RTK saved.
- Implementer and reviewer runs started by `codex exec` do not need RTK.

## Agentic workflow

Use agentic coding. The main session coordinates and delegates; it does not do all the work itself. Delegated runs keep the main session's context small and give every change an independent review.

### Roles

- **Coordinator:** the interactive session you talk to. It reads the issue, plans, splits the work, writes briefs, checks what workers return, runs the final tests, and owns all Git and GitHub operations.
- **Implementer:** one delegated run that makes the change described in one brief, inside one worktree.
- **Reviewer:** one delegated, read-only run that reviews the change against the issue and this file, and reports findings without editing files.

### Models

| Role | Codex | Claude Code |
|---|---|---|
| Coordinator and complex planning | Interactive session on `gpt-6-sol`, reasoning effort `xhigh` | Main session on Opus 5.5 |
| Implementer | `gpt-6-luna`, reasoning effort `xhigh` only | Subagent on Sonnet 5.5, or the Codex implementer command below |
| Reviewer | `gpt-6-sol`, reasoning effort `high` (or `medium` for small changes) | Subagent on Opus 5.5, or the Codex reviewer command below |

```bash
# New worktree and branch per task, from the latest main
git fetch origin && git worktree add -b feat/<topic> ../wt-<topic> origin/main

# Implementer run (stdin must be closed)
codex exec -m gpt-6-luna -c model_reasoning_effort="xhigh" -s workspace-write -C <worktree> "<brief>" < /dev/null

# Reviewer run (read-only)
codex exec -m gpt-6-sol -c model_reasoning_effort="high" -s read-only -C <worktree> "<brief>" < /dev/null
```

### Rules for the coordinator

- Delegate implementation and review for any change bigger than a small edit. Do docs fixes, one-line fixes, and issue or label work directly.
- Run independent tasks in parallel, each in its own worktree and branch.
- Every brief states: the issue number and acceptance criteria, the worktree path, the files and areas in scope, the rules from this file that matter, the test commands, and what the report must contain.
- Forbid `ps`, `pgrep`, `pkill`, `kill`, and `top` in every brief, because a worker can match and kill its own process.
- Pass the model and the reasoning effort on every run. The local default may be a different model or a lower effort. Never run `gpt-6-luna` below `xhigh`.
- Close standard input (`< /dev/null`) on every `codex exec` run, or it waits forever.
- Give the implementer `-s workspace-write`. Add `-c sandbox_workspace_write.network_access=true` only when it must install dependencies or run Docker. Give the reviewer `-s read-only`.
- Never start a worker with `danger-full-access` or `--dangerously-bypass-approvals-and-sandbox`.
- Check every result yourself (read the diff, run the tests) before committing. Never commit work you have not checked.
- Decide whether another implement or review round is needed, and start it yourself.
- Name the model that actually ran each role in the completion report. Do not record an intended model as if it had been used.

### Rules for workers

- If you were started by `codex exec` or as a subagent, you are a worker, not the coordinator. The coordinator rules above do not apply to you.
- Implementer: do the work yourself in this run. Reviewer: review only and do not edit files.
- Do not start `codex exec`, another session, or any subagent, and do not hand the task to another model.
- One run is one round. Finish with a report and stop.
- Do not commit, push, or touch GitHub issues or pull requests. Put suggested issues in your report.

## GitHub issues

- Search existing issues (open and closed) before opening one. Comment on a matching issue instead of opening a duplicate.
- Give each issue one type label (`bug`, `enhancement`, `refactor`, `docs`, or `security`), one priority label (`priority: critical`, `priority: high`, `priority: medium`, or `priority: low`), and one or more `area:` labels. Create a new area label only when a new area of work starts.
- Use `blocked` (waiting on another issue), `needs decision` (waiting on a product decision), or `waiting on external` (waiting on a third party) when work cannot move. Write `Depends on #<number>` in the body.
- Label colors follow the group: type labels are bold distinct colors, priority goes from dark red (critical) to pale yellow (low), area labels are light pastels, and status labels are grays.
- Write the body in plain words: what happens now, what should change, and acceptance criteria as a checklist. For bugs, add how it was found or reproduced, with dates.
- Before starting an issue, read its comments to check nobody else is on it, then comment that it is being implemented, with the date and the branch name.
- When work finds a problem outside the current change, open an issue for it and mention the number in your report instead of fixing it on the side.
- Link every pull request to its issue with `Closes #<number>`. Use `Refs #<number>` when the pull request covers only part of the issue.
- Do not close an issue by hand unless the project owner asks, or the work is proven done and no pull request carries it. Say why in a closing comment.
- Opening and commenting on issues does not need approval. Closing, relabeling another person's issue, or deleting anything does.

## Implementation principles

- Read the existing code and behavior before changing anything.
- Prefer small extensions over rewrites.
- Deliver the simplest implementation that satisfies the issue and its acceptance criteria.
- Do not add frameworks, queues, services, or infrastructure without a current requirement. Do not optimize for hypothetical scale.
- Preserve existing orders, stock movements, and import history. Never write code that deletes or rewrites historical records.

## Python style

- Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) for new and changed code.
- Exception: do not start new function or method names with `_`. Use clear public names instead.
- Keep lines at 100 characters or fewer. Do not pack several statements onto one line, and do not assign lambdas to names; write a small function.
- Add type hints to every function signature.
- Give every public module, class, and function a Google-style docstring (`Args:`, `Returns:`, `Raises:` when useful). Keep it in sync with the behavior.
- Return Pydantic schemas or small dataclasses from services, not loose `dict` objects with many keys.
- Do not reformat untouched code in a feature change. Clean up a file when you are already changing it, or in a separate refactor change.

## TypeScript and React style

- Use strict TypeScript. Do not use `any`; define a type instead.
- One component per file, named after the component. Keep page components thin and move reusable parts into shared components.
- Keep all API calls in the API layer (`api.ts` or a module under it), not inside components.
- Keep styles close to the feature they belong to instead of growing one global stylesheet.

## Design principles

Keep them practical. Choose the simplest design that keeps the code easy to change.

- **Modular code.** Group code by feature (orders, inventory, customers, reporting, messaging). Each backend feature gets its own FastAPI router, service module, and schemas. Aim for files under about 400 lines; split a file when it grows past that or mixes unrelated concerns.
- **Layers.** Routers handle HTTP only (parse input, check permissions, call a service, return a response). Services hold business rules. Models describe the database. Do not put business rules in routers or React components.
- **OOP when it makes sense.** Use a class when there is state plus behavior that belong together, or several interchangeable implementations. Use plain functions for simple, stateless steps. Do not create a class just to hold one function.
- **SOLID, in plain terms:**
  - Single responsibility: each module, class, or function has one reason to change.
  - Open/closed: add new behavior (a new channel, a new export format) by adding a new class or module, not by growing `if/elif` chains.
  - Liskov substitution: any implementation of an interface must work wherever the interface is expected, with no special cases.
  - Interface segregation: keep interfaces small. Callers should not depend on methods they do not use.
  - Dependency inversion: business code depends on interfaces (for example `typing.Protocol`), and concrete providers are passed in. This keeps the code testable without real network calls.
- **Design patterns that fit this project.** Use them when they remove real complexity, not for their own sake:
  - Strategy or Adapter for interchangeable integrations: AI intake providers, message channels (WhatsApp, Facebook, Instagram), and report exporters (CSV, PDF).
  - Factory to choose the right implementation from configuration.
  - Service layer for business workflows such as order approval, dispatch, and stock receiving.
  - State-transition table for order and purchase-order status rules, instead of scattered status checks.
- **No duplication.** Before writing new code, search for existing helpers. When the same logic appears a second time, extract it into a shared function. Never copy code to make a variant; extract the shared part instead. Typical candidates: cents formatting, permission checks, stock movement creation, CSV parsing.
- **No speculative code.** Do not add layers, settings, or abstractions that no current issue needs.

## Scope boundaries

Included:

- Customer message intake and AI product matching with staff review.
- Orders from draft to approval, dispatch, or cancellation.
- Catalog, stock, per-unit IMEI tracking, and CSV catalog import.
- Suppliers, restock suggestions, and supplier purchase orders.
- Customer history, operations reports, alerts, and exports.
- Meta WhatsApp, Facebook, and Instagram message channels.
- A hosted demo with fictional data.

Not included unless an issue explicitly asks for it:

- Online payments or card processing.
- A customer-facing portal or customer accounts.
- Automatic ordering from suppliers or automatic order approval.
- Multi-branch or multi-tenant support.
- Microservices or mobile apps.
- Large UI redesigns unrelated to an issue.

## User approval gates

Stop and ask the project owner before:

- Changing how totals, prices, stock, or order status rules work.
- Adding any action that reaches a customer or supplier without a staff click.
- Destructive database operations, or a migration that drops or rewrites data.
- Removing existing functionality.
- Adding a new runtime dependency or external service.
- Pushing, merging, or opening pull requests, unless you were asked to.

For ordinary implementation details inside an agreed issue, proceed without asking.

## Database

- Every schema change needs a migration once migrations are set up. Never edit a deployed database by hand.
- Keep queries inside services. Avoid N+1 queries (one query per row in a loop) in lists and reports.

## Tests

The quality target is reliable business rules, not maximum coverage.

- Add or update pytest tests for every backend behavior change.
- Always cover the critical paths a change touches: login and role permissions, order draft to approval to dispatch or cancellation, stock reservation and deduction, totals in cents, CSV import preview and confirmation, IMEI unit tracking, and message analysis.
- Mock external services (OpenAI, Meta). Tests must never call the network.
- Add a Playwright test when a change alters a main user flow.
- Do not spend time raising coverage of unrelated code.

## Docker

- Use Docker locally only to build, run, and test the app.
- `docker compose down -v` deletes the database volume. Never run it on a stack you did not create for the current task.
- For throwaway test stacks, use a separate Compose project name (`docker compose -p <name>`) so the main development stack is not touched, and remove it with its volumes when done.
- Never run `docker system prune` or push images from a developer machine.
- Workers that start containers bind host ports to `127.0.0.1`, mount only their own worktree read-write, and never mount `/`, the home folder, or `/var/run/docker.sock`. No privileged containers and no host networking.

## Dependencies

- Reuse existing dependencies whenever practical. Do not add a dependency for something the current stack does simply.
- Pin dependencies the way the project already does (`requirements.txt` ranges plus `requirements-lock.txt`, and `package-lock.json`).
- Document any new runtime or system dependency in the README.
- Do not upgrade unrelated dependencies during feature work.

## Documentation

- Update the README when setup, usage, behavior, or architecture changes, including the Mermaid diagram.
- Update this file when a team rule or workflow changes.
- Do not create speculative or duplicate documentation.
- Do not soft-wrap lines in Markdown files. Keep each sentence or bullet on one line.

## Git

- Trunk-based development: `main` is the only long-lived branch and must always be deployable.
- Create a short-lived branch from `main` for each issue and merge it within a few days. Keep pull requests small.
- Never push directly to `main`. Every change goes through a pull request that passes CI and is squash-merged. Leave review and merging to the project owner.
- A pull request that conflicts with `main` gets no CI checks, because GitHub cannot build the trial merge. Update the branch from `main` before opening the pull request.
- Hide unfinished features behind a setting or flag instead of keeping a long-running branch.
- Check the working tree before editing, and preserve other people's uncommitted changes.
- Use small, focused commits. Commit messages use `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`, `test: ...`, or `chore: ...`.
- Branch prefixes: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`.
- Never commit secrets, databases, customer data, generated dependencies, or local credentials.
- Never add AI attribution or `Co-Authored-By` trailers.
- Do not push unless asked.

## Completion report

When a task is done, report briefly:

1. What changed.
2. Tests run and their results.
3. Migrations added and how to roll them back, if any.
4. Known limitations, and issues opened for problems found along the way.
5. The models that actually ran the implementer and reviewer roles.
6. The pull request's full URL, when one was opened.
