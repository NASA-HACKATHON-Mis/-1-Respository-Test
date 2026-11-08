"""Run with python -m app.seed; existing IDs and inventory are preserved."""
import json
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from app.db import DEFAULT_DATABASE_PATH, connect_database, transaction

SCHEMA = Path(__file__).with_name('schema.sql')
SOURCE = Path(__file__).resolve().parent.parent / 'data' / 'books.json'


def load_books(source=SOURCE):
    books = json.loads(Path(source).read_text(encoding='utf-8'))
    if not isinstance(books, list) or len(books) != 20:
        raise ValueError('Seed must contain exactly 20 books')
    # Validate the complete input before touching the destination database.
    with sqlite3.connect(':memory:') as validation:
        validation.executescript(SCHEMA.read_text(encoding='utf-8'))
        fields = {row[1]: row[2] for row in validation.execute('PRAGMA table_info(books)')}
        for book in books:
            if not isinstance(book, dict) or set(book) != set(fields):
                raise ValueError('Book fields do not match the schema')
            for key, kind in fields.items():
                value = book[key]
                if value is None and key in ('subtitle', 'isbn13'):
                    continue
                valid = (type(value) is bool if key == 'is_recommended' else
                         type(value) is int if kind == 'INTEGER' else
                         type(value) in (int, float) if kind == 'REAL' else
                         isinstance(value, str))
                if not valid:
                    raise ValueError(f'Invalid type for {key}')
            published = date.fromisoformat(book['published_at'])
            created = datetime.fromisoformat(book['created_at'])
            if published.isoformat() != book['published_at'] or created.utcoffset() != timedelta(0):
                raise ValueError('Dates must use ISO format and created_at must be UTC')
            if book['isbn13'] is not None or book['cover_image'] != f"/static/covers/{book['id']:02d}.svg":
                raise ValueError('Invalid fictional ISBN or cover path')
            insert_book(validation, book)
    if {book['id'] for book in books} != set(range(1, 21)):
        raise ValueError('Seed IDs must be 1 through 20')
    return books


def insert_book(db, book, *, skip_existing=False):
    columns = ', '.join(book)
    placeholders = ', '.join('?' for _ in book)
    suffix = ' ON CONFLICT(id) DO NOTHING' if skip_existing else ''
    db.execute(f'INSERT INTO books ({columns}) VALUES ({placeholders}){suffix}', list(book.values()))


def seed_database(path=DEFAULT_DATABASE_PATH, source=SOURCE):
    books = load_books(source)
    db = connect_database(path)
    try:
        with transaction(db):
            # executescript would implicitly commit the active transaction.
            for statement in SCHEMA.read_text(encoding='utf-8').split(';'):
                if statement.strip():
                    db.execute(statement)
            before = db.total_changes
            for book in books:
                insert_book(db, book, skip_existing=True)
            inserted = db.total_changes - before
        return inserted
    finally:
        db.close()


if __name__ == '__main__':
    count = seed_database(os.environ.get('DATABASE_PATH', DEFAULT_DATABASE_PATH))
    print(f'Seed complete: {count} books inserted; existing books preserved.')
