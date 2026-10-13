# REA 백엔드

- operations.py: 공식 REA 세션·환경·Ghidra 읽기 전용 디컴파일.
- projects.py: 파일·폴더·웹 입력, 원문 추출, 실제 프로젝트 폴더 저장·탐색·열기.
- artifacts.mjs: 설치된 공식 @electron/asar로 ASAR 파일 원문 추출.
- bridge.mjs: 원본 REA MCP 연결. 코딩 에이전트가 아닙니다.

저장 위치: ../../rea_projects/<프로젝트 ID>/, Git 제외. original은 관측·추출 파일, inferred는 의사코드·추론, analysis는 구조·함수·모듈·출처·한계입니다. 프로그램마다 README와 project.json을 저장합니다. original에는 네이티브 바이너리 자체가 있을 수 있으며 이는 원본 소스코드를 뜻하지 않습니다.

프론트: frontend/src/pages/rea/REAWorkspace.tsx. 단일 /api의 rea/pick·rea/analyze·rea/stop·rea/projects·rea/project/tree,file,open을 사용합니다. 기존 임의 도구 실행·JSON·진단·설정 UI와 전용 공개 경로는 제거했습니다.

파일 선택은 실제 로컬 선택창, 폴더 선택은 선택 디렉터리의 정적 소스 사본, 웹은 별도 브라우저에서 전달된 프론트 자료를 관측합니다. 로그인·사용자 동작·코딩 에이전트 호출·프로그램 재구현·추출 프로그램 실행을 수행하지 않습니다. 서버 내부 코드 및 관측하지 못한 데이터는 복원했다고 표시하지 않습니다.

Ghidra 12.1.4/JDK 21은 기존 연결을 사용합니다. Windows 네이티브 분석은 원본 지원 대상에 한합니다. 작업 프로세스는 CPU 두 코어·낮은 우선순위를 사용하며 Chrome GPU를 임의 비활성화하지 않습니다.
