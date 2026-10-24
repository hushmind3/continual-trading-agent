# 공용 계정·브라우저

용도: 플랫폼 상단 **서버 연결 옆 공용 설정 아이콘**에서 여는 계정 기반입니다. 소유 메뉴 ID는 `overlord/nazarick/accounts`이며 사이드바에서는 숨깁니다. 여러 에이전트가 선택한 공용 브라우저의 로그인 상태와 업체별 가입 진행 기록을 재사용합니다.

## 구현·연결

- `manager.py`: `../manager.py` → 오버로드 → 메뉴 총괄 → 단일 `/api`. GET `overlord/nazarick/accounts/status`; POST `browser/start`, `browser/open`, `services/save`, `services/import`, `credential`, `agents/connect`는 같은 접두사를 사용합니다.
- `providers.py`, `browser.py`: `modules/nazarick/module.json`의 `browser_providers`로 설치된 브라우저를 찾습니다. Chrome의 기존 `browser-profile/`은 유지하고 Brave/Edge는 같은 runtime의 `browser-profiles/<브라우저 ID>/`을 사용합니다. 일반 로그인 모드와 AI 연결 모드는 같은 전용 프로필을 사용하며, 명시적으로 모드를 바꿀 때만 그 프로필의 창을 재실행합니다. CDP는 loopback에만 바인드합니다. 실제 프로필 소유 PID를 복구하며 사용자 기본 프로필을 복사하거나 플랫폼 적용으로 브라우저를 종료하지 않습니다. Safari/Firefox는 기존 일반 창 열기만 지원하며 현재 공용 CDP 연결은 미지원입니다.
- `sessions.py`: 선택한 Chromium 공용 프로필의 쿠키 DB를 읽기 전용으로 열어 인증 쿠키 이름·만료·값 존재 여부만 확인합니다. 쿠키 값은 조회·복호화·복사·응답에 포함하지 않습니다. `account_providers`의 업체·주소·인증 쿠키 묶음을 사용하며 Google은 [공식 인증 쿠키 설명](https://policies.google.com/technologies/cookies?hl=ko)을 기준으로 합니다. `saved`는 저장된 인증 정보가 있다는 뜻이며 서버의 세션 유효성 검증과 구분합니다. DB 잠금/오류는 `unknown`, 지원하지 않는 브라우저는 `unsupported`로 표시해 미로그인으로 단정하지 않습니다. 저장된 계정은 로그인 URL 대신 계정 URL을 열고, 재로그인이나 모드 전환을 강제하지 않습니다.
- `state.py`: 같은 런타임의 `accounts.sqlite3`에 업체 이름·공식 HTTPS 주소·로그인 방식·진행 상태·메모·키 보관 여부만 저장합니다. 브라우저/연결 설정의 프로세스 간 잠금도 담당합니다. 업체 목록과 진행 기록은 로그인을 증명하지 않습니다.
- `vault.py`: macOS Security.framework의 키체인 API를 직접 사용합니다. API 키를 명령줄 인수·SQLite·응답·문서에 저장하지 않습니다. 현재 다른 OS의 키 저장은 미지원이며 브라우저/업체 목록은 별개입니다.
- `integration.py`: 버튼을 눌렀을 때만 로컬 Codex MCP 설정, Hermes 프로필별 `BROWSER_CDP_URL` 및 `shared-accounts` 스킬, OpenClaw의 `platform` attach-only 브라우저 프로필·공용 계정 스킬을 병합합니다. 변경 전 설정은 소유 runtime의 `settings-before-shared/`에 보존합니다. 모델·기존 인증키는 변경하지 않습니다.
- `cli.py`: 표준 입출력 MCP `mcp-accounts`와 `mcp-browser`, 업체 목록 `list`, 진행 기록 `update ID STATUS --notes 내용`, 키 주입 실행 `run --service ID --env API_KEY -- COMMAND`. 호출은 프로젝트 `.venv/platform/bin/python backend/overlord/nazarick/accounts/cli.py ...`를 사용합니다. 키 주입을 받은 프로그램이 자신의 환경변수를 출력하지 않도록 사용해야 합니다.
- `mcp-browser`는 기존 OpenClaw 설치의 Google 공식 `chrome-devtools-mcp`를 재사용합니다. 현재 설치 버전 1.10.1이며 사용 통계·CrUX·성능/네트워크 도구를 끕니다. 설치본이 없으면 명시적으로 실패하고 자동 다운로드하지 않습니다. Codex 설정은 프로젝트 `.codex/config.toml`에 로컬 절대 경로로 생성하며 Git에서 제외합니다. [공식 MCP 설정 규격](https://learn.chatgpt.com/docs/extend/mcp)을 따릅니다.
- 화면: [modules/nazarick/frontend/accounts/](../../../../modules/nazarick/frontend/accounts/README.md). 모듈 명세의 `shared_settings`와 화면 등록의 `settingsPage`를 공통 로더가 자동 취합합니다. Shell은 등록 항목을 넓은 중앙 설정창에 표시하며 등록 항목이 없으면 아이콘을 제거합니다. 여섯 분류의 이름·순서는 모듈 명세에서 관리하고 API 키는 별도 탭에서 보관합니다.

## 사용·확인

상단 공용 설정 → 계정·서비스에서 사용할 브라우저 선택 → 저장된 로그인이 없을 때 Google/GitHub 로그인 → 에이전트 공용 연결 설정. `로그인 저장됨`이면 같은 프로필을 그대로 사용하며 `계정 열기`는 계정 관리 페이지를 엽니다. 설정으로 돌아오거나 새로고침하면 저장 상태를 다시 확인합니다. Codex는 도구 재연결 이후, Hermes는 프로필 환경을 새로 읽는 대화부터 사용합니다. 실행 중인 대화·작업을 재시작하거나 강제 교체하지 않습니다. OpenClaw는 `platform` 브라우저 프로필을 사용합니다.

계정·서비스 → 업체 일괄 추가에서 `업체명 https://공식주소`를 줄별로 붙여넣습니다. 최대 100개, 같은 도메인은 기존 기록을 유지하며 갱신합니다. 등록된 업체는 공용 브라우저에서 열고 상태를 기록합니다. 가입/키 발급 여부는 실제 화면에서 확인한 뒤 기록해야 합니다. API 키 탭에서 업체를 선택해 키체인에 저장하고, 실행 시에만 환경변수로 전달합니다.

2026-10-24 실제 확인: 플랫폼 TypeScript·Vite 빌드·기존 8766 서버 적용, 상단 아이콘과 공용 설정 Drawer 표시, 전용 Chrome 실행·Google 로그인 화면 진입, 버튼을 통한 에이전트 설정 저장을 확인했습니다. 두 Codex용 MCP의 initialize/tools/list 연결(계정 2개·브라우저 25개 도구), 실제 Hermes 브라우저의 공용 endpoint 해석, 공식 OpenClaw config validate 성공·공용 스킬 eligible/modelVisible 인식, macOS 키체인의 임시 값 저장·읽기·검사 항목 정리를 확인했습니다. 검사에 모델·추론 호출은 사용하지 않았습니다.

2026-10-24 로그인 표시 수정: 기존 공용 Brave의 Google 인증 저장 상태 `saved`와 GitHub의 `missing`을 실제 프로필에서 확인했습니다. 이번 수정에서 로그인 자체를 다시 수행하거나 기존 세션을 다른 브라우저로 옮기지 않았습니다. 서버가 세션을 취소했지만 로컬 쿠키는 남아 있는 경우까지 판정하는 기능은 아닙니다.

미완료·제약: 업체 34개 목록 등록·실제 가입·실제 API 키 발급/호출은 아직 수행하지 않았습니다. 추가 인증·CAPTCHA·업체 약관 동의는 해당 시점 사용자 처리가 필요할 수 있습니다. 여러 에이전트의 업무 전체를 강제로 직렬화하는 스케줄러는 없으므로 한 가입 작업은 한 에이전트가 맡습니다. Codex/Hermes/OpenClaw가 실제 계정으로 함께 업무를 수행하는 종단 확인과 다른 OS 실행은 미확인입니다. Google 로그인 하나가 모든 업체의 동의·과금·API 키를 대신하지 않습니다.
