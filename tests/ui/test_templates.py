"""UI contract checks. Run with: python -m pytest tests/ui -p no:cacheprovider"""

from copy import deepcopy
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from pathlib import Path
import re
import sys
import threading
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.preview_ui import ROOT, catalog_context, load_fixtures, make_handler, render_scenario


FIXTURES = load_fixtures()


class Document(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.forms = []
        self.current_form = None
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.nodes.append((tag, attrs))
        if tag == "form":
            self.current_form = {"attributes": attrs, "controls": []}
            self.forms.append(self.current_form)
        elif self.current_form is not None and tag in ("input", "select", "textarea", "button"):
            self.current_form["controls"].append((tag, attrs))

    def handle_endtag(self, tag):
        if tag == "form":
            self.current_form = None


@pytest.mark.parametrize("scenario", FIXTURES["scenarios"])
def test_all_contract_contexts_render_accessible_documents(scenario):
    markup = render_scenario(scenario, FIXTURES)
    document = Document(markup)
    assert '<html lang="ko">' in markup
    assert sum(tag == "h1" for tag, _ in document.nodes) == 1
    ids = [attrs["id"] for _, attrs in document.nodes if "id" in attrs]
    assert len(ids) == len(set(ids)), "Duplicate IDs break labels and error references"
    labels = {attrs.get("for") for tag, attrs in document.nodes if tag == "label"}
    for tag, attrs in document.nodes:
        if tag == "img":
            assert "alt" in attrs
            assert (ROOT / "app" / attrs["src"].lstrip("/")).is_file()
        if tag in ("input", "select", "textarea") and attrs.get("type") != "hidden":
            assert attrs.get("id") in labels
        for reference in attrs.get("aria-describedby", "").split():
            assert reference in ids
        if tag == "a":
            assert attrs.get("href") and attrs["href"] != "#"
    assert "테스트" in markup


@pytest.mark.parametrize("scenario", FIXTURES["scenarios"])
def test_mutating_forms_match_backend_contract_and_have_csrf(scenario):
    document = Document(render_scenario(scenario, FIXTURES))
    for form in document.forms:
        if form["attributes"].get("method", "get").lower() != "post":
            continue
        action = form["attributes"]["action"]
        controls = {attrs.get("name"): attrs for _, attrs in form["controls"] if attrs.get("name")}
        assert controls["csrf_token"]["type"] == "hidden"
        assert controls["csrf_token"]["value"] == FIXTURES["common"]["csrf_token"]
        if action == "/cart/items":
            assert {"book_id", "quantity"} <= controls.keys()
        elif re.fullmatch(r"/cart/items/\d+/quantity", action):
            assert "quantity" in controls
        elif re.fullmatch(r"/cart/items/\d+/remove", action):
            assert set(controls) == {"csrf_token"}
        else:
            assert action == "/checkout"
            assert {"recipient_name", "shipping_address"} <= controls.keys()
        for _, attrs in form["controls"]:
            if "formaction" in attrs:
                assert re.fullmatch(r"/buy-now/\d+", attrs["formaction"])
                assert "quantity" in controls


def test_fixture_books_match_documented_titles_prices_descriptions_and_assets():
    text = (ROOT / "docs" / "sample-data.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| (\d+) \| (.*?) \| (.*?) \| (.*?) \| ([\d,]+) \| ([\d,]+) \|$", text, re.M)
    assert len(FIXTURES["books"]) == len(rows) == 20
    assert sum(book["is_recommended"] for book in FIXTURES["books"]) == 6
    assert any(book["stock"] == 0 for book in FIXTURES["books"])
    for book, row in zip(FIXTURES["books"], rows):
        ident, title, author, category, list_price, sale_price = row
        assert (book["id"], book["title"], book["author"], book["category"]) == (int(ident), title, author, category)
        assert (book["list_price"], book["sale_price"]) == (int(list_price.replace(",", "")), int(sale_price.replace(",", "")))
        assert book["discount_percent"] == (book["list_price"] - book["sale_price"]) * 100 // book["list_price"]
        assert book["isbn13"] is None
        assert isinstance(book["is_recommended"], bool)
        cover = ET.parse(ROOT / "app" / book["cover_image"].lstrip("/")).getroot()
        assert cover.attrib["viewBox"] == "0 0 240 360"
        assert title == cover.find("{http://www.w3.org/2000/svg}title").text


def test_sold_out_books_cannot_submit_purchase_forms():
    document = Document(render_scenario("sold-out", FIXTURES))
    purchase = next(form for form in document.forms if form["attributes"].get("method") == "post")
    buttons = [attrs for tag, attrs in purchase["controls"] if tag == "button"]
    assert len(buttons) == 2 and all("disabled" in attrs for attrs in buttons)
    assert "품절" in render_scenario("sold-out", FIXTURES)


def test_checkout_preserves_and_escapes_user_input_and_connects_field_error():
    name = '<script>alert("name")</script>'
    address = '</textarea><img src=x onerror="alert(1)">'
    markup = render_scenario("checkout-error", FIXTURES, {
        "form": {"recipient_name": name, "shipping_address": address},
    })
    assert name not in markup and address not in markup
    document = Document(markup)
    recipient = next(attrs for tag, attrs in document.nodes if attrs.get("id") == "recipient_name")
    shipping = next(attrs for tag, attrs in document.nodes if attrs.get("id") == "shipping_address")
    assert recipient["value"] == name
    assert shipping["aria-invalid"] == "true"
    assert shipping["aria-describedby"] == "shipping-address-errors"
    assert "배송지를 입력해 주세요." in markup


def test_filters_and_pagination_keep_search_category_and_sort():
    markup = render_scenario("books", FIXTURES, {
        "filters": {"q": "책 & <검색>", "category": "과학·IT", "sort": "price_desc"},
        "pagination": {"page": 2, "page_size": 20, "total_items": 65, "total_pages": 4},
    })
    document = Document(markup)
    selected = [attrs["value"] for tag, attrs in document.nodes if tag == "option" and "selected" in attrs]
    assert selected == ["과학·IT", "price_desc"]
    page_links = [attrs["href"] for tag, attrs in document.nodes if tag == "a" and "page=" in attrs.get("href", "")]
    assert len(page_links) == 2
    for link in page_links:
        query = parse_qs(urlsplit(link).query)
        assert query["q"] == ["책 & <검색>"]
        assert query["category"] == ["과학·IT"]
        assert query["sort"] == ["price_desc"]


def test_cart_and_order_use_contract_items_rather_than_dictionary_methods():
    for scenario in ("cart", "checkout", "order-complete"):
        markup = render_scenario(scenario, FIXTURES)
        assert "시간을 걷는 서점" in markup
        assert "하루를 바꾸는 작은 습관" in markup
        assert "46,440" in markup
    assert 'href="/checkout"' not in render_scenario("cart-empty", FIXTURES)


def test_home_collection_sizes():
    home = FIXTURES["scenarios"]["home"]["context"]
    assert [len(home[key]) for key in ("bestseller_books", "new_books", "recommended_books")] == [5, 5, 6]


@pytest.fixture(scope="module")
def preview_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FIXTURES))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.mark.parametrize("path", ["/", "/books", "/search?q=서점", "/books/1", "/cart", "/checkout", "/order-complete/1001"])
def test_read_only_preview_routes(preview_url, path):
    from urllib.parse import quote

    with urlopen(preview_url + quote(path, safe="/?=")) as response:
        assert response.status == 200
        assert "개발용 fixture 미리보기" in response.read().decode("utf-8")


