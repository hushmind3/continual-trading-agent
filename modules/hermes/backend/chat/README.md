# Chat and autonomous execution

HTTP start/status/stop adapters call the original AIAgent in the isolated worker. Chat runs once. Goal and recurring modes use the original hermes_cli.goals.GoalManager and hermes_cli.loops.LoopManager; autonomy.py only drives these managers and forwards progress. The original auxiliary goal judge uses the selected model endpoint.

조직 회의는 대표가 총괄에게 맡기는 업무입니다. 총괄이 조사·직군 선택·토론·결론 작성을 추가 진행 지시 없이 이어가고, 기존 총괄 대화에 결론·근거·위험·승인할 사항을 짧게 보고합니다. 직원 토론은 선택적으로 관찰하며 대표 지시는 참가 발언과 구분합니다. 초안 승인·보류·수정은 기존 경로를 사용하고 승인 전 실행하지 않습니다. 일반 대화의 실행 방식은 변경하지 않습니다.

총괄은 대표의 비서·CEO라는 한국어 역할 지침으로 질문에 짧게 답하고, 명시적으로 맡긴 작업·승인에만 실행·회의·위임을 사용합니다. 역할은 공통 사용자 지침을 보존한 뒤 적용하며 호칭을 현황 요약 명령으로 혼동하지 않도록 구분합니다. 회사 overview·제품 진행·과거 기억을 매 요청에 자동 조회하거나 시스템 지침에 넣지 않습니다. 현재 질문에 회사 기록이나 이전 결정이 필요할 때만 기존 company_records·session_search로 조회합니다. 특정 한국어 인사 목록으로 분기하지 않으며 원본 도구·기억 기능은 유지합니다.
큰 총괄 문맥은 원본 ContextCompressor의 작업 예산·보호된 최근 대화·도구 묶음 경계를 재사용해 모델에 전달할 범위만 줄입니다. 원문 SessionDB의 행을 지우거나 별도 DB/요약 모델/새 에이전트 루프를 만들지 않습니다. 과거 업무 발췌·자동 요약을 새 요청 앞에 주입하지 않습니다. 시스템 지침을 재작성하지 않으며 필요한 이전 내용은 기존 조회 도구로 읽습니다. 오래된 내용은 같은 DB의 session_search 및 범위가 지정된 recall로 읽습니다. 일반 대화의 이력은 이 경로를 사용하지 않습니다. company_context 이벤트의 token 값은 추정치이며 실제 입력량·응답 시간과 구분합니다.
총괄 lazy는 검색·회의·회사 기록과 공식 memory·skills 등록 도구 전체를 직접 노출하고, 위임·파일·터미널·빌드 도구 설명은 원본 tool_describe/tool_search로 필요할 때 불러옵니다. 실행 기능은 유지하며 일반 대화와 native/eager의 직접 노출 설정은 바꾸지 않습니다. 초기 플랫폼·조직 연결 안내는 중복을 줄이고 실제 호스트에 맞춥니다. 도구 노출 설정이 바뀔 때 기존 SessionDB의 스키마 고정 목록도 원본 메서드로 갱신해 오래된 직접 도구가 복원되는 것을 막습니다. 일반 후속 대화에서는 다시 갱신하지 않아 접두부 캐시를 유지합니다. 사용자 시스템·조직 공통·직원 개별 지침, 원본 기억·스킬·SessionDB는 유지합니다. 아래 직접 도구 추가 기록은 당시 실행 관찰이며 현재 lazy의 노출 정책은 이 문단을 따릅니다.

2026-10-20 최종 실제 확인(기존 총괄·설치본·같은 모델 설정): 로컬 Ornith/Thinking on/65,536 문맥에서 모델 기동 직후 호출은 9.77초(입력 처리 5.68초), 이어 보낸 일상 대화는 1.42초·첫 표시 0.91초·모델 1회·도구 0회였습니다. 후속 요청의 실제 신규 처리 입력은 32토큰(0.154초)이었고 전체 문맥 11,480토큰과 구분합니다. 동일 메시지의 수정 전 후속 요청은 6.53초·전체 11,427토큰 재처리였습니다. 설치된 llama.cpp의 checkpoint-min-step을 1,024로 적용한 결과이며 기동 직후까지 즉답인 것은 아닙니다. 계정 카탈로그에서 조회한 GPT-6-Luna/low는 호칭 응답 2.96초·모델 1회·출력 13토큰·도구 0회, 명시적인 회사 기록 조회는 7.32초·모델 2회·실제 company_records overview 1회로 승인 프로젝트 수 1을 반환했습니다. 선택 제공자·모델은 기존 로컬/Thinking on/65K로 복구했고 모델은 ready입니다. 이는 해당 실행 관찰값이며 모든 요청의 속도나 업무 완성을 보장하지 않습니다.

프로젝트 설치기의 자동 변환 요청은 chat의 workspace 값으로 해당 내려받은 프로젝트를 작업 폴더로 지정합니다. 이 값은 해당 실행의 cfg에만 적용하고 저장된 기본 작업 환경을 바꾸지 않습니다. 모델 준비·도구 승인·중지 경로는 기존 대화 실행과 같습니다.

원본 앱의 하네스 호출은 `application_system_prompt`로 역할과 응답 규격을 전달합니다(문자열 50,000자 이하). `engine/worker.py`가 실행별 ephemeral 시스템 지침에 추가하며 저장된 사용자 시스템 프롬프트는 변경하지 않습니다. 과거 앱 대화는 참고 자료로 구분하고 현재 요청만 수행합니다. 기존 모델·thinking·도구 권한·소유자 승인 경로를 그대로 사용합니다.

