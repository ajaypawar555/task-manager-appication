# Task Manager API

A small REST API built with Python 3.11+, FastAPI, Pydantic, and Supabase PostgreSQL. It supports task creation, listing, lookup, partial updates, deletion, status and priority filters, title search, pagination, and due dates.

See [API.md](API.md) for the endpoint reference, request examples, Postman steps, and status codes.

## Architecture

- `app/api/routes`: HTTP endpoints, input/query validation, optional authentication, and safe database error responses.
- `app/services`: application use cases and not-found behavior.
- `app/repositories`: Supabase/PostgREST queries, including filters and pagination.
- `app/schemas`: Pydantic request and response validation.
- `app/models`: allowed status and priority values.
- `app/core` and `app/db`: settings and lazy Supabase client setup.
- `migrations`: SQL schema and indexes to run in Supabase.
- `tests`: mocked HTTP-level tests; they do not connect to Supabase.

This first version is a **public, single shared task space** with authentication disabled by default. Anyone with the app URL can view, create, update, and delete tasks. The Supabase key stays on the server. To enable the optional shared bearer token, set `API_AUTH_ENABLED=true` and configure `API_ACCESS_TOKEN`. A shared token is not per-user identity or authorization; add Supabase Auth, owner IDs, owner-scoped queries, and RLS policies before using this as a multi-user service.

## Prerequisites

- Python 3.11 or newer.
- A Supabase project.
- PowerShell on Windows, or a POSIX shell on macOS/Linux.

## Create the Supabase database

1. Create a Supabase project and open its **SQL Editor**.
2. Paste and run [`migrations/001_create_tasks.sql`](migrations/001_create_tasks.sql).
3. In the project API settings, copy the project URL and a server-side Supabase secret key (not the publishable key). Do not put this key in frontend code, screenshots, source control, or this chat. Older projects may call the equivalent key `service_role`; treat it as an elevated secret and rotate it if it leaks.

The migration creates the `tasks` table, enum-like check constraints, timestamp trigger, and indexes. It enables RLS and revokes table access from `anon` and `authenticated`; only the backend's `service_role` database role is granted access. Supabase server secret keys bypass RLS, so this public API can read and modify every task in the shared table. Never expose the Supabase key. The later multi-user phase should use user identity and ownership policies rather than a shared global token.

## Set up locally

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again.

