# 개발 문서 안내

기술 스택은 **Python · FastAPI · sqlite3 · Jinja2**로 확정한다.
기존 단일 명세의 기능/도서 데이터는 아래 문서에 분리했다. 이 파일은 진입점이다.

| 문서 | 내용 |
|---|---|
| [프로젝트 범위](docs/scope.md) | 목표, 필수 기능, 제외 범위, MVP 원칙 |
| [아키텍처](docs/architecture.md) | 확정 스택, 실행 목표, 디렉터리와 두 사람의 소유권 |
| [공통 계약](docs/contracts.md) | HTTP 경로, 폼 필드, Jinja2 context, 오류 규칙 |
| [화면 명세](docs/ui.md) | 페이지 구성과 반응형 디자인 |
| [데이터 명세](docs/data.md) | sqlite3 스키마와 seed 규칙 |
| [샘플 도서](docs/sample-data.md) | 가상 도서 20권, 소개와 추가 샘플 생성 규칙 |
| [병렬 개발 계획](docs/plan.md) | 포지션별 phase, 선행 조건, GitHub 이슈 링크 |
| [검증 기준](docs/acceptance.md) | 역할별 검증과 최종 인수 조건 |

먼저 범위/아키텍처/공통 계약을 읽고 자기 포지션의 이슈를 시작한다.
현재는 계획 문서만 존재한다. 앱 코드와 실행/테스트 명령은 각 이슈에서 구현한다.