`application_response_format=json_object`는 OpenAI 호환 chat_completions 전송에만 JSON 제약을 요청합니다. runtime_policy.py가 기존 request_overrides와 병합하므로 thinking 옵션을 지우지 않습니다. 다른 전송의 JSON 계약은 앱 반환 시 검증하며 지원하지 않는 형식을 임의 변환하지 않습니다.

`application_plan_only=true`인 외부 호환 계획 요청은 JSON 문법과 도구 문법의 Ollama 충돌을 피하도록 해당 요청의 도구 전송만 비웁니다. 실제 `agent_task` 실행은 이 플래그 없이 일반 도구 경로를 사용합니다. 저장된 사용자 도구 목록/권한은 변경하지 않습니다.

`application_generation`은 원본 앱의 출력 한도(max_tokens 1~65,536 정수)와 temperature(0~2 숫자)를 실행별로 전달합니다. 원본 provider의 인수를 보존하기 위한 경로이며 전역 기본 제한이 아닙니다. runtime_policy에서 검증하고 원본 agent의 해당 실행에만 적용합니다.

현재 native 총괄은 application_plan_only/application_request/focused_discussion을 사용하지 않습니다. 외부 provider 호환 경로는 다른 앱을 위해 유지합니다.

Frontend modes: one turn, work toward a goal, recurring task. /goal <task>, /goal resume, /loop <interval> <task>, /loop resume and /stop also use the same paths. Tool approval and user-question callbacks remain interactive.
모델 제공자는 모델 설정의 custom/OpenAI 호환 또는 openai-codex/ChatGPT 연결을 따릅니다. 같은 native 세션·도구·기억을 유지하며 Goal 판정도 선택 제공자로 연결합니다. 별도 Codex 실행 루프나 회사 DB를 만들지 않습니다. 연결/검증 범위는 [모델 안내](../models/README.md)를 참고합니다.
ChatGPT의 모델별 추론 수준은 원본 reasoning_config에 연결하고 Goal 판정에도 같은 값을 전달합니다. 모델 기본값 선택은 계정 카탈로그의 default_reasoning_level을 사용합니다. 원본 전송이 지원하지 않는 광고 옵션은 자동 하향 실행하지 않습니다.

Goals stop when judged done, blocked, interrupted or budget-limited. Loops stop on the native completion marker, requested count, until criterion or native backstop. Intervals are clamped to the original minimum (30 seconds by default); self-paced mode starts at 60 seconds and backs off on unchanged responses. A model can signal completion before the requested count. Zero count uses the native 100-tick backstop, rather than implying unlimited work.

Goal 첫 턴은 원본 goal_kick_prompt에 실제 이전 대화의 마지막 사용자 메시지를 넘깁니다. 아직 모델에 전달하지 않은 새 요청을 이전 메시지처럼 넘겨 긴 목표 원문이 '이미 전달됨'으로 생략되던 어댑터 오류를 수정했습니다. test_hermes_port.test_17에서 실제 첫 모델 요청의 사용자 메시지에 긴 목표 전체가 포함되는지 확인합니다.
Goal 판정의 provider/model 경로를 갱신할 때 기존 auxiliary.goal_judge 옵션을 병합해 출력/추론 등 사용자 설정을 보존합니다. 같은 로컬 모델의 압축/판정에는 현재 Thinking 선택도 전달하며 원본 auxiliary_client의 실제 HTTP 요청으로 확인합니다(test_18). 압축 기능·요약 출력 자체를 끄거나 새 압축 루프로 대체하지 않습니다.

State lives in the native session DB. Stop pauses autonomous work. After a worker restart, opening a formerly active session marks it paused and offers Resume; it does not silently restart work. The platform backend must stay running for recurring execution. This is in-session /loop, not an OS scheduler or the standalone Hermes cron gateway. Status polling alone never starts a model or task.

telemetry.py reads original agent usage counters and the owned local llama.cpp /slots endpoint, cached for at least 0.8 seconds. Generation speed is sampled from actual decoded-token deltas while the same task is processing. begin() captures the owned model log byte offset before the execution thread starts; only decoder timings written after that point supplement short responses that finish before two slot samples. Prompt evaluation throughput is never shown as generation speed; missing observations stay unknown. Status retains final counters after agent cleanup. Tool events delimit the current streamed response and phase.

The worker tells the original agent its Windows host and detected browser executable, explains that Git Bash ps/which cannot identify Windows applications reliably, and directs visible GUI launches through detached PowerShell Start-Process. It must verify once, leave the requested app open, and not relaunch after the user closes it. This is operating-context guidance, not a replacement for native tools or proof that every model obeys it.

For visible Chrome/Edge launch, desktop_browser.py adds a platform extension through the original registry and explicit computer_use toolset membership. It resolves known installed browser executables, validates http/https/about:blank, starts the executable with a shell-free detached argument list, and suppresses duplicate same-turn launches. It reports only a launch request; native computer_use accessibility capture verifies the visible window. The existing AIAgent and native desktop/browser tools remain in use. This helper is platform code, not claimed to be part of the original Hermes source.

A native failed/incomplete/budget-exhausted result becomes paused with an explicit incomplete message rather than complete. Tool-loop errors remain visible in grouped results.

