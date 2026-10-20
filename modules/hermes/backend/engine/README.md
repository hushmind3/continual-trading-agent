# Engine

`upstream/` contains copied upstream implementation, not a replacement agent loop. `provenance.json` records origins and bootstrap changes. `worker.py` calls upstream AIAgent, SessionDB, tool registry, MCP and skills in an isolated process. `bridge.py` provides JSON-line IPC to the existing FastAPI process; no additional public gateway is started.

settings의 도구 선택지는 원본 registry의 등록된 범주와 toolsets 메타데이터에서 취합하며 클라이언트 전용·세션 제한 도구를 제외합니다. 기존 저장 선택은 일시적으로 플러그인이 빠져도 유지합니다. 프론트에 고정된 기능 목록으로 웹 검색이 누락되던 경계를 제거했습니다.
runtime_policy.configure_tools의 일반 lazy 설정은 선택한 web·컴퓨터 도구를 직접 노출하고 다른 도구는 지연 로딩합니다. 총괄은 direct_surfaces=False이며 web_search/web_extract 두 도구만 직접 노출하고 나머지는 필요할 때 검색합니다. 실행 기능은 유지하며 native/eager는 원본 기본 목록/전체 노출 동작을 유지합니다. configure_tools는 원본 설정과 비교해 도구 설정이 달라질 때만 저장합니다.

Python dependencies belong to `modules/hermes/.venv/`; runtime state belongs to `runtime/ai_agent/Hermes/`. All runtime paths resolve from this project. The original checkout must not appear on PYTHONPATH or be used as a symlink target.

중지 시 원본 agent.interrupt(hard_cancel=True)를 제어 스레드 밖에서 한 번만 호출합니다. 압축 HTTP 스트림 종료가 지연돼도 IPC 상태 조회를 막지 않으며 실제 실행 스레드가 끝나기 전에는 중지 완료로 표시하지 않습니다.

프로젝트 자동 연결은 `mcp/project` 명령을 `../mcp/project_links.py`로 전달합니다. 다른 MCP 설정을 보존하면서 프로젝트 전용 서버만 추가·해제하며, 원본 discovery와 도구 등록 결과를 확인합니다. 로컬 모델 로더는 설치된 llama.cpp의 `--n-gpu-layers auto`를 사용합니다. 기존 999 고정값이 자동 메모리 맞춤을 막아 Vulkan KV 캐시 할당에 실패한 것을 확인했으며, 문맥 크기는 사용자/원본 설정을 유지하고 GPU 계층만 가용 VRAM에 맞춥니다.

브라우저 실행기는 모듈 자체 backend/engine/browser/node_modules의 agent-browser 0.26.0이며 설치된 Chrome/Edge를 재사용합니다. 기본 native 설정에서 browser.backend=off는 browser-use CLI만 끄고 원본 agent-browser 도구를 사용한다는 뜻입니다. 채팅은 원본 interactive approval context를 사용해 프론트 허용/거절에 연결합니다. AX 캡처의 전체 텍스트를 제한 길이로 보존하는 로컬 패치는 provider-provenance.json에 기록합니다.

서버 재시작 전 기존 worker 상태만 확인하며 작업·중지 처리·모델 로딩·MCP 설치 중에는 재시작을 차단합니다. 준비 승인 시 새 요청을 차단한 뒤 상태를 재확인하고 IPC 쓰기와 직렬화해 시작/재시작 경합을 막습니다. 상태 확인 실패도 재시작 허용으로 처리하지 않습니다.
ChatGPT device-code 로그인이 진행 중인 worker도 재시작에서 보호합니다. 모델 제공자는 [모델 연결](../models/README.md)의 custom/openai-codex 선택을 따릅니다. 인증은 원본 Hermes가 관리하고 worker는 해당 제공자의 원본 전송을 사용합니다. 유지 중인 로컬 실행기의 슬롯/로그 수치를 클라우드 요청의 토큰·속도로 표시하지 않습니다.

실행 안내는 문서 결과를 로컬 Markdown 링크로 보고하도록 설명합니다. 플랫폼 HTML 미리보기는 정적 HTML·인라인 CSS를 지원하고 스크립트·외부 자원은 차단하므로, 단순 문서 열람을 위해 별도 메모장·브라우저를 실행하지 않도록 안내합니다. 이는 모델에 전달하는 지침이며 모든 모델이 이를 따랐다는 실행 검증은 아닙니다.

실행 정책: 프로젝트 지침 자동 주입·출력 한도·reasoning은 원본 AIAgent 기본값을 사용합니다. 일반 작업의 기억·스킬 검토도 원본 조건과 auxiliary.background_review 설정에 맡깁니다. 읽기 전용 작업과 명시된 focused_discussion 요청은 검토 쓰기를 막습니다. 앱의 주제 전용 맥락은 [대화 안내](../chat/README.md)를 따르며 일반 코드 작업은 원본 지침·기억을 유지합니다. execution.py는 모델별 문맥 설정 연결과 검토 종료 대기를 담당하며, 검토 중에는 worker 작업 소유권을 유지해 모델 내리기·서버 재시작이 겹치지 않게 합니다.

