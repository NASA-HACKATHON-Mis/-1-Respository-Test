# 기술 스택과 작업 경계

## 확정 스택

- Python 3.12 이상, FastAPI, Uvicorn.
- 데이터베이스: Python 표준 라이브러리 `sqlite3`. ORM은 사용하지 않는다.
- 서버 렌더링: Jinja2 (`Jinja2Templates`), 정적 HTML/CSS, 필요한 최소 JavaScript.
- 폼: `python-multipart`, 쿠키 세션: Starlette `SessionMiddleware`와 `itsdangerous`.
- 검증: pytest와 httpx/TestClient. Node.js 빌드 과정은 없다.

## 디렉터리와 소유권

```text
app/
  main.py                 # A: 앱/라우터/미들웨어/정적 파일 등록
  db.py                   # A: 연결, 외래키 설정, 트랜잭션
  schema.sql              # A: 테이블/제약조건
  seed.py                 # A: 시드 실행
  routers/                # A: catalog.py, cart.py, orders.py
  services/               # A: 조회/장바구니 검증/주문 처리
  templates/              # B: base, home, books, book_detail,
                          #    search, cart, checkout, order_complete, error
  static/css/             # B: 반응형 스타일
  static/js/              # B: 최소 상호작용
  static/covers/          # B: 직접 만든 표지 01.svg ~ 20.svg
data/books.json           # A: 공통 시드 원본
tests/backend/            # A: DB/HTTP/주문 테스트
tests/ui/                 # B: 렌더링/화면 검증
tools/preview_ui.py        # B: 개발용 fixture 렌더러; 제품 라우터와 분리
tests/fixtures/contexts.json # B: 계약을 따르는 화면 샘플
var/bookstore.sqlite3     # 로컬 생성, Git 추적 제외
requirements.txt          # A: 의존성 단일 관리
README.md                 # A: 실행 방법, B는 화면 검증 결과 별도 문서
```

A는 백엔드/DB, B는 화면/Jinja2 담당이다. 사람 이름과 GitHub assignee는 아직 지정하지 않는다.
각자 소유 디렉터리만 수정하고, 상대 변경은 별도 요청으로 전달한다. 공통 파일 변경은 A가 반영한다.
기능은 `docs/contracts.md`에 맞춘다. 계약 변경은 상대가 확인한 뒤 문서와 fixture를 같은 PR에서 수정한다.

## 실행 목표 (구현할 명령)

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.seed
$env:SESSION_SECRET = 'local-development-secret-change-before-sharing'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

`SESSION_SECRET`은 환경 변수에서 읽으며 실제 공유용 값을 커밋하지 않는다.
위 명령은 개발 완료 시 제공할 인터페이스이며, 현재 저장소에는 앱이 아직 없다.

## sqlite3 / 세션 규칙

- DB 작업은 요청 단위 연결을 사용하고 닫는다. 동기 DB 코드는 동기 라우트/서비스로 실행한다.
- 모든 연결에서 `PRAGMA foreign_keys=ON`; SQL 값은 파라미터 바인딩한다.
- 주문은 `BEGIN IMMEDIATE`부터 재고 재검증, 차감, 주문 저장까지 같은 연결과 트랜잭션으로 처리한다. 실패하면 전부 rollback한다.
- 장바구니는 서명된 세션 쿠키의 도서 ID/수량만 저장한다. 수령인·주소·가격은 쿠키에 넣지 않는다. MVP 최대 20종, 도서별 1~99권.
- 서버가 DB 가격과 재고를 다시 읽어 합계를 계산한다. 주문 성공 후 장바구니를 비우고 303 redirect한다.
- 주문 완료 URL은 세션이 주문한 ID에만 접근 가능하게 한다. 다른 세션에는 404를 반환한다.
- 모든 변경 폼에 세션 CSRF 토큰을 사용한다. Jinja2 HTML escape를 유지한다.

참고: [FastAPI 템플릿](https://fastapi.tiangolo.com/advanced/templates/), [폼 입력](https://fastapi.tiangolo.com/tutorial/request-forms/).
