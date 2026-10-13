# 프레임워크별 공통 도구 화면

| 항목 | 내용 |
| --- | --- |
| 담당 메뉴 | 프레임워크별 공통 도구 화면 |
| 주요 파일 | FrameworkWorkspace.tsx / FrameworkTools.tsx / NativeModuleRunner.tsx / FrameworkResult.tsx / FrameworkProviders.tsx |
| 역할 | 모듈 목록·공식 작업·원본 함수·결과·공급원 양식 |
| 기존 API operation/조회 | framework 조회; framework/<action>, framework/native_call, framework/providers/* |

재사용 화면이며 FinRL, FinRL-X, stockrl scope를 구분합니다. 메뉴 구역에 따라 다른 목록을 표시합니다.

모든 호출은 data/Operations.tsx와 단일 /api를 사용합니다. 부모 폴더 변경 시 import 경로와 shell/Shell.tsx의 메뉴 연결을 함께 갱신합니다.

## 전체 기능 확인·실행

- FeatureWorkspace.tsx: 큰 메뉴별 기존 화면·추가 작업·전체 API·입력 계약 탐색 및 실제 호출.
- NativeParameterFields.tsx: 원본 함수·생성자의 필수·선택 입력값 전체 표시.
- 추가 기능 메뉴는 백엔드 등록 정보를 사용하고 실행은 기존 FrameworkTools를 재사용합니다.
- GET 조회와 POST 실행을 구분하며 같은 /api 전송기를 사용합니다.
- 원본 JSON·클래스 연결·CLI 입력은 고급 설정으로 유지합니다.

큰 메뉴·작은 메뉴로 API를 필터링하며 원본 함수는 FinRL/FinRL-Trading 실행 화면으로 연결합니다. 프로젝트 모듈은 등록된 API 화면으로 이동하며 실행할 수 없는 공식 함수 선택기를 표시하지 않습니다. 동적 framework 작업도 실제 등록된 action별 API·입력 필드로 조회합니다. 공개 입력 객체의 추가 필드는 추가 입력 JSON으로 전달합니다.

FMP 재무/뉴스·지수 목록·CSV 처리·ML 데이터·신호/전략/성과의 13개 추가 화면은 개별 파일이 아닌 FeatureWorkspace/FrameworkTools의 동적 등록으로 제공되던 기능입니다. 백엔드 action 제거에 따라 화면을 폐기했고 전용 재무 CSV·예측 기간·예측 방식·비중 방식 입력 및 비어 있는 전략·성과 구역도 제거했습니다. 공유 파일은 남은 원형 실행·공급원·원본 API 화면에서 사용합니다.
