"""Database-backed catalog queries. SQL ordering is chosen from a fixed allowlist."""

CATEGORIES = ['소설', '자기계발', '경제·경영', '인문·교양', '과학·IT']
SORTS = {
    'popular': 'sales_count DESC', 'newest': 'published_at DESC',
    'price_asc': 'sale_price ASC', 'price_desc': 'sale_price DESC',
}
PAGE_SIZE = 20


def book_context(row):
    book = dict(row)
    book['is_recommended'] = bool(book['is_recommended'])
    book['discount_percent'] = (book['list_price'] - book['sale_price']) * 100 // book['list_price']
    return book


def get_book(db, book_id):
    # Python integers are unbounded; SQLite INTEGER IDs are signed 64-bit values.
    if not -(2**63) <= book_id <= 2**63 - 1:
        return None
    row = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    return book_context(row) if row else None


def list_books(db, *, q='', category='', sort='popular', page=1):
    if sort not in SORTS or (category and category not in CATEGORIES) or page < 1:
        raise ValueError('Invalid catalog filters')
    clauses, values = [], []
    if q:
        # Treat percent and underscore literally, rather than as LIKE wildcards.
        pattern = '%' + q.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
        clauses.append("(title LIKE ? ESCAPE '!' OR author LIKE ? ESCAPE '!' OR publisher LIKE ? ESCAPE '!')")
        values.extend([pattern] * 3)
    if category:
        clauses.append('category = ?')
        values.append(category)
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    total = db.execute('SELECT COUNT(*) FROM books' + where, values).fetchone()[0]
    # Avoid overflowing SQLite's signed integer offset for very large query pages.
    rows = [] if (page - 1) * PAGE_SIZE >= total else db.execute(
        'SELECT * FROM books' + where + ' ORDER BY ' + SORTS[sort] + ', id ASC LIMIT ? OFFSET ?',
        [*values, PAGE_SIZE, (page - 1) * PAGE_SIZE],
    ).fetchall()
    return {
        'books': [book_context(row) for row in rows],
        'filters': {'q': q, 'category': category, 'sort': sort},
        'pagination': {'page': page, 'page_size': PAGE_SIZE, 'total_items': total,
                       'total_pages': max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)},
    }


def home_books(db):
    return {
        'bestseller_books': list_books(db)['books'][:5],
        'new_books': list_books(db, sort='newest')['books'][:5],
        'recommended_books': [book_context(row) for row in db.execute(
            'SELECT * FROM books WHERE is_recommended = 1 ORDER BY id ASC LIMIT 6')],
    }
