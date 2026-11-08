CREATE TABLE IF NOT EXISTS books (
 id INTEGER PRIMARY KEY,
 title TEXT NOT NULL, subtitle TEXT, author TEXT NOT NULL, publisher TEXT NOT NULL,
 published_at TEXT NOT NULL, isbn13 TEXT,
 category TEXT NOT NULL CHECK(category IN ('소설','자기계발','경제·경영','인문·교양','과학·IT')),
 description TEXT NOT NULL, author_bio TEXT NOT NULL, table_of_contents TEXT NOT NULL,
 cover_image TEXT NOT NULL,
 list_price INTEGER NOT NULL CHECK(list_price > 0),
 sale_price INTEGER NOT NULL CHECK(sale_price BETWEEN 0 AND list_price),
 stock INTEGER NOT NULL CHECK(stock >= 0),
 page_count INTEGER NOT NULL CHECK(page_count > 0),
 rating REAL NOT NULL CHECK(rating BETWEEN 0 AND 5),
 review_count INTEGER NOT NULL CHECK(review_count >= 0),
 sales_count INTEGER NOT NULL CHECK(sales_count >= 0),
 is_recommended INTEGER NOT NULL CHECK(is_recommended IN (0,1)),
 created_at TEXT NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS orders (
 id INTEGER PRIMARY KEY,
 recipient_name TEXT NOT NULL, shipping_address TEXT NOT NULL,
 total_price INTEGER NOT NULL CHECK(total_price >= 0),
 status TEXT NOT NULL CHECK(status = 'test_completed'), created_at TEXT NOT NULL
) STRICT;
CREATE TABLE IF NOT EXISTS order_items (
 id INTEGER PRIMARY KEY,
 order_id INTEGER NOT NULL REFERENCES orders(id),
 book_id INTEGER NOT NULL REFERENCES books(id),
 title TEXT NOT NULL, unit_price INTEGER NOT NULL CHECK(unit_price >= 0),
 quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 99)
) STRICT;
