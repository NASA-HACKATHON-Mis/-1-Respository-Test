"""Read-only Jinja2 fixture preview, independent of the product app and DB.

    python tools/preview_ui.py --port 8765
    python tools/preview_ui.py --render-dir <directory>

POST requests deliberately return 405: this tool does not simulate purchases.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlencode, urlsplit, unquote

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "contexts.json"
TEMPLATES = ROOT / "app" / "templates"
STATIC = ROOT / "app" / "static"


def environment():
    return Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "xml"]),
        undefined=StrictUndefined,
    )


def load_fixtures():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


def render_scenario(name, fixtures=None, context_overrides=None):
    fixtures = fixtures or load_fixtures()
    scenario = fixtures["scenarios"][name]
    context = deepcopy(fixtures["common"])
    context.update(deepcopy(scenario["context"]))
    context.update(context_overrides or {})
    # FastAPI supplies the real request. Templates only need contract fields;
    # this placeholder prevents the fixture from depending on Starlette.
    context["request"] = SimpleNamespace(url=scenario["path"])
    return environment().get_template(scenario["template"]).render(**context)


def preview_banner(name, fixtures):
    from html import escape

    options = "".join(
        f'<option value="{escape(key, quote=True)}"'
        f'{" selected" if key == name else ""}>{escape(value["label"])}</option>'
        for key, value in fixtures["scenarios"].items()
    )
    return (
        '<aside aria-label="개발용 미리보기" style="background:#fff3ca;'
        'color:#413712;padding:12px 18px;font:12px/1.8 sans-serif;'
        'border-bottom:1px solid #dfcf95">'
        '<strong>개발용 fixture 미리보기</strong> · DB 저장 및 주문 동작 없음. '
        '구매 폼을 제출하면 405 안내가 표시됩니다.'
        '<form action="/" method="get" style="display:inline-flex;gap:8px;'
        'align-items:center;flex-wrap:wrap;margin-left:12px">'
        '<label for="preview-scenario">화면 상태</label>'
        f'<select id="preview-scenario" name="scenario" style="max-width:100%">{options}</select>'
        '<button type="submit">미리보기</button></form></aside>'
    )


def catalog_context(fixtures, query, search=False):
    """Filter fixture values for GET navigation only; never a product service."""
    category = query.get("category", [""])[0]
    sort = query.get("sort", ["popular"])[0]
    q = query.get("q", [""])[0] if search else ""
    page_text = query.get("page", ["1"])[0]
    if category and category not in fixtures["common"]["categories"]:
        raise ValueError("지원하지 않는 카테고리입니다.")
    if sort not in ("popular", "newest", "price_asc", "price_desc"):
        raise ValueError("지원하지 않는 정렬입니다.")
    try:
        page = int(page_text)
    except ValueError:
        raise ValueError("페이지는 1 이상의 정수여야 합니다.") from None
    if page < 1:
        raise ValueError("페이지는 1 이상의 정수여야 합니다.")
    books = [
        book for book in fixtures["books"]
        if (not category or book["category"] == category)
        and (not q or any(q.casefold() in book[key].casefold() for key in ("title", "author", "publisher")))
    ]
    books.sort(key=lambda book: book["id"])
    key, reverse = {
        "popular": ("sales_count", True), "newest": ("published_at", True),
        "price_asc": ("sale_price", False), "price_desc": ("sale_price", True),
    }[sort]
    books.sort(key=lambda book: book[key], reverse=reverse)
    return {
        "books": books[(page - 1) * 20:page * 20],
        "filters": {"q": q, "category": category, "sort": sort},
        "pagination": {"page": page, "page_size": 20, "total_items": len(books), "total_pages": max(1, (len(books) + 19) // 20)},
    }


def make_handler(fixtures):
    class Handler(BaseHTTPRequestHandler):
        def send_content(self, status, content, content_type="text/html; charset=utf-8"):
            payload = content.encode("utf-8") if isinstance(content, str) else content
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def render(self, scenario, overrides=None, status=200):
            markup = render_scenario(scenario, fixtures, overrides)
            markup = markup.replace("<body>", "<body>" + preview_banner(scenario, fixtures), 1)
            self.send_content(status, markup)

        def do_GET(self):
            parsed = urlsplit(self.path)
            path = unquote(parsed.path)
            query = parse_qs(parsed.query, keep_blank_values=True)
            if path.startswith("/static/"):
                target = (STATIC / path.removeprefix("/static/")).resolve()
                if not target.is_relative_to(STATIC.resolve()) or not target.is_file():
                    self.render("not-found", status=404)
                    return
                self.send_content(200, target.read_bytes(), mimetypes.guess_type(target.name)[0] or "application/octet-stream")
                return
            if "scenario" in query:
                name = query["scenario"][0]
                if name not in fixtures["scenarios"]:
                    self.render("not-found", status=404)
                    return
                self.render(name)
                return
            if path in ("/books", "/search"):
                try:
                    context = catalog_context(fixtures, query, path == "/search")
                except ValueError as error:
                    self.render("not-found", {"status_code": 422, "message": str(error)}, 422)
                    return
                self.render("search" if path == "/search" else "books", context)
                return
            if path.startswith("/books/"):
                book = next((book for book in fixtures["books"] if str(book["id"]) == path.removeprefix("/books/")), None)
                if book is None:
                    self.render("not-found", status=404)
                    return
                self.render("book-detail", {"book": book})
                return
            routes = {"/": "home", "/cart": "cart", "/checkout": "checkout", "/order-complete/1001": "order-complete"}
            scenario = routes.get(path)
            self.render(scenario or "not-found", status=200 if scenario else 404)

        def do_POST(self):
            # Close rather than reading arbitrary request bodies in this read-only tool.
            self.close_connection = True
            self.render("not-found", {"status_code": 405, "message": "미리보기에서는 주문이나 장바구니를 변경할 수 없습니다."}, 405)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--render-dir", type=Path)
    args = parser.parse_args()
    fixtures = load_fixtures()
    if args.render_dir:
        args.render_dir.mkdir(parents=True, exist_ok=True)
        for name in fixtures["scenarios"]:
            (args.render_dir / f"{name}.html").write_text(render_scenario(name, fixtures), encoding="utf-8")
        print(f"Rendered {len(fixtures['scenarios'])} fixture pages to {args.render_dir}")
        return
    server = ThreadingHTTPServer((args.host, args.port), make_handler(fixtures))
    print(f"Fixture preview: http://{args.host}:{args.port} (read-only, no database)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
