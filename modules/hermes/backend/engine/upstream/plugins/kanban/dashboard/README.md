# Hermes 원본 칸반 대시보드

용도: Hermes 원본 대시보드의 `/kanban` 화면과 작업판 설명 문구를 안내합니다.

- `manifest.json`: 칸반 탭의 주소, 화면 묶음, API 연결을 지정합니다.
- 실행 중인 Hermes 원본 화면은 `runtime/ai_agent/HermesOriginal/source/plugins/kanban/dashboard/dist/index.js`의 플러그인 화면 묶음을 읽습니다.
- 열별 상태 설명과 버튼 문구는 Hermes 웹 한국어 사전 `runtime/ai_agent/HermesOriginal/source/web/src/i18n/ko.ts`에서 관리합니다. 수정 뒤에는 같은 설치본의 `source/web`에서 `npm run build`를 실행해 `source/hermes_cli/web_dist/`에 반영합니다.
- 카드·작업판의 데이터 처리는 `plugin_api.py`가 기존 칸반 API와 연결합니다. 설명 문구를 고칠 때 작업 상태 변경·배정 코드는 수정하지 않습니다.

확인 방법: 60750 원본 대시보드의 `/kanban` 화면을 새로 불러와 버튼 도움말과 각 열의 설명을 확인합니다. 최근 확인에서는 `분류`, `할 일`, `준비됨`, `진행 중`, `차단됨` 설명이 쉬운 한국어로 표시됐습니다. 기능 동작이나 실제 작업 실행은 이 문구 변경으로 검증하지 않았습니다.
