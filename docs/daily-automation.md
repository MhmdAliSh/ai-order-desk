# Daily operations automation

The report runner saves one daily snapshot of sales, restock suggestions, and the deterministic owner report. It does not change stock, approve orders, or contact suppliers.

Run it once manually from Git Bash:

```bash
cd /c/Users/PC/Documents/ai-order-desk/backend
./.venv/Scripts/python.exe -m app.daily_job
```

For a real deployment, schedule this command once a day in the hosting platform's scheduler. For a local Windows demonstration, create a Task Scheduler task that runs the same command daily after the project has been deployed or the computer is expected to be on.

The saved reports are visible on the Operations page. The next enhancement will optionally use AI to explain these already-calculated facts in more natural language.
