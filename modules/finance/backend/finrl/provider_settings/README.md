# 공급원 설정 연결

- 핵심 파일·진입점: operations.py의 provider_environment, provider_status, save_provider.
- 사용처: management/all_backend_features, platform/framework_operations·system_operations.
- 필수 의존성: Python 환경변수와 management/connection_settings/provider_credentials의 기존 OS 인증 저장소.
- 프론트: 기존 금융 연결·설정 화면을 사용하며 별도 메뉴를 만들지 않습니다.
- 상태: import 경로 재배치 완료. 실제 공급원 인증·시세 수신 검사는 미실행입니다.

config.settings 외부 호출을 제거했습니다. 저장된 FMP/WRDS 인증과 환경변수의 설정 여부를 이 폴더에서 조회합니다. 수집 상태 조회는 ../price_data/operations.py의 collection_status입니다. 설정 여부와 실제 원격 인증·수신 성공은 구분합니다.

거래소·브로커 인증은 키움만 등록합니다. Alpaca 연결 설정·직접 매매 도구와 Kraken 수집 코드를 제거했습니다. Yahoo·FMP·WRDS 시세·데이터 공급과 기존 인증 저장값·가격 자료는 유지합니다. FinRL 원본 초기화가 Alpaca SDK를 import하므로 내부 패키지 의존성과 키움 격리 환경은 유지합니다.

2026-10-14: 공급원 저장은 모든 환경변수 이름을 먼저 확인한 뒤 보안 저장소에 씁니다. 잘못된 필드가 섞인 요청은 일부 인증값도 저장하지 않습니다. 가짜 저장소로 확인했으며 실제 인증값은 변경하지 않았습니다.
