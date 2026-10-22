# 헤르메스 원본

용도: NousResearch/hermes-agent 전체 체크아웃과 공식 실행 환경을 AI 에이전트 → 헤르메스 원본 → 원본 화면에서 엽니다.

- 원본: `runtime/ai_agent/HermesOriginal/source/`. CLI·TUI·gateway·web·desktop·plugins·skills·문서 등 Git 추적 파일을 선별하거나 패치하지 않습니다.
- 원본 PM의 기본 설치(`python -m pm.cli install`)가 실행 도구와 `all` Python 환경을 관리합니다. 기존 이식본의 환경·프롬프트·회사 어댑터를 사용하지 않습니다.
- 원본 설정·대화·로그인·기억·스킬: `runtime/ai_agent/HermesOriginal/home/`; PM 도구: 같은 소메뉴의 `tools/`. 기존 `runtime/ai_agent/Hermes/`는 변경하지 않습니다.
- `backend/launch.py`: 공식 PM 환경을 읽어 원본 `hermes`를 exec합니다. CLI 사용은 `python3 modules/hermes_original/backend/launch.py <원본 인수>`입니다.
- `backend/runtime.py`: 원본 dashboard의 시작·상태·명시적 중지만 담당합니다. 원본의 OS 할당 loopback 포트·ready 파일을 사용하고 PID와 실제 명령·시작 시각을 대조합니다.
- `backend/manager.py`: 기존 모듈 자동 등록/단일 `/api`의 `ai_agent/HermesOriginal/{status,start,stop}`. 엔진·모델·도구 실행 API를 재작성하지 않습니다.
- 원본 화면은 공통 `ui-app-workspace` 레이아웃으로 큰 페이지 제목·바깥 여백 없이 남은 화면을 채웁니다. 다른 기능의 오류 알림은 상단 알림 버튼에서 확인하며 원본 위에 별도 줄로 표시하지 않습니다. 원본 내부 UI는 변경하지 않습니다.
- `frontend/{register.ts,Original.tsx}`: 공통 React/Vite/Tailwind·플랫폼 버튼을 사용하는 메뉴/실행 제어와 원본 iframe. 내부 UI·HTTP·WebSocket·인증·설정·업데이트는 원본 dashboard가 소유합니다. 원본 네이티브 통신을 플랫폼 JSON API로 축소 변환하지 않습니다.

원본 자체의 FastAPI dashboard listener는 loopback에만 바인드합니다. 플랫폼 기능 API를 별도 서버로 복제하는 것이 아니라 원본 프로그램을 그대로 실행하는 연결입니다. 원본 페이지는 iframe/새 창 모두 같은 원본 주소를 사용합니다. 플랫폼 재시작으로 원본 작업을 종료하지 않습니다.

확인 방법: 메뉴에서 원본 실행 → 원본 화면/설정/CLI 도움말을 확인합니다. 별도 모델·메신저·결제 등의 계정이나 키가 필요한 기능은 원본 설정에서 연결해야 합니다. 설치와 전체 외부 연동 검증은 구분합니다. 2026-10-23 확인: 공식 원본 484de065a821b4245697351d08327b465ffd41ba 전체 20,720개 추적 파일 설치, PM 기본 all 환경·기본 브라우저/컴퓨터 도구 설치 성공. 원본 CLI 도움말 실행·공식 웹 빌드·dashboard HTTP 200 확인. 모델 추론·외부 메신저/계정 연동과 Desktop 앱 바이너리 설치는 이번 확인에 포함하지 않습니다. Desktop 소스는 전체 체크아웃에 포함됩니다.
