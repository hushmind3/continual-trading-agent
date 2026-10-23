# 플랫폼 프론트엔드

용도: React/Vite/Tailwind 호스트의 소스 위치·공통 UI·빌드와 검사 연결을 안내합니다.

| 담당 | 구현·문서 |
| --- | --- |
| 전체 메뉴·레이아웃 | [src/shell/](src/shell/README.md) |
| API·공통 상태 | [src/data/](src/data/README.md) |
| 화면 소유 경로 안내 | [src/pages/](src/pages/README.md) |
| 버튼·입력·패널·공통 디자인 | [src/ui/](src/ui/README.md), [tailwind.css](src/tailwind.css) |
| 금융 화면 | [modules/finance/frontend/](../modules/finance/frontend/README.md) |
| REA 화면 | [modules/rea/frontend/](../modules/rea/frontend/README.md) |
| Hermes 화면 | [modules/hermes/frontend/](../modules/hermes/frontend/README.md) |
| 원본 Hermes·OpenClaw | [Hermes 원본](../modules/hermes_original/README.md) · [OpenClaw 원본](../modules/openclaw_original/README.md) |
| 오버로드 / 나자릭 | [modules/nazarick/frontend/](../modules/nazarick/frontend/README.md) |
| 프로젝트 설치·앱 화면 | [modules/projects/](../modules/projects/README.md) |

업무 화면은 각 모듈이 소유하며 호스트의 자동 등록기를 통해 연결합니다. 모듈이 없으면 그 모듈을 강제 import하지 않습니다. `@platform`은 `frontend/src` 별칭입니다. 모든 화면은 기존 `src/ui/` 공통 컴포넌트와 `src/tailwind.css`의 디자인 값을 사용합니다. 모듈별 임의 CSS나 별도 프론트 서버를 추가하지 않습니다. 업무 호출은 기존 단일 `/api`를 사용합니다.

공통 테마는 Pretendard Variable 한글 폰트(소스 자산과 OFL 라이선스 포함)·밝은 중성 배경·초록/청록 강조색을 사용합니다. 모델/추론 선택 등 관련 필드는 공통 반응형 설정 그리드를 재사용합니다. 메뉴 계층·업무 API를 시각 스타일과 분리해 유지합니다.

## 실행·확인

운영: 루트 `서버켜기.cmd` → http://127.0.0.1:8766/ . 루트 package-lock.json과 node_modules는 플랫폼 frontend workspace의 설치 위치이며 REA/Hermes의 Node 실행 패키지는 각 모듈 내부에 있습니다.

- 설치: 루트에서 `npm ci`.
- 개발: `npm run dev --workspace frontend` → 5173; API는 8766으로 전달.
- 빌드: `npm run build --workspace frontend`.
- 타입: `npm run typecheck --workspace frontend`.
- API·브라우저 검사: `npm run test:api --workspace frontend`, `npm run test:browser --workspace frontend`.

검사는 사용자 지시에 따라 실행하며 빌드·서버 적용·화면 표시·실제 업무 실행을 구분합니다. `dist/`는 빌드 산출물입니다. 현재 모듈 분리 확인은 [모듈 안내](../modules/README.md), Hermes UI의 최근 확인은 [대화 안내](../modules/hermes/frontend/chat/README.md), 모델 추론 실측은 [모델 안내](../modules/hermes/backend/models/README.md)를 따릅니다. 특정 UI 검사의 통과를 전체 금융·REA 업무 실행 완료로 확대하지 않습니다. 기본 모듈 독립 소스 내보내기는 공통 UI 소스 복사본을 포함하며 다른 플랫폼 폴더를 참조하지 않습니다. 현재 단독 실행 확인 범위는 프로젝트 관리 README를 따릅니다.