읽기 전용 분석은 설정의 read_only 권한으로 켭니다. 선택 작업 폴더 안의 read_file·search_files만 실행 전 허용하며 편집·명령·코드 실행·위임·MCP·컴퓨터 도구는 차단합니다. 원본 AIAgent는 유지하고 로컬 배치 실행 경계에 권한 검사를 둡니다. 대화 DB·로그 저장은 계속하며, 이 기능은 전체 프로세스를 OS 샌드박스에 넣는 기능은 아닙니다. 각 자동 실행 턴의 failed/completed 상태를 목표 판정 전에 확인하고 미완료 시 일시정지합니다.

application_context_scope=focused_discussion은 외부 앱의 순수 사업 검토용 요청입니다. 해당 agent에만 skip_context_files/skip_memory/skip_background_review와 빈 도구 목록을 적용하고, 앱 역할·사용자 시스템 지침·Thinking·출력 옵션은 유지합니다. 기본 native 범위와 직원 실행은 그대로입니다. native 총괄은 이 호환 모드를 사용하지 않습니다.

2026-10-19 문맥 격리 보정: skip_context_files/skip_memory만으로는 원본 시스템 프롬프트의 호스트·현재 경로·코딩 맥락·플러그인 구간이 없어지지 않았습니다. focused_discussion은 실행별 프롬프트 빌더를 앱 역할+사용자 지정 지침으로 교체하고 압축 재생성에도 같은 경계를 유지합니다. 일반 native/직원 도구 실행은 변경하지 않습니다. 기존 회의/앱 대화에 저장된 잘못된 추정은 삭제하지 않으며, 과거 기록과 사용자 지정 공유 맥락의 영향은 별개입니다. 회귀는 test_project_harness의 원본 빌더 미호출·캐시 재생성·native 보존 검사로 확인합니다. 수정 후 실제 모델 답변의 주제 혼동 재발 여부는 별도 확인 대상입니다.

2026-10-20 확인: test_hermes_telemetry의 이전 작업 제외·부분 로그·prompt/decoder 구분 회귀와 원본 Hermes 경계 13개 통과. 실제 짧은 총괄 응답의 61.7/62.3 tok/s는 해당 llama.cpp decoder receipt를 사용했습니다. 모델/문맥/Thinking 설정은 변경하지 않았습니다.

company.py는 기존 SessionDB의 영구 총괄 세션과 원본 도구 registry를 연결합니다. 대화·장기 기억·컨텍스트 파일·Goal/Loop·권한/질문 처리는 일반 Hermes와 같습니다. 회사 기능은 조회·초안·역할별 기록·회의록 도구이며 별도 agent/provider/DB 대화 루프가 없습니다. 최초 과거 CEO 메시지를 native DB에 한 번 가져오고 이후 동일 세션을 재사용합니다. 기존 데이터는 삭제하지 않습니다. 세션별 내부 토큰은 모델 지침/브라우저 응답에 포함하지 않습니다.

총괄의 기본 작업 폴더는 연결된 조직의 workspaces입니다. 호출자가 workspace를 명시하면 일반 Hermes의 기존 디렉터리 검증을 거쳐 그 선택을 유지하며 기본 폴더로 덮어쓰지 않습니다. project_npm의 실행 범위는 연결된 조직 작업 폴더입니다.
프로젝트 지침은 원본 Hermes의 AGENTS.md 탐색(Git 루트→현재 작업 폴더)을 그대로 사용합니다. 총괄 전용 AGENTS.md를 따로 생성하거나 루트 파일을 바꾸지 않습니다. 같은 저장소 안에서는 React·Vite·Tailwind·공통 UI 등 프로젝트 개발 규칙을 공유하며 총괄 역할 지침으로 대체하지 않습니다. 총괄의 Git 쓰기 승인 규칙은 대표가 지정한 게시 권한에만 적용됩니다. 별도 Git 저장소에서 작업하면 해당 저장소의 지침을 읽습니다.
일반/총괄 요청 시작 시 원본 register_task_env_overrides로 해당 native task의 터미널 CWD도 갱신합니다. 같은 세션에서 이전 cd로 기록된 Temp 경로가 새 작업 폴더 선택을 덮어쓰지 않도록 합니다. 모델이 이후 명시적으로 다른 곳으로 cd하는 행동을 강제로 차단하는 기능은 아닙니다.

project_commands.py는 같은 native registry의 project_npm 도구입니다. 회사 작업 폴더 경계를 확인하고 Node/npm CLI를 인수 목록으로 직접 실행하므로 셸 인용/cd가 필요 없습니다. 실제 종료 코드·출력을 반환하고 test/build는 담당 작업 폴더 verification/에 영수증을 남깁니다. 전역 설치 플래그·임의 명령은 허용하지 않으며 별도 agent 루프가 아닙니다. 기존 terminal/file 도구는 유지합니다.
자식 npm 프로세스의 stdin은 닫아 부모 worker의 IPC 입력을 읽지 못하게 합니다. 사용자 질문·권한 승인은 기존 Hermes 대화 경로에서 처리합니다.
npm 시간 초과와 소유자 중지를 구분하며, 중지된 명령도 실제 종료 코드·부분 출력·오류를 test/build 영수증에 남깁니다. company_records의 HTTP 오류는 내부 토큰을 지운 서버 검증 사유를 반환해 잘못된 업무 ID 등을 수정할 수 있게 합니다.
모델의 성공 문장이 error 필드에 들어가 업무가 실패로 저장된 실제 오류를 방지하도록 native 도구는 finish(성공)/fail(실패)와 body만 받습니다. 모호한 error 인수는 기록 전에 거절합니다. fail은 기존 단일 API의 실패 기록으로 변환하며 원래 서버의 실제 실패 보존 계약은 유지합니다.

