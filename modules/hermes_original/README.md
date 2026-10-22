# 헤르메스 원본

용도: NousResearch/hermes-agent 전체 체크아웃과 공식 실행 환경을 AI 에이전트 → 헤르메스 원본 → 원본 화면에서 엽니다.

- 원본: `runtime/ai_agent/HermesOriginal/source/`. CLI·TUI·gateway·web·desktop·plugins·skills·문서 등 전체 Git 추적 파일을 유지합니다. 사용자 요청에 따라 웹 UI 문구에만 한국어 패치를 적용하며 엔진·도구·대화 실행은 변경하지 않습니다.
- 원본 PM의 기본 설치(`python -m pm.cli install`)가 실행 도구와 `all` Python 환경을 관리합니다. 기존 이식본의 환경·프롬프트·회사 어댑터를 사용하지 않습니다.
- 원본 설정·대화·로그인·기억·스킬: `runtime/ai_agent/HermesOriginal/home/`; PM 도구: 같은 소메뉴의 `tools/`. 기존 `runtime/ai_agent/Hermes/`는 변경하지 않습니다.
- `backend/launch.py`: 공식 PM 환경을 읽어 원본 `hermes`를 exec합니다. CLI 사용은 `python3 modules/hermes_original/backend/launch.py <원본 인수>`입니다.
- `backend/runtime.py`: 원본 dashboard의 시작·상태·명시적 중지만 담당합니다. 최초 OS 할당 loopback 포트를 다음 실행에도 재사용하여 원본 localStorage의 언어·테마 설정을 유지하고, ready 파일을 사용하며 PID와 실제 명령·시작 시각을 대조합니다.
- `backend/manager.py`: 기존 모듈 자동 등록/단일 `/api`의 `ai_agent/HermesOriginal/{status,start,stop}`. 엔진·모델·도구 실행 API를 재작성하지 않습니다.
- 원본 화면은 공통 `ui-app-workspace` 레이아웃으로 큰 페이지 제목·바깥 여백 없이 남은 화면을 채웁니다. 실행 상태·새 창·중지 버튼은 공통 Shell의 `workspace-header-slot`에 React portal로 표시하며 별도 제목·제어 줄을 만들지 않습니다. 다른 기능의 오류 알림은 상단 알림 버튼에서 확인하며 원본 위에 별도 줄로 표시하지 않습니다. 원본 내부 레이아웃은 유지하며 문구만 아래 한국어 패치로 보완합니다.
- `frontend/{register.ts,Original.tsx}`: 공통 React/Vite/Tailwind·플랫폼 버튼을 사용하는 메뉴/실행 제어와 원본 iframe. 내부 UI·HTTP·WebSocket·인증·설정·업데이트는 원본 dashboard가 소유합니다. 원본 네이티브 통신을 플랫폼 JSON API로 축소 변환하지 않습니다.

원본 자체의 FastAPI dashboard listener는 loopback에만 바인드합니다. 플랫폼 기능 API를 별도 서버로 복제하는 것이 아니라 원본 프로그램을 그대로 실행하는 연결입니다. 원본 페이지는 iframe/새 창 모두 같은 원본 주소를 사용합니다. 플랫폼 재시작으로 원본 작업을 종료하지 않습니다.

한국어는 원본 언어 선택의 `한국어`로 저장합니다. 기본 언어도 한국어입니다. `korean-ui.patch`는 누락된 번역 114개, 메뉴·모델 설정 설명·추론 수준·채팅 연결 안내를 보완합니다. 명령어·모델 ID·제공자 이름과 원문 진단은 번역하지 않습니다. 플러그인 자체 문구·외부 문서·고급 설정의 서버 스키마 설명은 아직 영어가 남을 수 있습니다.

패치 기준은 공식 원본 `484de065a821b4245697351d08327b465ffd41ba`입니다. `backend/launch.py`가 dashboard 시작 시 적용 여부를 확인하고 미적용일 때만 적용합니다. 원본 업데이트 후 충돌하면 파일을 덮어쓰지 않고 오류를 표시하므로 새 버전에 맞춰 패치를 갱신해야 합니다. 원본 공식 웹 빌드로 반영하며 엔진 재설치나 모델 호출은 필요하지 않습니다.

확인 방법: 메뉴에서 원본 실행 → 원본 화면/설정/CLI 도움말을 확인합니다. 별도 모델·메신저·결제 등의 계정이나 키가 필요한 기능은 원본 설정에서 연결해야 합니다. 설치와 전체 외부 연동 검증은 구분합니다. 2026-10-23 확인: 공식 원본 484de065a821b4245697351d08327b465ffd41ba 전체 20,720개 추적 파일 설치, PM 기본 all 환경·기본 브라우저/컴퓨터 도구 설치 성공. 원본 CLI 도움말 실행·공식 웹 빌드·dashboard HTTP 200 확인. 모델 추론·외부 메신저/계정 연동과 Desktop 앱 바이너리 설치는 이번 확인에 포함하지 않습니다. Desktop 소스는 전체 체크아웃에 포함됩니다.

2026-10-23 한국어 패치 확인: 원본 공식 웹 타입 검사·빌드 성공. 실제 원본 모델 화면에서 메뉴·모델 설정·토큰 비용 설명·보조 작업 12개 이름과 설명의 한국어 표시를 확인했습니다. 원본 checkout에서 저장 패치의 역적용 검사로 재실행 시 중복 적용되지 않는 조건도 확인했습니다. 모델 추론은 실행하지 않았습니다.
