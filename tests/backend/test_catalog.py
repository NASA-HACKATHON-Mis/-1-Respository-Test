import json
import sqlite3
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fastapi.templating import Jinja2Templates
from jinja2 import DictLoader, Environment

from app.db import connect_database
from app.main import create_app
from app.seed import SOURCE, load_books, seed_database
from app.services.catalog import CATEGORIES, get_book, home_books, list_books


@pytest.fixture
def database(tmp_path):
    path = tmp_path / 'catalog.sqlite3'
    assert seed_database(path) == 20
    return path


@pytest.fixture
def db(database):
    connection = connect_database(database)
    yield connection
    connection.close()


@pytest.fixture
def client(database, monkeypatch):
    monkeypatch.setenv('SESSION_SECRET', 'catalog-test-secret')
    monkeypatch.setenv('DATABASE_PATH', str(database))
    app = create_app()
    # Test-only renderer checks the real router context without authoring B's templates.
    names = ['home', 'books', 'search', 'book_detail', 'error']
    app.state.templates = Jinja2Templates(env=Environment(
        loader=DictLoader({name + '.html': '{{ csrf_token }}' for name in names}), autoescape=True))
    with TestClient(app) as test_client:
        yield test_client


def test_seed_preserves_inventory_and_orders(database, db):
    db.execute('UPDATE books SET stock=2 WHERE id=1')
    db.execute("INSERT INTO orders VALUES (1, 'Test', 'Test address', 16200, 'test_completed', '2026-11-08T00:00:00Z')")
    db.execute("INSERT INTO order_items VALUES (1, 1, 1, 'Snapshot', 16200, 1)")
    assert seed_database(database) == 0
    assert get_book(db, 1)['stock'] == 2
    assert db.execute('SELECT title FROM order_items').fetchone()[0] == 'Snapshot'
    assert db.execute('SELECT COUNT(*) FROM books').fetchone()[0] == 20


def test_invalid_seed_does_not_touch_destination(database, tmp_path, db):
    books = load_books()
    books[-1]['stock'] = -1
    source = tmp_path / 'bad.json'
    source.write_text(json.dumps(books), encoding='utf-8')
    with pytest.raises(sqlite3.IntegrityError):
        seed_database(database, source)
    assert db.execute('SELECT COUNT(*) FROM books').fetchone()[0] == 20
    fresh = tmp_path / 'not-created.sqlite3'
    with pytest.raises(sqlite3.IntegrityError):
        seed_database(fresh, source)
    assert not fresh.exists()


