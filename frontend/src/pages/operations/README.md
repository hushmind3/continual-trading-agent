# 운영 제어

| 항목 | 내용 |
| --- | --- |
| 담당 메뉴 | 운영 제어 |
| 주요 파일 | OperationsBoard.tsx |
| 역할 | 자동 운영·개별 서비스·자원·오류 |
| 기존 API operation/조회 | system/start, system/stop, controls/feed, controls/paper, controls/engine, controls/learning |

모델 선택·로드는 학습의 저장 모델 영역에서 담당합니다.

모든 호출은 data/Operations.tsx와 단일 /api를 사용합니다. 부모 폴더 변경 시 import 경로와 shell/Shell.tsx의 메뉴 연결을 함께 갱신합니다.
