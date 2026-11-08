# 데이터베이스와 샘플 데이터

## 도서 데이터베이스 설계

| 필드 | 자료형 | 의미 |
|---|---|---|
| id | Integer | 고유번호 |
| title | String | 도서명 |
| subtitle | String? | 부제목 |
| author | String | 저자 |
| publisher | String | 출판사 |
| published_at | Date | 출간일 |
| isbn13 | String? | ISBN-13; 가상 책은 null |
| category | String | 소설/자기계발/경제·경영/인문·교양/과학·IT |
| description | Text | 책 소개 |
| author_bio | Text | 저자 소개 |
| table_of_contents | Text | 목차 |
| cover_image | String | 로컬 표지 경로 |
| list_price | Integer | 정가(원) |
| sale_price | Integer | 판매가(원) |
| stock | Integer | 재고 |
| page_count | Integer | 쪽수 |
| rating | Float | 테스트 평점(0~5) |
| review_count | Integer | 테스트 리뷰 수 |
| sales_count | Integer | 테스트 판매량 |
| is_recommended | Boolean | MD 추천 여부 |
| created_at | DateTime | 등록 시각 |

할인율은 `(list_price - sale_price) / list_price * 100`으로 계산하며 정수 가격을 화면에서 `원`으로 표시한다. 품절 도서는 구매 불가 처리한다. 가상 도서에는 실제처럼 보이는 임의 ISBN을 할당하지 않는다.

### 주문 데이터

**Order:** id, recipient_name, shipping_address, total_price, status, created_at.

**OrderItem:** id, order_id, book_id, title, unit_price, quantity.

주문 완료 시점의 제목과 가격을 주문 항목에 별도 저장한다. 재고 확인과 차감, 주문 생성은 한 데이터베이스 트랜잭션으로 처리한다. 테스트 주문임을 화면에 명확하게 표시한다. 개인 정보는 필요한 최소 항목만 수집하고 테스트 이외의 용도로 쓰지 않는다.

## 샘플 데이터

가상 도서 20권의 목록·소개·생성 규칙은 [sample-data.md](sample-data.md)에 분리했다.

## sqlite3 스키마 규칙

원본 표의 Integer는 INTEGER, String/Text/Date/DateTime은 TEXT, Float는 REAL로 구현한다.
`?` 표시 필드만 NULL을 허용한다. Boolean은 INTEGER 0/1로 저장하고 context에서는 bool로 변환한다.
테이블은 books/orders/order_items, id는 INTEGER PRIMARY KEY, 주문 ID도 정수이다.
외래키는 order_items.order_id → orders.id, book_id → books.id로 설정한다.
가격은 원 단위 정수, list_price > 0, 0 <= sale_price <= list_price, stock >= 0,
quantity 1~99, page_count > 0, rating 0~5를 CHECK로 검증한다.
status는 테스트 주문 완료를 나타내는 `test_completed`로 저장한다. published_at은 YYYY-MM-DD,
created_at은 UTC ISO 문자열이다. 주문 title/unit_price는 books와 별도로 스냅샷 저장한다.

## 시드와 fixture 계약

- sample-data.md의 20권 제목/저자/소개/가격을 그대로 `data/books.json`에 옮긴다. 실제 출판물로 바꾸지 않는다.
- cover_image는 ID 순서대로 `/static/covers/01.svg` ~ `/static/covers/20.svg`.
- B가 표지를 제작한다. DB seed는 이미지 파일 완성을 기다리지 않는다.
- 입력 JSON을 검증한 뒤 단일 트랜잭션으로 seed한다. 최초 삽입 후 재실행은 기존 ID를 건너뛰어 주문 재고를 보존한다.
- 초기화가 필요하면 별도 명시적 개발용 reset 명령을 둔다. 기본 seed는 기존 데이터 삭제를 하지 않는다.
- A가 정한 나머지 샘플 필드를 B의 fixture에서 그대로 재사용한다. 실행 DB 파일은 추적하지 않는다.