def test_seed_insert_failure_rolls_back(database, db):
    db.execute('DELETE FROM books WHERE id IN (19,20)')
    db.execute("CREATE TRIGGER fail_seed BEFORE INSERT ON books WHEN NEW.id=20 BEGIN SELECT RAISE(ABORT, 'test failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        seed_database(database)
    assert db.execute('SELECT COUNT(*) FROM books').fetchone()[0] == 18


@pytest.mark.parametrize('assignment', ['list_price=0', 'sale_price=-1', 'sale_price=999999',
    'stock=-1', 'stock=1.5', 'page_count=0', 'rating=6', 'is_recommended=2', 'title=NULL'])
def test_book_constraints(db, assignment):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute('UPDATE books SET ' + assignment + ' WHERE id=1')


def test_seed_content_and_home(db):
    books = load_books(SOURCE)
    assert len(books) == 20
    assert any(book['stock'] == 0 for book in books)
    assert sum(book['is_recommended'] for book in books) == 6
    home = home_books(db)
    assert [len(home[key]) for key in ['bestseller_books', 'new_books', 'recommended_books']] == [5, 5, 6]
    assert [b['id'] for b in home['bestseller_books']] == [20, 19, 18, 17, 16]
    expected = sorted(books, key=lambda b: b['published_at'], reverse=True)[:5]
    assert [b['id'] for b in home['new_books']] == [b['id'] for b in expected]
    book = get_book(db, 1)
    assert type(book['is_recommended']) is bool
    assert book['discount_percent'] == 10
    assert set(book) == set(books[0]) | {'discount_percent'}


@pytest.mark.parametrize('field', ['title', 'author', 'publisher'])
def test_substring_search(db, field):
    needle = get_book(db, 1)[field][1:3]
    result = list_books(db, q=needle)
    assert result['books']
    assert all(any(needle in book[k] for k in ['title', 'author', 'publisher']) for book in result['books'])


@pytest.mark.parametrize('category', CATEGORIES)
def test_categories_and_combined_search(db, category):
    result = list_books(db, category=category)
    assert result['pagination']['total_items'] == 4
    assert all(book['category'] == category for book in result['books'])
    assert list_books(db, q='서점', category=category)['pagination']['total_items'] == (1 if category == '소설' else 0)


@pytest.mark.parametrize('sort,field,reverse', [('popular','sales_count',True),
    ('newest','published_at',True), ('price_asc','sale_price',False), ('price_desc','sale_price',True)])
def test_sorting_and_ties(db, sort, field, reverse):
    books = list_books(db, sort=sort)['books']
    assert [b[field] for b in books] == sorted([b[field] for b in books], reverse=reverse)
    tie_value = 100 if field == 'sale_price' else books[0][field]
    db.execute(f'UPDATE books SET {field} = ?', (tie_value,))
    assert [b['id'] for b in list_books(db, sort=sort)['books']] == list(range(1,21))


def test_empty_and_literal_search_and_pagination(db):
    for query in ['%', '_', "' OR 1=1 --", '없는책']:
        result = list_books(db, q=query)
        assert result['books'] == []
        assert result['pagination']['total_pages'] == 1
    for page in [2, 10**30]:
        assert list_books(db, page=page)['books'] == []
    db.execute('INSERT INTO books SELECT 21, title, subtitle, author, publisher, published_at, isbn13, category, description, author_bio, table_of_contents, cover_image, list_price, sale_price, stock, page_count, rating, review_count, sales_count, is_recommended, created_at FROM books WHERE id=1')
    result = list_books(db, page=2)
    assert len(result['books']) == 1
    assert result['pagination']['total_pages'] == 2


@pytest.mark.parametrize('url,template,key', [('/', 'home.html', 'bestseller_books'),
    ('/books', 'books.html', 'books'), ('/search?q=서점', 'search.html', 'filters'),
    ('/books/1', 'book_detail.html', 'book')])
def test_http_context(client, url, template, key):
    response = client.get(url)
    assert response.status_code == 200
    assert response.template.name == template
    assert {'request','categories','cart_count','csrf_token','errors',key} <= response.context.keys()
    assert response.context['categories'] == CATEGORIES
    assert response.context['errors'] == []
    assert client.get('/').context['csrf_token'] == response.context['csrf_token']


@pytest.mark.parametrize('url,status', [('/books/999',404), ('/missing',404),
    ('/books?sort=invalid',422), ('/search?category=invalid',422),
    ('/books?page=0',422), ('/books?page=-1',422), ('/search?page=abc',422),
    ('/books?page=1.5',422)])
def test_http_errors(client, url, status):
    response = client.get(url)
    assert response.status_code == status
    assert response.template.name == 'error.html'
    assert response.context['status_code'] == status


def test_seed_matches_documented_books():
    specification = (Path(__file__).resolve().parents[2] / 'docs' / 'sample-data.md').read_text(encoding='utf-8')
    rows = re.findall(r'^\| (\d+) \| (.*?) \| (.*?) \| (.*?) \| ([\d,]+) \| ([\d,]+) \|$', specification, re.M)
    descriptions = dict(re.findall(r'^(\d+)\. \*\*.+?:\*\* (.+)$', specification, re.M))
    books = load_books()
    assert len(rows) == len(books) == 20
    for book, row in zip(books, rows):
        sid, title, author, category, regular, sale = row
        assert (book['id'], book['title'], book['author'], book['category']) == (int(sid), title, author, category)
        assert (book['list_price'], book['sale_price']) == (int(regular.replace(',', '')), int(sale.replace(',', '')))
        assert book['description'] == descriptions[sid]


@pytest.mark.parametrize('order_id,book_id,quantity,price', [(999,1,1,100), (1,999,1,100),
    (1,1,0,100), (1,1,100,100), (1,1,1,-1)])
def test_order_item_constraints(db, order_id, book_id, quantity, price):
    db.execute("INSERT INTO orders VALUES (1,'Test','Test',100,'test_completed','2026-11-08T00:00:00Z')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute('INSERT INTO order_items VALUES (1,?,?,?,?,?)', (order_id, book_id, 'Snapshot', price, quantity))