총괄의 일반 대화는 기본 1~3문장으로 답하고, 현재 요청에 필요하지 않은 회의·위임·현황 조회를 시작하지 않도록 지침을 축소했습니다. 기록 보존과 모델 입력을 분리해 원본 SessionDB.get_resume_conversations의 display/model 이력을 각각 사용합니다. 원본 무모델 도구 로그 정리는 compression.proactive_prune_tokens=8192, proactive_prune_min_result_chars=2000, proactive_prune_min_reclaim_tokens=1024를 누락된 설정의 기본값으로 연결합니다. 명시한 값(0 포함)이 우선이며 최대 컨텍스트·Thinking·출력 한도는 변경하지 않습니다. 최근 도구 결과와 원문 보관은 원본 compressor의 보호·archive_and_compact 규칙을 따릅니다.

실제 확인: 유휴 총괄 세션에 원본 prune_tool_results_only를 적용해 도구 결과 14개를 입력용 요약으로 정리했습니다. 모델 이력 내용은 JSON 문자 기준 113,862→79,715자(약30% 감소)였고 화면용 원본 도구 내용은 모두 보존됨을 검사했습니다. 추가 모델 호출은 0회입니다. 이는 실제 입력 토큰 수나 응답 시간 측정값이 아닙니다. 현재 짧은 대화의 실제 로컬·Luna 응답 확인은 문서 앞의 최종 측정에 정리했습니다. 모든 자연어 요청의 회의 억제를 보장하는 결과는 아닙니다.

조직 기억 조회: company_records recall과 원본 session_search로 같은 조직의 결정·제약·미완료·실패 기록을 필요할 때 조회합니다. 자동 recall_context 사전 검색은 제거했습니다. 새 기억 DB나 검색용 모델 호출을 추가하지 않습니다. 중요한 새 결정은 기존 remember 기록을 사용합니다. CEO는 결과·막힌 점·필요한 결정만 짧게 보고하며 요청 없는 Git 쓰기는 기존 사용자 승인 경로를 사용합니다.

확인: 원본 회사 ASGI/DB 및 native 연결 관련 26개 검사로 오래된 결정 조회·정정 우선·사업 범위 분리·미완료/실패 계승·새 테이블 없음·원문 보존·직접 Git 승인·활성 문맥 중복 제외를 확인합니다. 실제 서버의 기존 견적서 사업 회상도 추가 모델 호출 없이 확인했습니다. 실제 9B 응답의 길이/회의 빈도와 모든 자연어의 회상 정확도를 보장하는 검사는 아닙니다.

총괄의 판단 구분: 뉴스·현재 사실은 직접 웹 검색하고 출처/날짜를 짧게 보고합니다. 사업 아이디어·기회·전략은 근거 조사 후 관련 직원들의 짧은 검토를 종합합니다. 구체적인 제작 지시는 실행·검증하며 실제 쟁점이 있을 때만 검토합니다. 사업 논의까지 금지하는 포괄 지침은 제거했습니다.

검색 실행: 작업 환경에서 web을 선택한 일반 대화와 회사 세션 모두 원본 web 묶음에 키 없는 검색 제공자를 등록합니다. web_search.py는 원본 WebSearchProvider 레지스트리에 DDGS 어댑터만 등록합니다. 원본 옵션과 같은 ddgs==9.16.0을 Hermes 전용 환경/requirements에 고정했습니다. URL 본문은 동일 제공자의 web_extract로 직접 읽습니다. httpx와 표준 HTMLParser를 사용하며 원본 URL 검사·결과 형식·본문 길이 제어를 유지합니다. 스크립트·스타일은 제외하고 동적·인증 페이지는 브라우저 도구로 확인합니다. 별도 키·서비스·설치는 추가하지 않습니다. 선택하지 않은 다른 도구를 자동으로 켜지 않습니다.

2026-10-20 일반 Luna·low 실측: 기존 사용자 요청은 20.4초/모델 3회였으며 브라우저 이동 두 번에 약 3.8초가 걸렸습니다. 나머지를 순수 추론 시간으로 단정할 계측은 없습니다. 별도 새 검사 대화에서 web 연결 후 33.4초/5회(검색 도구 발견·설명 포함), direct surface가 lazy 목록에 다시 들어가던 오류 수정 후 23.6초/4회를 확인했습니다. 후자는 검색 2회·본문 추출 시도 1회이며 최종 원문 링크가 실제 검색 결과에 포함됐습니다. DDGS는 본문 추출을 지원하지 않으므로 추출 성공/항상 짧은 응답 시간을 보장하지 않습니다. 동일 질문 1회씩의 관측이며 성능 벤치마크로 일반화하지 않습니다. 검사 대화는 보관 처리했고 사용자 대화는 수정하지 않았습니다. 근거는 runtime/ai_agent/Hermes/verification/luna-search{,-direct}.json입니다.

현재 확인: 원본 web_search_tool의 키 없는 검색 성공(결과 2건), TypeScript 통과, 실제 브라우저의 원본 회사 화면·초안·승인 확인창 취소 시 실행 없음·확인 후 동일 세션 실행·1440/390px 넘침/JS 오류 없음을 확인했습니다. 브라우저 검사는 API 픽스처이며 실제 모델 호출은 0회입니다. CEO의 실제 뉴스/사업 대화 판단은 별도 실사용 확인 대상입니다.

