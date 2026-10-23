# 모듈 화면 위치 안내

용도: 플랫폼 화면의 실제 소유 모듈을 찾는 연결 문서입니다. 업무 화면의 구현 기준 위치는 이 폴더가 아닌 각 modules/<id>/frontend입니다.

- [금융](../../../modules/finance/frontend/README.md): 운영·가상계좌·정책 학습·MoE·연결 설정.
- [REA 역공학](../../../modules/rea/frontend/README.md): 프로그램 분석·프로젝트 탐색.
- [Hermes](../../../modules/hermes/frontend/README.md): AI 에이전트 → Hermes → 기능별 소메뉴.
- [GitHub 프로젝트 관리](../../../modules/projects/README.md): 설치 앱과 프로젝트 관리.

전체 총괄은 src/shell/menu_groups/menu_registry.ts이며 modules/*/module.json의 프론트 진입점을 자동 취합합니다. 공통 UI는 frontend/src/ui/, 공통 디자인은 frontend/src/tailwind.css에 있습니다. 별도의 금융·REA 이동 안내 폴더는 유지하지 않으며 위 링크로 실제 구현 문서에 바로 연결합니다.
