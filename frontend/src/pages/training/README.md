# FinRL 정책 학습·저장 모델

| 항목 | 내용 |
| --- | --- |
| 담당 메뉴 | FinRL 정책 학습·저장 모델 |
| 주요 파일 | TrainingWorkspace.tsx / SacControls.tsx / CheckpointPanel.tsx / PolicyArchitecture.tsx |
| 역할 | 알고리즘·종목·검사·학습·모델 로드·다운로드·Replay 상세 |
| 기존 API operation/조회 | preflight/train, train, checkpoints/restore; algorithms / champions 조회 |

백엔드 메인은 stockrl.finrl.framework입니다. 실제 모델 적재와 학습 상태를 별도로 표시합니다.

모든 호출은 data/Operations.tsx와 단일 /api를 사용합니다. 부모 폴더 변경 시 import 경로와 shell/Shell.tsx의 메뉴 연결을 함께 갱신합니다.
