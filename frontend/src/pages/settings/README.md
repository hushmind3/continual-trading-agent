# 연결·설정

| 항목 | 내용 |
| --- | --- |
| 담당 메뉴 | 연결·설정 |
| 주요 파일 | ConnectionSettings.tsx |
| 역할 | 인증·공급원·기존 운영 설정·설정 출처 |
| 기존 API operation/조회 | provider/connect, provider/test, provider/public, provider/disconnect, settings |

인증 값은 백엔드 보안 저장소를 사용하며 문서·소스에 기록하지 않습니다.

모든 호출은 data/Operations.tsx와 단일 /api를 사용합니다. 부모 폴더 변경 시 import 경로와 shell/Shell.tsx의 메뉴 연결을 함께 갱신합니다.
