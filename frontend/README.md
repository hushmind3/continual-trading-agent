# 프론트엔드

React 화면과 기능별 메뉴를 관리합니다. 백엔드가 등록한 기능은 기존 단일 /api로 호출합니다.

## 구조

| 역할 | 문서 |
| --- | --- |
| 전체 메뉴·공통 레이아웃·오류 표시 | [src/shell/README.md](src/shell/README.md) |
| API·공통 상태 | [src/data/README.md](src/data/README.md) |
| 대메뉴·소메뉴 화면 | [src/pages/README.md](src/pages/README.md) |
| 버튼·패널·표·상세 창·디자인 | [src/ui/README.md](src/ui/README.md) |

금융과 REA는 독립 대메뉴입니다. 소메뉴 화면 → 소메뉴 매니저 → 대메뉴 → 전체 메뉴 매니저의 등록 구조를 유지합니다. 기본 화면은 금융 7개·REA 2개이며 백엔드 등록 추가 기능은 같은 메뉴 체계에 연결합니다. 메뉴 주소와 소메뉴 폴더는 영문 이름을 사용합니다.

## 실행

운영: 루트 서버켜기.cmd → http://127.0.0.1:8766/

npm workspace: package-lock.json과 node_modules는 프로젝트 루트에서 공유합니다. 이 폴더의 package.json은 React/Vite workspace 선언입니다.

- 설치: 루트에서 npm ci
- 개발: npm run dev --workspace frontend → http://127.0.0.1:5173/ (API는 8766으로 전달)
- 운영 빌드: npm run build --workspace frontend
- 타입 검사: npm run typecheck --workspace frontend
- API 검사: npm run test:api --workspace frontend
- 브라우저 검사: npm run test:browser --workspace frontend

검사는 사용자의 별도 실행 지시에 따릅니다. 빌드 생성·서버 적용·화면 렌더링·기능 검사는 서로 다른 확인 단계입니다. dist는 운영 빌드 산출물이며 소스가 아닙니다.

## 공통 디자인

Workspace.css가 배경·타이포그래피·메뉴·카드·버튼·입력·상태·상세 창·반응형 화면을 관리합니다. 밝은 중성색과 한 가지 실행 강조색을 사용하고, 기본 화면은 핵심 동작과 실제 상태를 보여줍니다. 상세 기능은 펼쳐서 접근하며 기존 기능·API·데이터·모델 설정을 디자인 변경으로 삭제하지 않습니다.

현재 공통 레이아웃·운영 화면·MoE 라이브러리 디자인을 구현하고 Vite 운영 빌드와 프론트 적용을 완료했습니다. 이번 디자인 변경의 브라우저·타입·기능 검사는 실행하지 않았습니다. 전체 소메뉴의 개별 화면 재설계와 시각 확인은 진행 중입니다.
