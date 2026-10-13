# 루트·모듈 정리

- scripts/·tests/·docs/는 development/ 아래로 통합했습니다. 서버켜기.cmd·설치.cmd·설치 명세·CI·적용 스크립트의 경로를 함께 수정했습니다.
- .venv-kiwoom/은 .venv/kiwoom/으로 이동하고 Python 실행·활성화·콘솔 진입점·키움 worker 경로를 수정했습니다. 라이브러리 버전은 바꾸지 않았습니다. 주 환경과 키움 SDK는 각각 websockets<11 및 websockets>=15.0.1을 요구하므로 동일한 Python 패키지 공간으로 합치지 않았습니다.
- 운영 참조·현재 적재·실행 기록·남길 모듈의 의존성이 없는 FinRL 소스 44개를 휴지통으로 옮겼습니다. 해당 바이트코드와 완료된 일회성 스크립트 8개를 포함해 96개 파일을 이동했습니다. 상세 경로는 local_cleanup_report.json에 있습니다.
- 원본 패키지 버전은 FinRL 0.3.8이며, 필요한 원본을 다시 설치할 때는 프로젝트 루트에서 `.venv\Scripts\python.exe -m pip install --force-reinstall --no-deps "git+https://github.com/AI4Finance-Foundation/FinRL.git@00f3596facd01cced5217d875d8c1fc413a31665"`를 사용합니다. 고정된 동일 원본 커밋을 사용합니다.
- 모듈·도구에는 사용 메뉴·의존 메뉴와 이 파일을 불러오는 소스 파일을 표시합니다. 실행 함수가 없는 초기화·상수 파일은 독립 실행 도구가 아니므로 목록을 늘리지 않고 각 모듈의 의존성으로 보여 줍니다. 오류 항목은 그대로 표시합니다.
- data/finrl_trading.db는 376,966행의 실제 저장 가격을 보유합니다. finrl_trading/price_data/operations.py가 학습·운영용 가격을 읽고 market_storage.AppendOnlyMarketCSV가 완료 가격을 저장하므로 유지했습니다. 가격·모델·계좌·인증·설정 값은 변경하지 않았습니다.
- .git/은 저장소 이력, .github/은 GitHub가 루트에서 찾는 CI 설정입니다. 서로 합치면 저장소·자동화가 깨지므로 표준 위치를 유지했습니다. configs/·data/·runtime/은 현재 실행의 설정·원본 데이터·모델 및 작업 상태 경로입니다.

확인: 이전·이후 프로젝트 구현 파일의 정적 import 조사에서 미참조 후보·소스 해석 오류는 없었습니다. 실제 거래·시세 수신·학습·추론·외부 인증 및 브라우저·타입 검사는 실행하지 않습니다. 빌드·서버 적용 결과는 최종 작업 보고와 구분합니다.

실제 적용 확인: Vite 빌드 성공(7.52초), 서버 적용 완료, 실제 API framework 목록 233→189개·조회 오류 없음·전체 module_errors 비어 있음. 삭제 계획 96개 파일이 원래 위치에 남아 있지 않고 scripts/·tests/·docs/·.venv-kiwoom/·빈 src/ 루트 폴더가 제거된 것을 확인했습니다. 키움 Python 새 경로 실행·콘솔 진입점 9개 재생성 완료. 가격 DB 크기 84,537,344바이트 유지. 상세 응답은 root_cleanup_verification.json에 있습니다.
