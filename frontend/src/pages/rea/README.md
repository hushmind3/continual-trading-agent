# REA 분석·진단 화면

REAWorkspace.tsx는 REA 설치 버전·지원 Node·원본 MCP 도구 목록을 보여줍니다. 입력 스키마와 JSON을 확인하고 사용자가 실행을 요청합니다.

단일 API의 rea 상태 조회, rea/run, rea/doctor, rea/stop을 사용합니다. 원본 도구의 isError와 진단 결과를 그대로 표시하며 미지원 플랫폼·미설정 분석 엔진을 성공으로 표시하지 않습니다. MCP 대상/Evidence 문맥은 같은 서버의 다음 호출에도 유지됩니다.
