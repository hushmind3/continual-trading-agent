# FreeLLMAPI 남은 무료 총량 화면

용도: 기존 원본 UI의 기본 화면에 남은 무료 토큰 추정 총량 하나만 표시합니다. 페이지 스크롤·차트·요청 수·사용량 목록은 기본 화면에서 제외합니다. 고급 설정과 원본 코드는 삭제하지 않고 접어 둡니다.

- `usage-overview.patch`: 원본 React의 App.tsx, FallbackPage.tsx, usage-overview.tsx 변경. 기존 Tailwind 테마와 전체 높이 레이아웃을 사용합니다.
- 데이터: 원본 `/api/fallback` 활성 모델과 `/api/fallback/token-usage`의 모델별 월 카탈로그 한도에서 로컬 사용량을 뺀 합계입니다. 고정 모델명·개수 없이 새 활성 모델도 같은 기준으로 합산합니다.
- 제한: 공급업체 계정의 실제 잔액이 아니며 미제공 한도는 합산하지 않습니다. 일일/분당 제한이나 공급업체 공유 한도로 전부 소진하지 못할 수 있으므로 실제 사용 가능한 크레딧으로 보장하지 않습니다. 화면에 추정·실제 잔액 미연동을 표시합니다.
- 설치 소유: runtime/projects/manage/projects/freellmapi/versions/version-1/source/. 기준 원본 커밋: 26484157fd15f5fb66f54d3a86f568997ea304de.
- 업데이트 후 원본에서 `git apply --check <패치 절대 경로>` 성공 시 `--check` 없이 적용하고 client에서 `VITE_BASE=/assets/projects/<설치 ID>/ npm run build`로 빌드합니다. 충돌하면 강제 적용하지 않습니다. 자동 재적용은 미구현입니다.

확인: 기존 설치의 TypeScript·Vite 빌드와 Codex 안의 실제 화면을 확인합니다. 화면 수정 검증용 모델 호출은 하지 않습니다. 실제 업체 잔액은 미확인입니다.
