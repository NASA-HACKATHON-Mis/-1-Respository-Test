# 백엔드 ↔ Jinja2 계약 v1

이 문서가 두 담당자의 공통 기준이다. P0부터 이 형태로 병렬 작업한다. JSON API/SPA는 만들지 않는다.

## HTTP / 템플릿

| 메서드·경로 | 입력 | 템플릿 / 결과 |
|---|---|---|
| GET `/` | 없음 | `home.html`: bestseller_books, new_books, recommended_books |
| GET `/books` | category, sort, page | `books.html`: books, filters, pagination |
| GET `/search` | q, category, sort, page | `search.html`: books, filters, pagination |
| GET `/books/{book_id}` | 정수 ID | `book_detail.html`: book |
| GET `/cart` | 없음 | `cart.html`: cart |
| POST `/cart/items` | book_id, quantity | 장바구니에 수량 추가 → 303 `/cart` |
| POST `/cart/items/{book_id}/quantity` | quantity | 해당 수량으로 교체 → 303 `/cart` |
| POST `/cart/items/{book_id}/remove` | 없음 | 항목 삭제 → 303 `/cart` |
| POST `/buy-now/{book_id}` | quantity | 장바구니 기존 항목 유지, 해당 도서 수량 추가 → 303 `/checkout` |
| GET `/checkout` | 없음 | `checkout.html`: cart, form |
| POST `/checkout` | recipient_name, shipping_address | 재고 검증·테스트 주문 생성 → 303 `/order-complete/{order_id}` |
| GET `/order-complete/{order_id}` | 세션 소유 주문 ID | `order_complete.html`: order |

변경 요청은 `application/x-www-form-urlencoded`와 `csrf_token` 필드를 쓴다.
quantity는 정수 1~99이며 현재 재고 이하여야 한다. 추가 시 기존 수량까지 합쳐 검증한다.
빈 장바구니의 checkout은 303 `/cart`; 빈 장바구니 주문 POST는 400이다.
없는 도서/접근 불가 주문은 404, 재고 부족은 409, 잘못된 폼은 422, CSRF 실패는 403.
폼 오류는 해당 화면을 같은 상태 코드로 재렌더링하며 입력값과 errors를 유지한다.
그 외 없는 리소스는 `error.html`에 status_code/message를 전달한다.

## 공통 context

모든 화면에 `request`, `categories`, `cart_count`, `csrf_token`, `errors`를 제공한다.
categories는 문자열 목록: 소설 / 자기계발 / 경제·경영 / 인문·교양 / 과학·IT.
errors는 `[{field: "quantity", message: "재고를 초과했습니다."}]`, 정상은 빈 배열.
cart_count는 장바구니 전체 수량이다. 템플릿 이름은 architecture 문서의 파일명에 `.html`을 붙인다.

| 객체 | 필드와 의미 |
|---|---|
| Book | `data.md`의 snake_case 전체 필드 + discount_percent(정수, 소수점 버림) |
| filters | q(문자열, 기본 빈 값), category(기본 빈 값=전체), sort(기본 popular) |
| pagination | page(기본 1), page_size(20), total_items, total_pages(최소 1) |
| Cart | items(배열), total_quantity, total_price(원 정수) |
| CartItem | book_id, title, cover_image, unit_price, quantity, stock, subtotal |
| form | recipient_name, shipping_address(초기 빈 문자열) |
| Order | id, recipient_name, shipping_address, total_price, status, created_at, items |
| OrderItem | book_id, title, unit_price, quantity, subtotal |

`sort` 값은 popular(sales_count DESC), newest(published_at DESC), price_asc, price_desc.
동률은 id ASC. 검색은 제목/저자/출판사 부분 문자열, 빈 q는 전체, category와 함께 적용한다.
미지원 sort/category와 page<1/비정수는 422; 마지막 페이지를 넘으면 빈 목록을 반환한다.
홈 베스트셀러 5권, 신간 5권, 추천 6권. 가격 표시와 할인율은 0원 정가를 허용하지 않는 데이터 제약을 따른다.
cover_image는 `/static/covers/01.svg` 형식이다. 날짜는 ISO 문자열, 추천 여부는 Python bool로 제공한다.

## 독립 UI 작업

B가 `tests/fixtures/contexts.json`과 `tools/preview_ui.py`를 소유한다.
preview 렌더러는 별도 로컬 개발 앱/명령이며 제품의 `app/main.py`와 라우터를 수정하지 않는다.
실제 sqlite3와 A의 서비스 없이 같은 템플릿을 렌더링한다. 기본 Book fixture는 sample-data.md의 1번 도서를 사용한다.
정상/검색 없음/품절/빈 장바구니/수량 초과/입력 오류/주문 완료 context를 만든다.
P0에서 fixture의 필드와 자료형을 A가 확인한 다음, 화면 PR과 서버 PR은 독립적으로 진행한다.
버튼의 실제 DB 변경은 통합 이슈에서 검증한다. fixture 미리보기를 제품 구현 완료로 간주하지 않는다.
