# 프레임워크별 공통 도구 화면

| 항목 | 내용 |
| --- | --- |
| 담당 메뉴 | 프레임워크별 공통 도구 화면 |
| 주요 파일 | FrameworkWorkspace.tsx / FrameworkTools.tsx / NativeModuleRunner.tsx / FrameworkResult.tsx / FrameworkProviders.tsx |
| 역할 | 모듈 목록·공식 작업·원본 함수·결과·공급원 양식 |
| 기존 API operation/조회 | framework 조회; framework/<action>, framework/native_call, framework/providers/* |

재사용 화면이며 FinRL, FinRL-X, stockrl scope를 구분합니다. 메뉴 구역에 따라 다른 목록을 표시합니다.

모든 호출은 data/Operations.tsx와 단일 /api를 사용합니다. 부모 폴더 변경 시 import 경로와 shell/Shell.tsx의 메뉴 연결을 함께 갱신합니다.