자동 조회 제거 후 첫 실제 짧은 호출에서 과거 검사 지시를 재실행하는 실패를 확인했습니다. 원본 fallback 요약 경계를 사용한 후에도 요청 없는 과거 작업 보고가 남았습니다. 최종적으로 자동 과거 요약 주입도 제거하고 원본 경계로 보호한 최근 대화만 전달하며, 오래된 내용은 필요할 때 원본 DB에서 조회합니다. 최신 부름·인사에 과거 작업을 보고하지 않는 한국어 지침도 명확히 했습니다. 잘못 생성된 connection-check.html은 프로젝트 휴지통으로 옮겼습니다. 기존 DB 원문은 보존했습니다.

작업 중 추가 메시지: handlers.py의 POST chat/steer는 기존 단일 /api를 통해 worker.steer_chat에 연결합니다. 현재 작업과 session_id가 일치할 때만 원본 AIAgent.redirect를 사용합니다. 모델 응답 도중에는 해당 요청만 전환하고, 도구 실행 도중에는 원본 steer/yield 경계를 사용합니다. 준비·종료 경계에서 받지 못한 입력은 오류로 돌려 UI 초안을 유지하며 다른 대화로 보내지 않습니다. 별도 큐 DB·새 에이전트·실행 루프를 만들지 않습니다. company_records propose의 proposal은 problem/product/validation을 필수 명세로 정의하고 빈 제안은 구체적인 누락 항목과 함께 실행 전에 거절합니다.

2026-10-21 수정: 총괄의 웹 검색·본문 읽기 두 도구만 lazy 목록에서 직접 노출해 도구 검색 왕복을 줄입니다. 웹 조사는 검색/본문 추출을 우선하며 사용자가 요청하지 않은 창 실행·캡처를 하지 않도록 안내합니다. 이 변경은 모델·Thinking·저장 대화·일반 대화의 도구 노출 설정을 바꾸지 않습니다.

실제 확인(2026-10-21): 기존 Instinct 페이지 직접 추출 1.55초, 본문 492자. 같은 기존 총괄 세션·Ornith/Thinking on/65,536에서 동일 웹 확인 요청은 종전 78.1초에서 19.9초로 줄었고 API 2회·web_extract 1회·창 실행/캡처 0회였습니다. 전체 입력 9,087토큰·출력 355토큰입니다. 추출 결과는 정상이나 첫 모델 응답에는 과거 답변의 근거 없는 회사·접근 제한 정보가 섞여 원문 우선·제외 지침을 추가 보완했습니다. 모델의 사실성 전반을 보장하는 검사는 아닙니다. 새 제품·검사 파일·설치는 만들지 않았습니다.

보완 적용 후 기존 대화에서 공식 원문 기준 정정을 요청해 도구 추가 호출 없이 10.9초·모델 1회로 두 문장 응답을 확인했습니다. 앞서 섞인 회사명·초청 제한·지속 클라우드 주장은 이 정정 응답에서 제외됐습니다. 모델 첫 기동의 입력 처리 시간은 남습니다.


실시간 토론: meetings.py의 team_meeting start/speak/finish를 사용합니다. speak는 원본 tools.delegate_tool의 자식 생성·실행·SessionDB·중단·승인 전파를 재사용합니다. 각 자식에게 실제 앞선 발언과 안건·담당 관점을 주고 웹 확인을 허용하지만 구현/결제/추가 위임 도구는 주지 않습니다. 스트림은 status와 기존 ceo_meetings에 기록하고 실제 자식 세션 ID를 보존합니다. 총괄이 다음 직군과 재반론을 선택합니다. 예전 company_records meeting 요청도 실제 start로 연결하여 빈 minutes가 반복 거절되던 경로를 없앴습니다.

기존 meeting_id로 재검토하며 직전 두 사용자 턴을 원본 경계로 보호합니다. 대표 지시는 원본 steer에 전달하고 회의 발언에 투영합니다. finish는 실제 두 직군 이상 검토가 있어야 완료됩니다. proposal은 기존 ventures에 pending으로 제출하며 승인하지 않습니다. 재검토는 같은 ID를 수정하고 revising 동안 승인을 거절합니다. 미결/중단/실패는 저장 발언을 보존한 채 실패로 기록합니다. telemetry.py는 총괄과 실제 자식의 원본 사용량을 합산합니다. 새 DB/모델/하네스/고정 회의 파이프라인은 없습니다.

실제 실행 확인: 기존 조직/기존 총괄/선택된 로컬 모델로 실시간 비서 사업 첫 토론 6개 직군(132.8초), 동일 안건의 수정 토론 CPO→CTO(63.2초)를 완료했습니다. 각 자식은 원본 SessionDB에서 source=subagent 및 부모 총괄 ID가 확인됐습니다. 초안 ID를 바꾸지 않고 네 필드를 수정해 pending으로 재제출했고 실행 승인은 하지 않았습니다. 위임 일시정지/깊이 한도는 원본 guard를 그대로 확인합니다. 별도 테스트 프로젝트/검사 파일/설치본을 만들지 않았습니다.

현재 직원 체계: prompt_profiles.py의 프롬프트 원문과 platform-settings.json의 staff_registry를 사용합니다. 직원 UUID·표시 이름·전문성은 분리하며 영문 직함 enum이나 호환 ID는 실행·도구 선택에 사용하지 않습니다. manager_staff_id는 총괄 담당 직원의 고유 ID입니다. 회사 도구와 회의·실제 delegate_task는 staff_id를 사용하고 일반 메시지의 user/assistant/tool 역할은 원본 통신 규격을 유지합니다.

