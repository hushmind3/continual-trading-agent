# 연결 대상 소메뉴

용도: 대상 정의 저장·수정·제거와 구현된 어댑터의 등록 확인을 담당합니다.

- 구현: `manager.py`; GET `overlord/nazarick/connections/list`, POST `save`, `inspect`, `remove`.
- 직접 의존: `../store.py`의 SQLite 트랜잭션·작업 기록, `../adapters.py`의 명시적 등록표.
- 입력: 이름·영역·연결 방식·기존 모듈 ID·용도 메모. 입력 스키마는 알 수 없는 필드를 거절하며 키·토큰을 받지 않습니다.
- `planned`는 외부 연결부 미구현, `unchecked`는 저장 후 미확인, `registered`는 서버의 모듈 등록 확인, `failed`는 확인 실패입니다. 수정하면 이전 확인 상태를 초기화합니다.
- 제거는 연결 정의에만 적용하며 실제 기능·대상 데이터는 제거하지 않습니다. 성공·실패·정의 변경은 같은 트랜잭션에서 기록합니다.
- 프론트: `modules/nazarick/frontend/Connections.tsx`, `ConnectionForm.tsx`.

확인: 기존 플랫폼 기능을 선택해 저장·등록 확인·재조회합니다. 외부 예정 대상의 inspect는 HTTP 409이며 외부 요청을 보내지 않습니다. 전체 실제 확인 결과는 [중메뉴 안내](../README.md)를 따릅니다.
