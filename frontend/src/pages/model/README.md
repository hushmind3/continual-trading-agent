# MoE·Expert 프로젝트 확장

| 항목 | 내용 |
| --- | --- |
| 담당 메뉴 | MoE·Expert 프로젝트 확장 |
| 주요 파일 | ModelWorkspace.tsx / ExpertLibraryPanel.tsx와 관련 상세 컴포넌트 |
| 역할 | Expert 구성·버전·가져오기·탐색·검사·변환·최적화·Champion 생성 |
| 기존 API operation/조회 | experts/select, champions/create, library/*, model/open-directory |

프로젝트 확장 화면입니다. 기본 알고리즘 학습은 FinRL 학습 화면으로 연결합니다.

모든 호출은 data/Operations.tsx와 단일 /api를 사용합니다. 부모 폴더 변경 시 import 경로와 shell/Shell.tsx의 메뉴 연결을 함께 갱신합니다.

MoE 알고리즘 선택은 공통 OperationsProvider를 통해 학습 화면과 공유합니다. champions/create에 algorithm·Expert 선택과 학습 종목을 전달하며 생성 결과는 선택 알고리즘의 정책·가치 구조를 표시합니다.
