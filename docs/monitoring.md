# Monitoring (Week 12)

Three views of the live API, all in Azure Monitor, all ₹0:

```text
                      ┌───────────── Application Insights (appi-ecom-mini) ─────────────┐
FastAPI app ──OTel──► │ requests, durations, status codes, exceptions + stack traces,    │
 (managed identity)   │ app logs (e.g. "Order 12 placed"), Live Metrics                  │
                      └──────────────────────────────┬───────────────────────────────────┘
                                                     │ stored in
App Service ──diagnostic setting──► Log Analytics workspace (log-ecom-mini, 0.1 GB/day cap)
 (platform)   HTTP logs, console logs (stdout/stderr), platform logs (container start/stop)

App Service metrics (built in) ──► metric alert "Http5xx > 0 in 5 min" ──► email to the owner
```

| View | Answers | Where |
| --- | --- | --- |
| **Application Insights** | Which requests are slow or failing, and why (stack trace)? What is happening right now? | Portal → `appi-ecom-mini` → Failures, Performance, Transaction search, Live Metrics |
| **App Service logs in Log Analytics** | What did the platform see, even when the app itself could not report anything (e.g. a container that never started)? | Portal → `log-ecom-mini` → Logs (KQL) |
| **Metrics + alert** | Is anything returning server errors right now? Tell me by email. | Portal → web app → Metrics; Monitor → Alerts |

## How it is wired

- **Infrastructure (Terraform):**
  - Foundation layer, `monitoring.tf`: the Log Analytics workspace, Application Insights (workspace-based), and the email action group. They live in the foundation so the history survives an app-layer rebuild.
  - App layer, `monitoring.tf`: the diagnostic setting, the 5xx alert, and the web app's **Monitoring Metrics Publisher** role.
- **App code:** [`app/core/telemetry.py`](../app/core/telemetry.py). When `APPLICATIONINSIGHTS_CONNECTION_STRING` is set, it calls `configure_azure_monitor(...)` from Microsoft's OpenTelemetry distro, then `FastAPIInstrumentor.instrument_app(app)`. Tests, CI and local runs leave the setting empty and send nothing.
- **No keys:** Application Insights has *local authentication disabled*, so the instrumentation key in the connection string cannot be used to send data. The app authenticates with its **managed identity** (`DefaultAzureCredential`), like it does for Blob Storage and the registry.
- **Less noise:** `OTEL_PYTHON_FASTAPI_EXCLUDED_URLS=/health$` leaves out App Service's health probe, which runs once a minute.
- **Logs without personal data:** checkout logs `Order <id> placed by user <user id>, total <amount>`. It records a user ID, never an email.
- **Cost guard:** the workspace's daily cap is 0.1 GB. That allows at most about 3 GB a month, below the free 5 GB, so ingestion is ₹0 by construction. Collection pauses for the rest of the day if the cap is reached. Email notifications are free. The single metric alert is priced ₹0 (at most about ₹10 a month).

## The sample error

`POST /diagnostics/error` is **admin-only** and raises an unhandled `SampleError`, exactly like a real bug.

**Response to the caller:** HTTP 500 with the body `Internal Server Error`. No stack trace leaks to the caller.

**Where it shows up:**

| Where | What you see | Delay |
| --- | --- | --- |
| Application Insights → **Failures** | `POST /diagnostics/error` with a 500, and the exception `SampleError` with its full stack trace | 1–3 min |
| Log Analytics → `AppServiceHTTPLogs` | the request, with status 500 | 2–5 min |
| Log Analytics → `AppServiceConsoleLogs` | uvicorn's `Exception in ASGI application` and the traceback | 2–5 min |
| Email | "Fired: alert-ecom-mini-http-5xx", and later "Resolved" once 5 minutes pass without errors | 5–10 min |

## Useful KQL queries

Run these in Portal → `log-ecom-mini` → **Logs**, or in Application Insights → **Logs**. There, the tables are named `requests`, `exceptions` and `traces`.

All of these were run against the live workspace on 2026-10-21.

| Question | Query |
| --- | --- |
| Which requests failed today? | `AppRequests \| where TimeGenerated > ago(1d) and Success == false \| summarize failures = count() by Name, ResultCode \| order by failures desc` |
| Which errors happened, and when? | `AppExceptions \| where TimeGenerated > ago(1d) \| project TimeGenerated, ExceptionType, OuterMessage \| order by TimeGenerated desc` |
| Which endpoints are slowest? | `AppRequests \| where TimeGenerated > ago(1d) \| summarize requests = count(), avg_ms = round(avg(DurationMs), 1), p95_ms = round(percentile(DurationMs, 95), 1) by Name \| order by p95_ms desc` |
| Which orders were placed? (app log) | `AppTraces \| where TimeGenerated > ago(7d) \| where Message startswith 'Order ' \| project TimeGenerated, Message \| order by TimeGenerated desc` |
| Which server errors did the platform see? | `AppServiceHTTPLogs \| where TimeGenerated > ago(1d) and ScStatus >= 500 \| project TimeGenerated, CsMethod, CsUriStem, ScStatus, TimeTaken \| order by TimeGenerated desc` |
| Show me the tracebacks | `AppServiceConsoleLogs \| where TimeGenerated > ago(1d) \| where ResultDescription has_any ('Traceback', 'ERROR') \| project TimeGenerated, ResultDescription \| order by TimeGenerated desc` |
| Did the container start, stop or fail? | `AppServicePlatformLogs \| where TimeGenerated > ago(1d) \| project TimeGenerated, Level, Message \| order by TimeGenerated desc \| take 20` |

`p95` is the 95th percentile: 95% of requests were faster than this. On F1, expect `AppServicePlatformLogs` to show the site being stopped after about 20 idle minutes and started again on the next request. That's the cold start, not a failure.

## Problems met and fixed

| Problem | Cause | Fix |
| --- | --- | --- |
| First deploy: the sample error reached the console logs, but **nothing** reached Application Insights | The distro's automatic FastAPI instrumentation swaps the `fastapi.FastAPI` class, so it only affects apps created **after** `configure_azure_monitor()`. `app/main.py` had already imported the class. The unit test had mocked everything, so it couldn't notice. | Instrument our existing app explicitly with `FastAPIInstrumentor.instrument_app(app)`, and turn the automatic one off. A regression test checks the instrumentation is attached, and fails without the fix (mutation-checked). |
| The checkout log line never appeared in tests | Alembic's `env.py` called `logging.config.fileConfig()`, which by default **disables every logger that already exists**. The tests run migrations after importing the app. | `fileConfig(..., disable_existing_loggers=False)` |
| A Terraform plan printed the Application Insights connection string | Values read from another layer's state (`terraform_remote_state`) lose their `sensitive` mark | `sensitive(...)` around the remote-state values in `app_settings`, including `DATABASE_URL` |
| Two merges into `main` (PRs #4 and #5) started no pipeline run | A GitHub incident, "Delays for Pull Requests and Webhook deliveries". For PR #4, GitHub's API even answered 422 for the merge commit. Our workflow was unchanged and active. | A manual **Run workflow** button (`workflow_dispatch`) on CI/CD. It deploys only on `main`. The fix was deployed with it. See [cicd.md](cicd.md). |

## Not done, by choice

- **Availability (ping) tests:** about ₹0.06 per run, or ₹170–520 a month. App Service's health check and the 5xx alert cover the demo.
- **Dashboards and workbooks:** the built-in Application Insights pages are enough.
- **Database query telemetry:** the distro instruments `psycopg2`, but this app uses psycopg 3.
- **Alerts on latency or CPU:** one meaningful alert is better than several noisy ones.
