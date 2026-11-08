import sqlite3

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.db import connect_database, get_db, transaction
from app.main import APP_DIR, create_app


def test_database_transactions_and_foreign_keys(tmp_path):
    connection = connect_database(tmp_path / "nested" / "test.sqlite3")
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE child (parent_id INTEGER REFERENCES parent(id))")
        with transaction(connection):
            connection.execute("INSERT INTO parent VALUES (?)", (1,))
        with pytest.raises(sqlite3.IntegrityError), transaction(connection):
            connection.execute("INSERT INTO parent VALUES (?)", (2,))
            connection.execute("INSERT INTO child VALUES (?)", (999,))
        assert [row["id"] for row in connection.execute("SELECT id FROM parent")] == [1]
        assert not connection.in_transaction
    finally:
        connection.close()


def test_app_startup_and_request_connection_cleanup(monkeypatch, tmp_path):
    monkeypatch.setenv("SESSION_SECRET", "test-only-secret")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    application = create_app()
    connections = []

    @application.get("/_test/database")
    def probe(connection: sqlite3.Connection = Depends(get_db)):
        connections.append(connection)
        return {"foreign_keys": connection.execute("PRAGMA foreign_keys").fetchone()[0]}

    with TestClient(application) as client:
        for _ in range(2):
            assert client.get("/_test/database").json() == {"foreign_keys": 1}
        assert client.get("/docs").status_code == 200
    assert connections[0] is not connections[1]
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")
    assert application.state.templates.env.loader.searchpath == [str(APP_DIR / "templates")]


def test_missing_secret_fails_startup(monkeypatch):
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="SESSION_SECRET"), TestClient(create_app()):
        pass
