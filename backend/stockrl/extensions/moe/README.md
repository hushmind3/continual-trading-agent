# MoE

- 역할: menu.py: 메뉴 등록; handlers.py: 기존 API 처리. 
- 핵심 파일: handlers.py, menu.py
- 상위 연결: ../submenu_manager.py → finance_menu_manager.py → 전체 menu_registry → 단일 /api.
- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.
- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.

소속 대메뉴：금융. 이 폴더는 금융 내부 기능 분류이며 독립 대메뉴로 등록하지 않습니다. 하위 기능 → 분류 submenu_manager → 금융 submenu_manager → finance_menu_manager → 전체 menu_registry → /api.

프론트 메뉴 주소: `#finance/moe`; 화면: `frontend/src/pages/finance/extensions/moe/Moe.tsx`. 백엔드 실행 모듈·API 작업명은 유지합니다.

Expert 조회의 기준 폴더는 operations_settings.settings().model_dir(바탕화면 모델/experts)입니다. Champion 모델 폴더와 구분합니다. 화면 조회에서 PT 내용 읽기·가중치/정밀도 자동 검사는 수행하지 않습니다. 등록 JSON과 경로·파일 메타데이터만 표시하며, 미확인 정밀도는 실행 실패로 단정하지 않습니다. 모델 파일 목록도 같은 Expert 기준으로 등록 여부를 판별합니다.

등록 설정은 프로젝트 configs/에 저장하지 않습니다. 모델/experts/expert_registry.json은 모델별 expert.json 경로와 선택 정보를 취합하고, 각 모델 폴더의 expert.json이 해당 모델의 등록·설정·기존 검사/변환 기록을 관리합니다. 조회·선택·등록·변환·Champion 취합은 expert_registry.read_catalog/write_catalog를 사용합니다. JSON 이동·경로 연결은 확인했으며 PT 읽기·추론 검사는 실행하지 않았습니다.

검색은 Hugging Face/GitHub 공개 정보와 README를 읽으며, 검색 중 로컬 PT 템플릿을 열지 않습니다. 원본 다운로드는 실행기 확인 여부와 분리합니다. 다운로드 후 모델 폴더에 원본·download.json을 저장하고 expert.json 및 Registry에 자동 등록합니다. 조립·활성화·학습은 자동 수행하지 않습니다. 원본 저장소와 실행 가능한 Expert를 구분합니다.

전체 실행 검사는 성공한 변경 없는 모델을 기본 제외합니다. 성공 기록의 버전·입력·정밀도 서명과 파일 메타데이터를 사용하고, 결과는 해당 모델 expert.json에 저장합니다. ORIGINAL.pt 생성 단계가 없습니다. 기존 결과/이미 낮은 비트 원본은 재변환·재비교하지 않습니다. 2비트 변환은 현재 지원 대상이 아닙니다.
