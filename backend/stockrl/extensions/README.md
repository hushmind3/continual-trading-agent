# 프로젝트 확장

## 메뉴 연결 파일

extensions_menu_manager.py가 이 구역의 작은 메뉴만 import합니다.

| 화면 | 연결 파일 | 프론트 담당 파일 |
| --- | --- | --- |
| MoE | moe_menu.py | pages/model/ModelWorkspace.tsx |

MoE는 algorithms 조회의 공식 목록을 사용하고 champions/create에 선택 algorithm을 전달합니다. 같은 선택값과 생성된 Champion의 알고리즘은 학습 화면에서 이어집니다.
| 프로젝트 모듈 | project_modules_menu.py | pages/frameworks/FrameworkWorkspace.tsx |
