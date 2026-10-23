# 오버로드 대메뉴

용도: 오버로드 소속 중메뉴를 취합해 기존 전체 메뉴 총괄·단일 `/api`에 연결합니다.

- `manager.py`: [나자릭 중메뉴](nazarick/README.md)의 `GROUP`·`ROUTERS`를 취합합니다.
- 등록 진입점: `modules/nazarick/module.json` → `modules/nazarick/backend/manager.py` → 이 대메뉴 매니저 → `menu_registry.py` → 단일 `/api`.
- 업무 코드와 데이터는 중메뉴가 소유합니다. 대메뉴에 별도 서버·실행기·DB를 만들지 않습니다.

화면: 오버로드 → 나자릭 → 기반 개요·연결 대상·작업 기록. 구현·실제 확인 범위는 중메뉴 README를 따릅니다.