staff_migration.py는 시작 시 일회성으로 기존 설정 키·회사 DB 직원 열/회의 JSON·원본 SessionDB의 구조화된 도구 인수·설치된 회사 화면/조회 소스를 새 식별자로 이관합니다. 원문 자연어 기록은 삭제하지 않습니다. runtime/ai_agent/Hermes/migrations에 백업·매핑 감사 자료·테이블별 건수를 보관하며 런타임 호환 변환에는 사용하지 않습니다. 실제 도구 스키마에는 폐기된 코드 enum이 없습니다.

원본 실행 연결: 원본 에이전트의 실제 _dispatch_delegate_task 메서드를 감싸 직원별 지침을 주입합니다. 단순 registry handler만 감싸는 방식은 원본의 직접 dispatch 경로에 적용되지 않으므로 사용하지 않습니다. 자식은 원본 도구·작업 공간·출력·결과 전달·중단·승인과 SessionDB를 유지합니다. 회의는 도구 범위를 조회/검토로 좁히며 실행 직원은 원본 위임의 실제 도구를 사용합니다. 사업 승인 이후 자율 운영은 기존 LoopManager로 처리하고 별도 스케줄러를 만들지 않습니다.

실제 이관 확인: 등록 직원 7명과 기존 업무/교훈의 staff_id 연결, 이름 수정 후 같은 ID 유지, 회사 현황의 6개 직원 카드 표시를 확인했습니다. 실제 로컬 모델의 실행 위임은 자식을 생성했으나 과거 안건 혼입·반복 호출 후 실패했습니다. 이를 제품 제작 성공으로 표시하지 않습니다. 로컬 파일·기록·위임 도구는 조직 대화에서 직접 노출하고 위임 context는 현재 goal과 과거 근거를 구분하도록 보완했습니다. 보완 후 제품 제작·지속 운영은 미확인입니다.

조직 위임의 결과 전달: 플랫폼 worker에는 원본 CLI/gateway의 백그라운드 결과 재주입 소비자가 없으므로, 회사 직원 위임은 원본 delegate_task의 동기 batch를 호출합니다. 원본 자식 병렬 실행·도구·중단·깊이/일시정지 guard는 유지하며 총괄은 실제 반환 결과를 받은 뒤 보고합니다. 일반 대화의 원본 background 위임은 변경하지 않습니다.

보완 후 실제 확인: 선택된 기존 로컬 모델과 같은 총괄 SessionDB에서 새 staff_id로 기술개발 직원을 호출했습니다. 기존 설정 README의 read_file 결과가 자식→총괄로 반환됐고, 원본 결과는 completed·도구 상태 ok·2회 모델 호출·자식 실행 12.32초였습니다. 직원 지침의 이름도 반환됐습니다. 제품 빌드·외부 공개·결제·매출·무기한 운영까지 확인한 결과는 아닙니다. 로컬 모델 답변에는 여전히 어색한 표현과 내부 ID 노출이 관측됐습니다.

위임의 직접 호출과 tool_call 경유 호출 모두 현재 에이전트의 같은 직원 식별자 검증·지침 주입·원본 동기 batch로 연결합니다. 잘못된 task 자료형이나 식별자는 도구 오류로 반환하며 전체 실행을 예외로 종료하지 않습니다.

직원 지침은 staff_id로 자동 주입하므로 총괄은 위임 context에 동일 프롬프트·대화 전문·코드를 다시 생성하지 않습니다. 실제 작업/폴더/산출물/완료 조건을 전달하여 위임 시 출력 토큰과 중복 문맥을 줄입니다.

진행 이벤트는 긴 인수의 값/목록만 축약하고 유효한 JSON을 유지합니다. 문자열 중간 절단으로 도구 표시를 파싱하지 못하던 경로를 수정했으며 전체 실행 기록은 SessionDB에 보존합니다. 위임의 staff_id는 개별 task 값을 우선하고 공통 식별자는 묶음의 기본값으로 사용합니다. 선행 산출물이 필요한 검증은 결과를 받은 후 별도로 위임합니다.

실제 제품 제작에서 개발 직원이 쉘로 App.tsx 머리 부분만 반복 작성하며 진척이 없는 현상을 확인했습니다. 조직 실행의 직접 도구에 write_file·patch·search_files를 포함하여 파일 편집을 별도 탐색 없이 실행하도록 하고, 실행 명령과 파일 작성을 구분하도록 지침을 보완했습니다. 사용자 모델/Thinking/문맥 한도는 낮추지 않습니다.

실제 루나 실행에서 직원 UUID 끝 글자 누락으로 검증 위임이 반복 거절되는 것을 확인했습니다. 위임 스키마는 현재 등록부에서 동적으로 enum을 구성하고, 불일치 오류는 실제 직원 ID/이름 목록을 반환하여 즉시 올바른 값으로 고칠 수 있게 합니다. 축약 ID나 옛 직함을 호환 식별자로 수용하지 않습니다.

조직 실행에 기존 project_npm 도구도 직접 노출합니다. 실제 9B가 이를 쉘 명령으로 오인하거나 terminal의 장기 서버 판정에 vite build가 차단돼 확인을 반복한 근거가 있습니다. 기존 전용 도구로 빌드 명령·완료 코드·receipt를 반환하며 모델별 하드코딩은 추가하지 않습니다.

