# 검토 지적 5건 조치

| 항목 | 변경 | 확인 상태 |
| --- | --- | --- |
| REA 테스트 참조 | `extract.OUTPUT`, `extract._copy_directory`를 사용하도록 수정 | 테스트 소스 수정 완료 · 실행 미확인 |
| 공식 모듈 실패 귀속 | 요청의 module/callable을 저장. 대상 없는 과거 실패는 별도 표시하고 다른 모듈에 귀속하지 않음 | 로컬 API 목록 응답 확인 · 회귀 테스트 추가, 미실행 |
| 소메뉴 폴더 불일치 | 아래 네 백엔드 폴더를 프론트 이름에 맞추고 import·메뉴 등록·문서를 수정 | 서버 적용 및 API 메뉴 등록 확인 |
| 미사용 판단 | 정적 참조·서버 import·성공한 작업의 호출 기록·인증 입력 탐지를 구분. 참조 미탐지와 미실행을 삭제 근거로 단정하지 않음 | 화면 문구·정적 조사 출력 수정 완료 |
| 일회성 스크립트 | 이전 정리에서 제거됨. 현재 scripts/의 Python 파일은 설치·서버 실행·참조 조사 3개 | 추가 폐기 없음 |

## 폴더 이름

프론트·백엔드 공통 소메뉴 이름: `operation_control`, `virtual_account_orders`, `all_backend_features`, `diagnostics_logs_code_apply`.
금융 내 trading/·management/ 분류는 유지합니다. REA는 backend/rea/ 아래에 독립적으로 유지합니다.

## 실제 확인과 제한

- Vite 프론트 빌드 완료. 기존 서버 실행 스크립트로 적용했으며 자동 검사 옵션은 생략했습니다.
- `/api`의 framework·menu_catalog 조회가 오류 없이 응답했습니다. 귀속 불명 과거 실패 1건을 별도로 반환합니다.
- 당시 FinRL-X `trading.alpaca_manager` 원본 1개에 UTF-8 해석 오류가 있었습니다. 이후 FinRL-X 제거 작업으로 해당 원본은 실행 경로에서 제거됐습니다. 현재 상태는 finrl_x_removal.md를 읽습니다.
- unittest·타입·브라우저 검사·시세 수집·학습·추론·주문은 실행하지 않았습니다. 모델·가격·계좌·인증·로컬 설정은 변경하지 않았습니다.
- 정적 조사 결과는 실행 증거가 아니며 동적 import가 있는 모듈을 자동 삭제하지 않습니다.

## 사용자 실행 검사

프로젝트 루트 PowerShell에서 실행합니다. 아래 명령은 에이전트가 실행하지 않았습니다.

```powershell
$env:PYTHONPATH = 'backend;development/tests'
$env:PYTHONUTF8 = '1'
& .\.venv\Scripts\python.exe -B -m unittest test_state_integrity.REAProjectStorageTests test_state_integrity.FrameworkFailureAttributionTests
& .\.venv\Scripts\python.exe -B development/scripts/audit_module_usage.py
```
