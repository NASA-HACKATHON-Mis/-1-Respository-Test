"""Request-scoped SQLite connections with explicit transaction ownership."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi import Request

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "var" / "bookstore.sqlite3"


def connect_database(path: str | Path = DEFAULT_DATABASE_PATH) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # FastAPI's synchronous dependencies/routes can run on different worker threads.
    connection = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    connection = connect_database(request.app.state.database_path)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Reserve the write lock before reading stock; commit or roll back as a unit."""
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
