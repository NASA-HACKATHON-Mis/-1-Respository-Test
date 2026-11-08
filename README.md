# Bookstore MVP

Python 3.12+ / FastAPI / sqlite3 / Jinja2. Specifications: [dev_docs.md](dev_docs.md).

## Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.seed
$env:SESSION_SECRET = 'local-development-secret-change-before-sharing'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Use `py` instead of `python` if your Python launcher is configured. Open
http://127.0.0.1:8000/docs to verify startup. SESSION_SECRET must be set before
starting the server; do not commit shared secrets. Cookies use local HTTP defaults.

A0 provides app/session setup, template/static path registration, and SQLite
connection/transaction helpers. A1 adds the books/orders/order_items schema,
20 fictional books, and GET `/`, `/books`, `/search`, `/books/{book_id}` routes.
Frontend templates/assets are owned by B and are not supplied here: rendered
storefront pages require those templates. Backend HTTP tests use a test-only
in-memory template loader to verify the route context contract independently.
Cart and order processing arrive in A2.

`python -m app.seed` validates the complete input before opening the destination,
then creates tables and inserts books in one transaction. Existing IDs are skipped
without changing inventory or orders. It honors `DATABASE_PATH`, as does the app;
set this variable before both commands when using a custom database. Seed does not
require SESSION_SECRET. Shared seed fields and cover paths are in `data/books.json`.
Recommended books are ordered by ID. Search matches literal substrings, including
percent and underscore characters; sort ties use ID ascending.

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

A1 verification on Python 3.13.5: 47 backend tests passed with
`python -m pytest tests/backend -q -p no:cacheprovider`; `pip check` passed.
Seed CLI verification against a disposable DB inserted 20 books on its first run
and 0 on its second. Tests cover schema constraints, seed rollback/preservation,
exact documented book content, catalog queries, pagination, HTTP statuses, and
template context keys. The existing Starlette TestClient deprecation warning remains.
