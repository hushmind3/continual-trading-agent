# 나자릭 등록·화면

용도: 오버로드 → 나자릭 중메뉴의 자동 등록과 React 화면을 소유합니다.

- 실제 백엔드: [backend/overlord/nazarick/](../../backend/overlord/nazarick/README.md). 소메뉴 → 나자릭 중메뉴 매니저 → 오버로드 대메뉴 매니저 → 전체 메뉴 총괄 → 단일 `/api`.
- `module.json`: 대메뉴 `overlord`, backend namespace `platform_plugins.nazarick`, 단일 자동 등록 정보입니다.
- `backend/manager.py`: 오버로드 대메뉴 매니저만 import하는 등록 연결입니다. 업무 코드를 여기에 중복하지 않습니다.
- [frontend/](frontend/README.md): 실제 화면·공통 UI 연결입니다.
- 데이터: `runtime/overlord/nazarick/`. 등록 폴더를 제거해도 데이터는 자동 삭제하지 않습니다.

백엔드는 기존 `backend/overlord/` 소속이므로 이 등록 폴더만 복사한 독립 배포를 지원한다고 표시하지 않습니다. 실행·실제 확인·미완료 사항은 실제 백엔드 README를 따릅니다.