### macOS/Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` locally:

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-server-side-secret-key
API_AUTH_ENABLED=false
```

The API is public with this setting. To enable optional bearer-token protection, set `API_AUTH_ENABLED=true` and add `API_ACCESS_TOKEN` to `.env`.

If you enable optional bearer-token protection, generate a random token locally, for example:

```powershell
# PowerShell
[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

```bash
# macOS/Linux
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Never commit `.env`. The application does not need Supabase credentials for `/health` or the mocked tests; task operations do.

## Run the API

With the virtual environment active:

```powershell
# Windows PowerShell, macOS, or Linux
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/docs> for Swagger UI. The health endpoint is available at <http://127.0.0.1:8000/health>.

## Run the desktop UI

The project includes a simple Tkinter desktop client. It uses Python's standard library and calls the REST API; it does not connect to Supabase directly. Start the API in one terminal, then open a second PowerShell terminal in the project folder and run:

```powershell
.\.venv\Scripts\python.exe ui.py
```

Keep the API base URL as `http://127.0.0.1:8000`. The UI lets you list, filter, search, create, select, update, and delete tasks without a token when authentication is disabled.

See [API.md](API.md) for the HTTP endpoint reference and Postman instructions.

## Deploy the browser UI to Vercel

The Tkinter desktop window (`ui.py`) cannot run in a browser. The browser interface is `public/index.html`; FastAPI serves it at `/` and serves the task API from the same origin. Vercel's Python runtime supports FastAPI apps and its FastAPI integration can serve static frontend files. See the [Vercel FastAPI guide](https://vercel.com/docs/frameworks/backend/fastapi).

Push this project to a Git provider supported by Vercel, then import the repository as a new Vercel project. Add these environment variables in the Vercel project settings for each deployment environment:

| Variable | Value |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL. |
| `SUPABASE_KEY` | A server-side Supabase secret key, never a publishable key. |
| `API_AUTH_ENABLED` | `false` for a public demo. Set `true` only when you also configure a token. |
| `API_ACCESS_TOKEN` | Optional; only required when `API_AUTH_ENABLED=true`. |

Keep the Supabase secret in Vercel's server-side environment settings. Do not put it in `public/index.html`, browser JavaScript, or a `NEXT_PUBLIC_` variable. For this public demo, set `API_AUTH_ENABLED=false` in Vercel. Anyone who finds the deployed URL can change or delete every task in the shared table.

After setting the variables, deploy the Vercel project. Open the deployment root URL to use the browser UI. The API is also available at `/api/v1/tasks`, and Swagger UI at `/docs`. The Vercel entrypoint is configured in `pyproject.toml`; no separate UI build step is needed.

In Swagger UI, task endpoints work without an authorization header when `API_AUTH_ENABLED=false`. If you enable authentication, fill its `authorization` header parameter with `Bearer <your API_ACCESS_TOKEN>`. For example:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/tasks `
  -Headers @{ Authorization = "Bearer your-local-token" } `
  -ContentType "application/json" `
  -Body '{"title":"Prepare demo","priority":"high"}'
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks \
  -H 'Authorization: Bearer your-local-token' \
  -H 'Content-Type: application/json' \
  -d '{"title":"Prepare demo","priority":"high"}'
```

List tasks with filters such as `GET /api/v1/tasks?status=pending&priority=high&search=demo&limit=20&offset=0`. Allowed statuses are `pending`, `in_progress`, `completed`; priorities are `low`, `medium`, `high`. `limit` is 1–100 and defaults to 20.

## Tests and lint

The HTTP tests use a fake service and override FastAPI dependencies; they need no Supabase project or credentials. There are currently no live integration tests. To run the unit tests and style checks:

```powershell
python -m pytest
ruff check .
ruff format --check .
```

```bash
python -m pytest
ruff check .
ruff format --check .
```

## HTTP behavior

- `POST /api/v1/tasks`: `201 Created`.
- `GET /api/v1/tasks` and `GET /api/v1/tasks/{task_id}`: `200 OK`.
- `PATCH /api/v1/tasks/{task_id}`: `200 OK`; at least one field is required.
- `DELETE /api/v1/tasks/{task_id}`: `204 No Content`.
- Invalid data: FastAPI/Pydantic `422`; missing task: `404`; absent/invalid bearer token: `401` when optional authentication is enabled.
- Supabase failures: generic `503` response; exception details are logged server-side, not returned.

## Troubleshooting

- **`503 Task storage is temporarily unavailable`**: confirm the migration ran, `SUPABASE_URL` and `SUPABASE_KEY` are correct, and the key is the server-side secret. Restart Uvicorn after editing `.env`.
- **`401 Invalid or missing API token`**: this only applies when `API_AUTH_ENABLED=true`; set it to `false` for the public demo, or include the configured bearer token.
- **Relation/table not found**: run the migration in the intended Supabase project's SQL Editor.
- **Permission denied**: confirm the server key maps to the granted `service_role`; do not grant the `anon` role open table access as a shortcut.
- **Import errors**: activate the virtual environment and run `pip install -r requirements.txt`.
- **RLS blocks access**: this initial backend uses a server-only elevated key. Do not disable RLS. For a future user-authenticated implementation, pass the user's access token and create owner-scoped policies.

## Security and next phase

Keep `.env` and the Supabase secret key private, use HTTPS outside local development, store deployment secrets in a secret manager, and rotate credentials if exposed. This public demo allows anyone with its URL to read and change all tasks. Before using it with private or multi-user data, integrate Supabase Auth, add a `user_id` foreign key, scope every repository query by authenticated user, and write/test RLS policies that prevent cross-user reads and writes. Task IDs by themselves are never authorization.
