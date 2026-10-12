# 진단·로그·적용

| 항목 | 내용 |
| --- | --- |
| 담당 메뉴 | 진단·로그·적용 |
| 주요 파일 | Diagnostics.tsx |
| 역할 | 작업·적용 단계·프로세스·로그·버전·전체 상태 |
| 기존 API operation/조회 | system/apply; logs 조회 |

프론트와 백엔드 적용을 구분하고 실제 결과만 완료로 표시합니다.

모든 호출은 data/Operations.tsx와 단일 /api를 사용합니다. 부모 폴더 변경 시 import 경로와 shell/Shell.tsx의 메뉴 연결을 함께 갱신합니다.
