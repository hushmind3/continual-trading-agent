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

## Windows native 경로

Ghidra·JDK는 담당 `runtime/rea/program_analysis/engines/`에 설치하고 `modules/rea/configs/rea.json`의 `GHIDRA_INSTALL_DIR`·`JAVA_HOME`으로 연결합니다. `operations.runtime_environment()`는 REA 자식 프로세스에만 System32 탐색 경로와 Java 표준 출력·오류의 UTF-8 기본값을 전달합니다. 한글 프로젝트 경로가 Ghidra 배치 실행기의 JDK 탐색 과정에서 깨지는 문제를 막으며 기존 명시적 Java 인코딩 옵션은 유지합니다. OS 전역 환경이나 원본 Ghidra 소스는 수정하지 않습니다.

REA 6.4.0의 직접 Java 검사는 Java 옵션을 비운 뒤 출력을 UTF-8로 해석합니다. Windows 한글 경로가 손상되면 정상 JDK도 runtime-only로 오판하므로 `bridge.mjs`가 해당 버전의 `GhidraInstallation.js` 검사 명령에 stdout/stderr UTF-8 실행 인수만 추가합니다. 실제 Ghidra 배치 실행은 내부 `for /f` 경로 판독에 필요한 Windows 기본 코드 페이지와 원본 환경 정리를 유지합니다. 버전·대상 구문이 다르면 파일을 변경하지 않고 실패를 표시하며, 패키지를 다시 설치해도 MCP 시작 시 같은 패치를 적용합니다.

2026-10-25 Windows 확인: 공식 배포의 SHA-256 확인 후 Ghidra 12.1.4·Temurin JDK 21.0.12.1을 준비했습니다. 기존 inputs의 실제 javac.exe를 원본 MCP로 열어 함수 목록·batch_decompile·닫기까지 수행했습니다. 발견 126개 중 본문 함수 74개는 74개 모두 추출됐고, EXTERNAL 주소의 외부 참조 52개는 본문이 없으므로 실패에 섞지 않고 근거 JSON과 결과 메타데이터에 따로 보존합니다. 단일 /api의 rea/analyze에서도 실제 분석·저장을 완료했고, 기존 프로젝트 탐색 화면에 함수 74개·복원 74개·복원 불가 0개가 표시되며 브라우저 오류가 없음을 확인했습니다. 원본 실행파일은 변경하지 않습니다.

## macOS native 경로
용도: 기존 REA 분석기의 실행 환경 호환성입니다. operations.node_runtime은 Mac에서 Windows AppData를 탐색하지 않고, 설치는 공통 platform_native.npm_command로 실제 Homebrew npm JS를 실행합니다. extract._web은 같은 도구의 native Chrome/Edge 실행 파일을 headless CDP로 사용합니다. extract.pick은 Mac에서 기본 osascript 파일/폴더 선택창을 사용하고 취소(-128)·분석 잠금·중지 처리를 유지합니다. 새 서버·분석 엔진·DB는 없습니다.

2026-10-22 실제 확인: 기존 REA 환경에서 Node v26.7.0·npm 11.19.0·기존 저장 기록 조회를 확인했습니다. Mac Chrome을 실제 실행해 CDP 준비와 기존 8766 플랫폼 URL의 대상 등록을 확인했고 프로세스·임시 프로필은 정리했습니다. 첫 dump-dom 종료 대기는 시간 초과되어 중단했으며, REA가 실제 사용하는 CDP 경로로 확인을 전환했습니다. 전체 웹/바이너리 분석·로그인 페이지·파일 선택 대화상자 조작은 실행하지 않았습니다.
