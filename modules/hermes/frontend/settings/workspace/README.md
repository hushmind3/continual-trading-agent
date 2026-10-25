# 작업 환경 소메뉴

작업 폴더·에이전트 사용 도구·최대 실행 한도를 설정합니다. 원본 모델이나 실행기를 복사하지 않습니다.

WorkspaceSettings.tsx는 ../useAgentSettings.ts로 현재 설정을 읽고, 단일 /api의 ai_agent/Hermes/settings에 workspace·toolsets·max_iterations를 저장합니다. toolsets의 기준은 공식 config.yaml의 platform_toolsets.cli이며 주 대화와 공식 프로필 도구 설정이 같은 값을 사용합니다. 예전 네 종류 도구 목록을 별도 기본값으로 유지하지 않습니다. 모델·키·시스템 프롬프트를 덮어쓰지 않습니다. 실행 중에는 저장을 막고 이유를 표시합니다. 읽기 모드는 채팅 입력창에서 요청마다 선택하며 작업 환경 저장과 분리합니다.

공통 ui/SettingsSection·SettingsLoadState·Primitives를 사용하고 tailwind.css에서 스타일을 공유합니다. 소메뉴 주소와 등록은 상위 ai_agent/agent_navigation.ts와 submenu_manager.ts에서 취합합니다.

도구 목록은 settings의 toolset_options(원본 Hermes registry 등록 결과)를 사용합니다. 한글 라벨은 번역이며 도구 종류를 고정하지 않습니다. 웹 검색도 여기서 선택할 수 있으며 웹 검색·기억·예약·브라우저·설치된 플러그인은 공식 도구 해석기와 제공자 구성을 따릅니다. 외부 인증·설치가 필요한 도구는 별도로 준비해야 합니다. 임시로 등록되지 않은 기존 선택은 저장 시 버리지 않습니다.

검사: frontend/tests/hermes-workspace.local-browser.spec.ts의 작업 환경 필드 저장 검사. 설정 API는 픽스처를 사용하며 실제 사용자 권한·설정을 바꾸지 않습니다.
