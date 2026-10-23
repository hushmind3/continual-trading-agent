# 작업 기록 소메뉴

용도: 연결 정의 변경과 실제 어댑터 확인 결과를 조회합니다.

- 구현: `manager.py`의 GET `overlord/nazarick/activity/list`.
- 직접 의존: `../store.py`; 최근 100건을 최신순으로 읽습니다.
- 프론트: `modules/nazarick/frontend/Activity.tsx`.
- 확인: 실제 대상 등록·확인 후 작업 이름·결과·시간·확인 범위와 재조회 시 보존 여부를 확인합니다. 범용 작업 실행기나 매출 기록 기능은 아닙니다.

실제 확인 결과·남은 작업은 [중메뉴 안내](../README.md)를 따릅니다.
