# 프로그램 분석

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: artifacts.mjs, bridge.mjs, extract.py, handlers.py, menu.py, operations.py
- 상위 연결: ../submenu_manager.py → rea_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 2026-10-14 소스·웹·네이티브·패키지와 중지/다음 분석 및 브라우저 흐름 확인. 모델 생성·학습은 실행하지 않습니다.

operations.py는 설치된 원본 REA CLI/MCP·Ghidra와 연결하며 extract.py는 원문 추출·분석 저장만 수행합니다. bridge.mjs·artifacts.mjs도 이 폴더에 있습니다. 코딩 에이전트·재구현·추출 프로그램 실행은 자동 호출하지 않습니다.

2026-10-14: REA는 저장 폴더 생성 실패 뒤에도 분석 잠금을 해제합니다. 프로젝트 루트 휴지통은 폴더 추출에서 제외합니다. 임시 JavaScript 폴더의 원문 저장·구조 생성 및 실제 로컬 웹사이트의 HTML/스크립트 추출을 확인했습니다. 실제 바이너리 디컴파일·로그인 사이트는 미확인입니다.

2026-10-14: 손상된 ZIP/APK/IPA는 HTTP 400으로 거부합니다. 텍스트·문서·설정 파일은 원문을 보관하며 디컴파일러로 보내지 않습니다. 경로 존재·파일/폴더 구분은 프로젝트 생성 전에 확인합니다. 압축파일의 JS/HTML은 기존 REA 구조 분석기를 연결합니다. rea/status는 실제 작업 단계·대상·저장 결과를 전달하며 native-open/functions/decompile/save 단계를 구분합니다.

파일·폴더 선택도 분석과 같은 작업 잠금 및 중지 경로로 관리합니다. 취소는 선택 프로세스를 종료하고 빈 경로로 응답합니다. 서버 종료 시 남은 선택·분석 프로세스를 정리합니다. 실제 프론트 취소 요청 및 즉시 재선택을 확인했습니다. 입력 원본·코딩 에이전트는 실행하지 않았습니다.

런타임: `runtime/rea/program_analysis/`. 분석 입력·도구 실행·임시 자료를 보관하며 최종 저장 프로젝트는 project_explorer 소메뉴의 런타임을 공유합니다.