2026-10-21 실제 Ornith 9B 확인: 기존 EstimateAI 소스를 기술개발 직원과 총괄이 직접 수정했습니다. 첫 빌드는 JSX 오류로 실패 후 수정됐고, 첫 화면 확인에서 가져오기 결함이 남아 추가 피드백으로 normalize까지 수정했습니다. 이후 실제 화면에서 JSON의 null/boolean/빈 문자열/공백/음수/NaN 거절·기존 220,000원 견적 보존, 0 허용, CSV 220,000원·XLSX 330,000원 계산을 확인했습니다. 직접 노출한 project_npm을 9B가 호출한 최종 build는 exit_code 0·2.9초(tsc 및 Vite)였습니다. 과도한 추론·요구 누락이 관측돼 무인 자율 수행의 품질·속도가 완성됐다는 검증은 아닙니다. 공개 서비스·계정·결제 연동도 이 확인에 포함하지 않습니다.

## 대화별 실행 수치와 총괄 세션
용도: telemetry.py는 마지막 실행과 직전 비교 기준을 기존 Hermes SessionDB의 model_config._platform_runtime_metrics에 저장합니다. 원본 토큰 원장은 그대로 사용하고 별도 DB·중복 누적기를 만들지 않습니다. 완료·실패·중지·일시정지에서도 확보된 수치를 보존하며 저장 실패는 metrics_error로 표시합니다. 누적 입력은 원본 get_compression_lineage가 반환한 압축 계보 세션들의 input/cache_read/cache_write 합계입니다. 원본 update_conversation_model_config_value로 압축 후속 세션에도 마지막 수치를 이어주며 직원 자식 세션은 별도 기록으로 유지합니다.

전체 요청 입력은 원본 session_prompt_tokens이며 캐시 제외 input_tokens와 구분합니다. 원본 turn_usage의 normalize_usage 반환값을 바꾸지 않는 관찰 래퍼로 실제 캐시 필드 존재 여부를 확인해 보고된 0과 미보고를 구별합니다. 자식까지 집계가 맞는 경우에만 0을 확정합니다. 로컬에서는 해당 실행 로그의 prompt eval 토큰/완료 요청 수도 교차 확인합니다. 캐시 미보고·집계 불일치는 미확인으로 남기며 문맥 증감을 실제 신규 처리량으로 추정하지 않습니다. 문맥 비교는 같은 모델의 직전 완료 기록만 사용합니다.

company.create_conversation은 기존 조직의 도구 연결을 새 native UUID에 연결합니다. 새 대화의 이력은 비어 있으며 과거 회의·사업 기록은 기존 도구로 필요한 때 조회합니다. 원래 회사 대표 세션과 기존 대화도 보존합니다.

2026-10-21 실제 확인: 기존 설치본에서 총괄을 선택하고 새 대화를 만들어 일반 대상으로 바뀌지 않는 것을 확인했습니다. 같은 조직의 새 native 세션에서 Luna/low 실제 답변 2개를 완료했고 후속 요청은 전체 입력 10,278·캐시 10,112·새 처리 166·문맥 증감 +51·세션 누적 20,505였습니다. 일반 대화의 이전 43,477 집계도 보존됐고 새로고침·API 재시작·일반/총괄 전환 후 같은 새 총괄 세션과 수치가 복원됐습니다. 9B는 기존 실제 실행 로그의 새 입력 11,213/요청 1회/생성 20.0 tok/s 판독을 확인했으며 이번 변경 후 9B 신규 추론이나 실제 압축 발생은 실행하지 않았습니다. 스크린샷은 runtime/ai_agent/Hermes/verification/conversation-metrics.png입니다.

2026-10-21 초기 문맥 정리 실제 확인: 같은 기존 총괄 세션·Luna/low에서 저장된 도구 pin이 새 lazy 설정을 덮는 원인을 확인했습니다. 정책 지문에 따른 1회 갱신 후 직접 목록은 14개에서 7개(업무 도구 4개+원본 탐색 도구 3개), 스키마는 24,263자에서 11,079자로 줄었습니다. 대화가 더 쌓인 상태에서도 단순 응답의 실제 문맥은 10,602→8,022토큰이었고 새 접두부 캐시가 없는 실행은 6.5초였습니다. 원본 지침은 12,131자, 플랫폼·조직 안내는 3,230자로 측정했으며 문자 수를 토큰으로 환산하지 않습니다. 이어 tool_describe(read_file)→실제 read_file로 기존 루트 README 첫 줄을 읽었습니다(3회 모델 호출·17.1초, 캐시 24,320/신규 처리 1,036). 두 번째 요청에서 정책 pin을 재갱신하지 않았고 7개 목록이 유지됐습니다. 준비 중 메타데이터 갱신 함수 인수 오류는 모델 호출 전 실패했으며 원본 콜백 형식으로 수정한 뒤 위 실제 경로를 통과했습니다. 초기 입력 감소를 작업 속도 개선으로 주장하지 않습니다. 이번 변경에서 실제 압축 발생·9B 신규 추론·회의·위임·제품 빌드는 실행하지 않았으며 모델별 제한은 추가하지 않았습니다.

Mac 실행 도구: project_commands.project_npm은 platform_native.npm_command로 Homebrew npm의 실제 JS 진입점을 Node로 실행합니다. npm.cmd나 node 옆의 Windows 패키지 배치를 Mac에 가정하지 않습니다. desktop_browser도 같은 native 브라우저 탐색을 사용합니다. 설치된 npm 11.19.0의 실제 버전 명령·원본 Hermes 셸 실행을 확인했으며 제품 빌드·회의·위임은 이번 경로 수정에서 실행하지 않았습니다. 상세 결과는 ../engine/README.md를 따릅니다.

