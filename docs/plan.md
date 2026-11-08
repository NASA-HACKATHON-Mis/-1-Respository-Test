# 2인 병렬 개발 계획

포지션 A = `position:backend`(Python/FastAPI/sqlite3), B = `position:frontend`(Jinja2/CSS/최소 JS).
각 phase는 일정 순서 표시다. 이전 phase 전체를 기다리지 않고 아래의 자기 선행 작업만 끝나면 시작한다.
사람별 GitHub 계정은 미지정이므로 assignee 대신 포지션 라벨을 쓴다.

| Phase | A: 백엔드/DB | B: 화면/Jinja2 | 합류 기준 |
|---|---|---|---|
| P0 기반 | A0 앱 구조·의존성·DB 연결 | B0 레이아웃·fixture 미리보기 | 계약 v1과 필드 확인 |
| P1 도서 | A1 스키마·20권 시드·도서 조회 라우트 | B1 홈·목록·검색·상세·표지 | 동일 context, 아직 별도 검증 가능 |
| P2 구매 | A2 세션 장바구니·주문 트랜잭션 | B2 장바구니·주문·완료·오류 화면 | 폼 경로/필드 일치 |
| P3 통합 | A3 실제 DB/세션으로 HTTP 흐름 통합 | B3 반응형·접근성·모든 링크/폼 연결 | 실제 앱에서 전체 구매 흐름 |
| P4 인수 | A4 DB/주문 회귀·실행 README | B4 화면 인수·검증 보고 | acceptance 체크리스트 충족 |

## 작업별 선행 조건

```text
A0 → A1 → A2 ─────┐
B0 → B1 → B2 ─────┴→ A3 → A4
       └→ B3 (fixture로 먼저 진행) → B4
                              A3 ─→ B4
```

- A1은 A0만, B1은 B0만 기다린다. A2는 A1, B2는 B1만 기다린다.
- A3의 필수 선행은 A2와 B2. 준비된 도서 화면은 A1/B1 종료 시 먼저 연결한다.
- B3는 B1/B2 후 fixture로 반응형을 검증한다. 실제 폼 동작 검증만 A3 결과를 기다린다.
- A4는 A3 후, B4는 A3와 B3 후 진행한다. 최종 완료는 A4/B4 모두 필요하다.

## 충돌과 대기 줄이기

- 브랜치는 `feat/a0-app-base`, `feat/b0-ui-base`처럼 이슈 하나당 하나를 만든다.
- A가 main.py/requirements/DB/라우터를, B가 templates/static/fixture를 수정한다.
- A1이 데이터 JSON의 표지 경로를 먼저 확정하고, B1은 같은 파일명으로 제작한다.
- 상대 코드가 없으면 fixture나 서비스 단위 테스트로 진행한다. 상대 파일을 임시 구현해 중복 작업하지 않는다.
- PR에는 `Closes #이슈번호`, 변경한 계약, 실행한 검증을 적는다. 작은 기능 단위로 병합한다.
- SQLite 파일, `.venv`, 비밀 값, 주문 개인정보는 커밋하지 않는다.
- 역할 라벨과 phase 라벨을 함께 붙인다. 실제 이슈 번호·링크는 아래 등록 결과를 본다.

## GitHub 등록 결과

작업별 상세 범위와 완료 조건은 GitHub 이슈 본문에 둔다. 모든 필수 선행은 GitHub의 blocked by 관계로도 등록했다.

| 작업 | 이슈 | 포지션 | 필수 선행 |
|---|---|---|---|
| A0 | [#1 [P0][Backend] FastAPI 실행 기반과 sqlite3 연결 구성](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/1) | position:backend | 없음 |
| B0 | [#2 [P0][Frontend] Jinja2 공통 레이아웃과 fixture 미리보기](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/2) | position:frontend | 없음 |
| A1 | [#3 [P1][Backend] 도서 스키마·20권 seed·검색 및 조회 라우트](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/3) | position:backend | [#1](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/1) |
| B1 | [#4 [P1][Frontend] 홈·목록·검색·상세와 도서 표지 20개](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/4) | position:frontend | [#2](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/2) |
| A2 | [#5 [P2][Backend] 세션 장바구니와 원자적 테스트 주문](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/5) | position:backend | [#3](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/3) |
| B2 | [#6 [P2][Frontend] 장바구니·checkout·주문 완료·오류 화면](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/6) | position:frontend | [#4](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/4) |
| A3 | [#7 [P3][Backend] 실제 DB·Jinja2·세션 구매 흐름 통합](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/7) | position:backend | [#5](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/5), [#6](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/6) |
| B3 | [#8 [P3][Frontend] 반응형·접근성·링크와 폼 연결 점검](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/8) | position:frontend | [#6](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/6) |
| A4 | [#9 [P4][Backend] 주문 회귀 검증과 Windows 실행 README](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/9) | position:backend | [#7](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/7) |
| B4 | [#10 [P4][Frontend] 실제 앱 사용자 흐름 인수와 화면 검증 보고](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/10) | position:frontend | [#7](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/7), [#8](https://github.com/NASA-HACKATHON-Mis/-1-Respository-Test/issues/8) |