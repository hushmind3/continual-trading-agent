# 공급원 설정 연결

- 핵심 파일·진입점: operations.py의 provider_environment, provider_status, save_provider.
- 사용처: management/backend_browser, platform/framework_operations·system_operations.
- 필수 의존성: 상위 finrlx → 공식 config.settings; management/connection_settings/provider_credentials의 기존 인증 저장소.
- 프론트: 기존 금융 연결·설정 화면을 사용하며 별도 메뉴를 만들지 않습니다.
- 상태: import 경로 재배치 완료. 실제 공급원 인증·시세 수신 검사는 미실행입니다.
