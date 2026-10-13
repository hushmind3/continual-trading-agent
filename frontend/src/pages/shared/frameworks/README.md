# 공통 모듈·API 화면

- FrameworkWorkspace/ModuleCatalog: 모듈 · 도구의 FinRL·프로젝트 통합 목록 및 백엔드 기능 전체의 공통 목록.
- NativeModuleRunner/FrameworkResult: 원본 공개 함수의 입력·실행·결과.
- FeatureWorkspace: 백엔드 등록 메뉴·API 조회와 공통 원본 모듈 실행.
- FrameworkProviders: 연결 설정에서 사용하는 공급원 인증 UI.

FinRL-Trading 큰 메뉴·전용 workspace·5개 action 화면을 제거했습니다. 전용 FrameworkTools 및 메뉴 등록 파일은 휴지통으로 이동했습니다. 폐기 화면의 링크·입력·스타일·오류 이동 경로도 정리했습니다. 공통 인증·가격·원본 함수 호출 의존성은 유지합니다.