2026-10-16: 격리된 가짜 모델 서버를 통해 원본 지침 주입, 강제 출력 제한·reasoning 비활성화 제거, 원본 스킬 검토 종료, 읽기 전용 도구 차단을 확인했습니다. 실제 Ornith의 thinking 출력·문맥 할당·품질 비교는 실행하지 않았습니다. 설치된 llama.cpp 도움말에서도 ctx-size 0이 모델 문맥을 사용하는 값임을 확인했습니다.

2026-10-18: 실제 GPU 적재·Thinking 템플릿·기본 지침/도구 토큰 조사는 [모델 안내](../models/README.md)에 기록했습니다. 실행 설정은 변경하지 않았으며 원본 지연 로딩 목록을 덮어쓰는 defer: []도 조사 대상입니다.

현재 실행 제어: runtime_policy.py가 모델별 문맥/Thinking과 원본 도구 검색 제공 방식을 연결합니다. defer: [] 강제 생성은 제거했습니다. Thinking auto는 원본/모델 기본값을 보존합니다. 설정·실측·남은 제한은 [모델 안내](../models/README.md)의 설정 복구 항목을 봅니다.

앱 하네스의 실행별 시스템 지침·JSON 응답 계약은 [대화 안내](../chat/README.md)를 따릅니다. 사용자 모델 설정은 저장 변경하지 않으며 JSON 제약은 원본 chat_completions 전송의 request_overrides를 사용합니다.

2026-10-19 문맥 격리 보정: skip_context_files/skip_memory만으로는 원본 시스템 프롬프트의 호스트·현재 경로·코딩 맥락·플러그인 구간이 없어지지 않았습니다. focused_discussion은 실행별 프롬프트 빌더를 앱 역할+사용자 지정 지침으로 교체하고 압축 재생성에도 같은 경계를 유지합니다. 일반 native/직원 도구 실행은 변경하지 않습니다. 기존 회의/앱 대화에 저장된 잘못된 추정은 삭제하지 않으며, 과거 기록과 사용자 지정 공유 맥락의 영향은 별개입니다. 회귀는 test_project_harness의 원본 빌더 미호출·캐시 재생성·native 보존 검사로 확인합니다. 수정 후 실제 모델 답변의 주제 혼동 재발 여부는 별도 확인 대상입니다.

앱 실행은 application_request=true와 실행별 시스템 지침을 사용합니다. worker는 사용자 대화를 생성하지 않고 별도 실행 ID/빈 이력을 사용하며 원본 AIAgent의 _persist_disabled를 적용합니다. 앱 DB가 업무/대화 이력을 소유하며 Hermes 모델·API·Thinking은 기존 설정을 공유합니다. 앱 실행은 사용자 Goal/Loop나 기존 세션 ID와 섞을 수 없습니다. 백그라운드 경험 정리는 내부 요청에서 수행하지 않습니다. 일반 Hermes 대화의 저장·재개는 유지합니다.

실행 수치: worker.py는 작업 스레드 시작 직전 chat.telemetry.begin으로 소유 모델 로그의 현재 위치를 잡습니다. telemetry가 이후 decoder timing만 읽어 짧은 응답의 실제 속도를 보완합니다. 원본 agent loop/출력 한도/Thinking 설정은 변경하지 않습니다. 관련 검증은 ../chat/README.md를 따릅니다.

로컬 모델의 기존 llama-server 실행기는 --checkpoint-min-step 기본값을 1,024로 전달합니다. LLAMA_ARG_CHECKPOINT_MIN_SPACING_NT 환경변수가 있으면 그 값을 우선하며 최대 문맥·GPU 적재·Thinking·체크포인트 개수는 바꾸지 않습니다. 중간 문맥 변경 후 공통 접두부가 있어도 전체 입력이 다시 처리되던 기존 설치본에서, 변경 후 후속 대화의 신규 처리 32토큰·입력 처리 0.154초를 관측했습니다. 모델 기동 직후에는 캐시가 없으므로 첫 입력 비용은 남습니다. 옵션은 설치된 실행기 --help와 [공식 체크포인트 안내](https://github.com/ggml-org/llama.cpp/pull/15293)를 기준으로 사용합니다. 실제 응답 수치는 [대화 안내](../chat/README.md)에 모읍니다.

현재 native 실행 중 메시지는 steer_chat→AIAgent.redirect/steer로 전달하며 stop과 구분합니다. 같은 세션·현재 살아 있는 실행만 허용합니다. 원본 lifecycle의 Tool guardrail halted 이벤트를 감지하면 결과를 complete로 표시하지 않고 paused와 한국어 오류로 남깁니다. 원본의 동일 실패 반복 차단 기능은 유지합니다.

반복 생성 중단은 실패 상태를 유지하며 한국어 원인과 미완료 사실을 반환합니다. 원본 영문 오류는 generation_failure 이벤트에 보존하고 성공/회의 완료로 바꾸거나 자동 무한 재시도하지 않습니다.

실시간 team_meeting은 총괄의 직접 노출 도구입니다. 자식은 원본 위임 실행기·같은 모델·기존 SessionDB를 사용하고 일반 대화 목록에서 숨기며 회의의 실제 발언 출처로 연결합니다. meeting_id는 요청별 재검토 지침이며 다른 대화에 전역 주입하지 않습니다. finally에서 미결/실패를 기존 기록에 남깁니다.