def test_preview_rejects_post_without_changing_fixture(preview_url):
    snapshot = deepcopy(FIXTURES)
    with pytest.raises(HTTPError) as raised:
        urlopen(Request(preview_url + "/checkout", data=b"recipient_name=test", method="POST"))
    assert raised.value.code == 405
    assert "변경할 수 없습니다" in raised.value.read().decode("utf-8")
    assert FIXTURES == snapshot


@pytest.mark.parametrize("path,status", [("/missing", 404), ("/books/999", 404), ("/books?sort=bad", 422), ("/static/../templates/base.html", 404)])
def test_preview_errors_are_html_and_static_root_is_confined(preview_url, path, status):
    with pytest.raises(HTTPError) as raised:
        urlopen(preview_url + path)
    assert raised.value.code == status
    assert "text/html" in raised.value.headers["Content-Type"]


def test_preview_get_filtering_uses_fixture_only():
    assert catalog_context(FIXTURES, {"q": ["김서윤"]}, search=True)["books"][0]["id"] == 1
    result = catalog_context(FIXTURES, {"category": ["과학·IT"], "sort": ["price_asc"]})
    assert len(result["books"]) == 4
    assert all(book["category"] == "과학·IT" for book in result["books"])
    assert [b["sale_price"] for b in result["books"]] == sorted(b["sale_price"] for b in result["books"])
    assert catalog_context(FIXTURES, {"page": ["2"]})["books"] == []
