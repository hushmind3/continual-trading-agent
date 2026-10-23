# 기반 개요 소메뉴

용도: 나자릭 본체·확장 영역과 현재 연결 정의를 보여줍니다.

- 구현: `manager.py`의 GET `overlord/nazarick/overview`.
- 직접 의존: `../store.py`, `../adapters.py`; 상위 `../manager.py`가 취합합니다.
- 프론트: `modules/nazarick/frontend/Nazarick.tsx`, `FoundationMap.tsx`.
- 확인: 기존 단일 API와 `#overlord/nazarick/overview`에서 실제 저장값·등록 목록을 조회합니다. 가상의 고객·매출·작업 수를 만들지 않습니다.

실제 확인 결과·미완료 범위는 [중메뉴 안내](../README.md)를 따릅니다.
