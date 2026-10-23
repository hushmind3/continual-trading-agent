# 나자릭 화면

용도: 오버로드 대메뉴 안의 나자릭 중메뉴와 세 소메뉴를 표시합니다.

- `register.ts`: `overlord/nazarick/{overview,connections,activity}` 등록. 세 화면은 같은 mountKey로 상태를 공유합니다.
- `Nazarick.tsx`: 조회·갱신·메뉴 이동·변경 요청. 기존 `@platform/data/api`의 단일 `/api`를 사용합니다.
- `FoundationMap.tsx`: 본체와 여섯 확장 영역. 공급자와 연결 상태를 가정하지 않습니다.
- `ConnectionForm.tsx`, `Connections.tsx`: 대상 저장·수정·제거·등록 확인.
- `Activity.tsx`, `types.ts`: 실제 결과 표시와 입력/응답 타입.
- 스타일: 공통 `frontend/src/tailwind.css`의 테마와 Tailwind 유틸리티. 공통 Panel·Button·Drawer·Input·Select·Tabs를 재사용합니다.

API·데이터·실제 확인 범위는 [백엔드 안내](../../../backend/overlord/nazarick/README.md)를 따릅니다. 실행: 기존 8766 서버 → 오버로드 → 나자릭. 타입 검사: `npm run typecheck --workspace frontend`.