새 총괄 세션의 업무 도구 인증은 projects/backend/conversation.py가 동일 회사 연결을 기존 SessionDB로 확인합니다. company-links의 회사 토큰만 복사하고 고정 대표 세션 ID만 허용하던 서버 경계를 수정했으며, 새 대화의 기록 조회·위임·업무 소유를 기존 세션과 같은 회사 안에서 사용합니다. 일반/다른 조직 대화의 도구 권한을 넓히지 않습니다.

회의 회차: meetings.round_speeches는 현재 대표 요청의 round_start 이후 발언만 판정합니다. 동일 직원의 중복 호출은 자식 에이전트를 만들기 전에 거절합니다. 실패한 호출도 자동으로 재반복하지 않으며 다른 직원 검토 뒤 총괄이 결론을 냅니다. 기존 회의 ID·과거 발언·직원 UUID는 보존하며 새 대표 요청의 재검토만 새 회차로 시작합니다. 현재 회차의 실제 완료 리뷰어 둘 이상이라는 원본 종료 조건은 유지합니다.

## 조직 도구 실행 문맥

company.execute·recall_for_staff·register는 호출한 worker를 명시적으로 받습니다. 마지막 prepare가 설정한 프로세스 전역 _worker를 사용하지 않습니다. 회의의 기록 호출·직원 조회·실행 수명 주기·도구 등록도 같은 인수를 전달합니다. 공식 owner의 다중 세션에 조직 확장을 연결할 때 다른 조직의 실행 문맥을 잘못 참조하지 않도록 하는 전제이며, 이 변경만으로 owner 플러그인 통합이 완료된 것은 아닙니다. 기존 회사 실행 검사 13개를 실제 PM 환경에서 통과했습니다. 새 위임·회의 생성의 실제 모델 검증과 구분합니다.

서버 적용 후 실제 기존 총괄 세션에서 업무 상태별 개수 조회를 요청했습니다. 원래 선택된 모델 설정으로 모델 요청 2회·도구 시작/완료 후 complete·오류 없음·답변 62자를 확인했습니다. 이는 기존 조직 조회 경로의 실제 재확인이며 공식 owner 플러그인·다중 세션 업무·새 회의 실행 완료를 뜻하지 않습니다.

## 공식 owner의 조직 플러그인

native_plugin.py는 원본 PluginContext에 기록 조회·회의·빌드 명령·직원 위임과 프롬프트를 등록합니다. runtime/ai_agent/Hermes/plugins/platform-organization에는 native_plugin.py에서 생성한 공식 SDK 패키지만 배치합니다. 원본 로더가 실제 코드 교체를 관리하며, 기존 platform_modules.mount_namespaces로 회사·회의 소메뉴 라이브러리를 가져옵니다. 엔진·DB·직원 설정을 복제하지 않습니다. 활성화는 원본 dashboard_set_agent_plugin_enabled의 선택 버전·게이트웨이 즉시 반영 경로를 사용하고, 최초 연결 이력은 기존 state_meta에 보관해 명시적인 비활성화를 매 기동 덮어쓰지 않습니다.

실제 SDK 확인: 도구 5개 등록과 원본 게이트웨이의 plugin reload 성공, 공통 프롬프트 488자·조직 프롬프트 1,957자 렌더링을 확인했습니다. 기존 실행 검사 21개 통과. 첫 원본 owner 모델 호출은 이전 세션의 9B 모델 이름과 현재 FreeLLMAPI가 섞여 HTTP 404로 실패했습니다. 원본 GatewayAgent.switch_model로 현재 선택 모델·제공자와 일치시키는 경로를 확인했으며, 후속 실제 도구 호출 결과는 별도로 기록합니다. 기존 raw 대화의 원본 owner 전환·설정별 정책 계승·회의 스트림의 플랫폼 표시·전체 기능 검증은 아직 미완료입니다.

실제 원본 owner 확인: 첫 SDK 도구 호출은 호출 문맥 인수가 없는 경로에서 실패했습니다. 원본 bind_subagent_parent 실행 문맥으로 실제 부모를 조회하고 SDK 로더의 교체 경계 안에 어댑터를 설치한 뒤, 기존 총괄 세션에서 company_records 실제 호출·도구 오류 없음·모델 2회·정상 완료를 확인했습니다. 회사 도구의 실제 등록 모듈은 hermes_plugins.platform_organization입니다. 일반 플랫폼 호출은 기존 실제 worker를 이어받아 현재 회의·승인·상태 표시를 보존합니다. 신규 원본 위임·회의·명령 실행과 전체 owner 클라이언트 전환은 아직 미확인/미완료입니다.

SDK의 도구 집합은 기존 platform_company·platform_company_recall 소속을 유지합니다. 원본 기본 집합에 회사 도구를 섞으면 현재 플랫폼의 직접 도구 노출 및 회의 직원의 읽기 집합과 어긋나기 때문입니다. 등록된 기존 직원 ID 7개가 실제 프롬프트에 연결되고 구형 CEO 문자열을 식별자로 받지 않는 것을 확인했습니다. 원본 SDK 조회 성공 뒤 플랫폼 직접 경로의 재확인에서는 실제 조회 대신 tool_search만 수행한 결과를 발견했으며, 집합 소속을 맞춘 뒤 직접 노출된 company_records가 실제 jobs 데이터를 오류 없이 반환한 것을 확인했습니다. 모델이 도중에 deferred 도구용 tool_call을 잘못 시도해 원본 검증에서 한 번 거절됐으며, 이후 직접 호출로 정상 조회했습니다. 플랫폼 경로는 모델 3회·complete였고 효율 개선 완료로 기록하지 않습니다. 모델의 complete 표시를 실제 도구 실행 성공으로 간주하지 않습니다.
