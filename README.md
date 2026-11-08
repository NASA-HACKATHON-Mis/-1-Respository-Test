# Bookstore MVP

Python 3.12+ / FastAPI / sqlite3 / Jinja2. Specifications: [dev_docs.md](dev_docs.md).

## Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SESSION_SECRET = 'local-development-secret-change-before-sharing'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Use `py` instead of `python` if your Python launcher is configured. Open
http://127.0.0.1:8000/docs to verify startup. SESSION_SECRET must be set before
starting the server; do not commit shared secrets. Cookies use local HTTP defaults.

A0 provides app/session setup, template/static path registration, and SQLite
connection/transaction helpers. Storefront routes, schema, and `python -m app.seed`
arrive in A1/A2. Frontend templates/assets are owned by B and are not supplied here.

SQLite defaults to `var/bookstore.sqlite3`; optionally set `DATABASE_PATH` before
startup. The parent directory is created on the first connection. Connections use
foreign keys and named rows, are closed after each request, and do not implicitly
commit grouped writes. Services must use `app.db.transaction` for atomic writes;
it begins with `BEGIN IMMEDIATE` and rolls back failures. Use synchronous routes
for SQLite work. Runtime databases and virtual environments are ignored by Git.

## Backend verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend -q
.\.venv\Scripts\python.exe -m pip check
```

A0 verified on Python 3.13.5: 3 tests passed, dependency check passed, and a real
Uvicorn server returned HTTP 200 for `/docs`. Tests use temporary databases.
The installed Starlette emits an httpx TestClient deprecation warning; tests pass.
The Windows environment also reported a non-failing pytest cache permission warning.
