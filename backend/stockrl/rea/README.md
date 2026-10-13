# REA 전용 연결

원본: https://github.com/morluto/rea. 공식 npm rea-agents 6.4.0과 같은 원본 MCP Client 2.3.1을 package-lock으로 고정합니다. 원본 구현은 수정하지 않습니다.

- package.json/package-lock.json: 이 폴더에 독립적으로 설치하는 Node 의존성.
- bridge.mjs: 공식 CLI의 --mcp와 공식 Client/stdio를 연결합니다.
- operations.py: 기존 단일 API에 상태·원본 도구 호출·진단·중지를 제공합니다.
- rea_menu_manager.py/rea_tools_menu.py: REA 큰 메뉴와 분석·진단 화면 등록.

Node는 ^22.19.0, ^24.11.0 또는 >=26.0.0이 필요합니다. STOCKRL_REA_NODE로 지정하거나 기존 설치 중 지원 버전을 사용합니다. 설치.cmd는 공식 npm ci를 이 폴더에서 실행하며 다른 Python·프론트 의존성을 REA 버전에 맞춰 바꾸지 않습니다.

MCP 세션은 같은 서버 안에서 유지되어 대상·Evidence 문맥을 다음 호출에서 재사용합니다. 분석 중지는 원본 자식 프로세스와 세션을 닫으며 서버 종료 때도 정리합니다. 호출은 shell 없이 JSON/stdio로 전달합니다. 휴지통은 입력·출력으로 사용하지 않습니다.

원본 170개 도구의 JSON 스키마와 결과를 전달합니다. 설치·등록은 모든 플랫폼의 분석 성공을 의미하지 않습니다. 현재 Windows에서 JavaScript 디렉터리 분석을 실행 확인했습니다. inspect_binary_layout의 pwntools 프로필은 원본이 Linux x64 전용 오류를 반환했으며 대체 구현하지 않았습니다. 심층 분석용 Ghidra/Hopper 등은 미설정이며 원본 doctor의 부족 항목을 표시합니다. Codex 등 다른 에이전트 설정을 setup으로 자동 변경하지 않습니다.

REA는 Codex 종속 프로젝트가 아닙니다. 공식 CLI도 지원하며 현재 React/FastAPI 연결은 독립 Node 자식 프로세스의 MCP/stdio를 사용합니다. Codex MCP 설정이나 로그인 없이 실행합니다. 로컬 CLI 진입점은 `node_modules/rea-agents/scripts/rea.mjs`이며 지원 Node로 `--help`를 실행하면 원본 명령을 확인할 수 있습니다.

엔진 경로 저장 API rea/settings는 GHIDRA_INSTALL_DIR/JAVA_HOME/HOPPER_LAUNCHER_PATH만 configs/local/rea.json에 저장하며 원본 MCP 및 엔진별 doctor 환경에 전달합니다. 전역 환경·Codex 설정은 변경하지 않습니다. 분석 중 저장은 거부하며 저장 후 소유 세션을 닫습니다. 엔진 설치 파일은 사용자가 별도로 설치·지정합니다.
