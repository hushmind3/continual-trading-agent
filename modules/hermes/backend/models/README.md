# 모델 연결

`handlers.py`가 모델 설정·로컬 목록·불러오기·내리기를 기존 API에 등록합니다. 실제 처리는 `../engine/worker.py`가 담당합니다.

- 로컬 목록: 바탕화면 `모델/` 아래 GGUF. 원본 파일을 복사하거나 변환하지 않습니다.
- 실행기: 프로젝트 `runtime/shared/engines/llama.cpp/llama-server.exe`.
- 문맥은 플랫폼의 해당 모델별 실행 설정을 우선하고, 없으면 원본 config.yaml의 해당 model.context_length를 따릅니다. 미지정 시 llama.cpp의 모델 기본 문맥(--ctx-size 0)을 사용하며 고정 65,536을 강제하지 않습니다. 선택한 모델·주소·명시 문맥은 원본 설정에도 일치시킵니다. 동시 슬롯 1개·GPU 레이어 우선·CPU 보조 스레드 2개는 실행기 자원 설정입니다.
- 연결 준비 전 또는 모델을 내린 뒤에는 대화를 시작하지 않고 불러오기를 안내합니다.
- AIAgent의 출력 한도·reasoning에는 어댑터 고정값을 전달하지 않습니다. 원본 엔진의 기본 정책과 모델·서버의 지원에 따릅니다.
- 외부 실행기를 사용하려면 OpenAI 호환 주소·모델을 저장합니다. 키는 로컬 설정에 저장하며 응답에 반환하지 않습니다.

2026-10-16: Qwen3.5-0.8B GGUF를 실제로 불러와 RTX 3070의 Vulkan 백엔드에서 파일 도구 호출·파일 생성·한국어 응답을 확인했습니다. 이 결과가 모든 모델의 도구 사용 능력을 보증하지는 않습니다.

## Ornith 실제 추론 측정 (2026-10-16)

사용자 허용으로 진행 중인 헤르메스 작업을 중지하고 서버를 적용한 뒤, 바탕화면 모델 폴더의 `Ornith-1.5-9B.Q4_K_M.gguf`를 llama.cpp로 다시 불러왔습니다. 모델 원본을 수정하거나 복사하지 않았습니다.

65,536 문맥·동시 슬롯 1개·GPU 레이어 999·CPU 보조 스레드 2개·Flash Attention·Q8 KV 캐시 조건에서 반복 코드/일반 설명의 합성 입력을 사용했습니다. 각 요청은 출력 128토큰, temperature 0, seed 42, EOS 무시, 프롬프트 캐시 비활성으로 고정했습니다. 측정은 긴 실제 대화나 도구 실행 전체의 속도를 뜻하지 않습니다.

| 설정 | 반복 코드 생성 | 일반 설명 생성 |
| --- | ---: | ---: |
| 기존 설정 | 65.30 tok/s | 64.83 tok/s |
| ngram-simple 비교 | 65.86 tok/s | 66.03 tok/s |
| 기존 설정 복구 후 | 66.07 tok/s | 66.04 tok/s |

비교 옵션의 출력은 기존 설정과 동일했지만, 기존 설정 재측정도 같은 수준이어서 유의미한 속도 개선은 확인하지 못했습니다. 비교 옵션을 기본값에 추가하지 않았으며 원래 설정으로 모델 준비 완료를 확인했습니다. 자동 작업은 재개하지 않았습니다. 원시 측정·실행 로그는 Git 제외 경로 `runtime/ai_agent/Hermes/verification/`에 저장합니다.


## 생성 속도·새 대화 문맥 조사 — 2026-10-18

용도: 메모리 적재와 원본 추론 정책·자동 문맥을 분리해 확인한 결과입니다. 영구 설정이나 기능 축소를 적용한 작업은 아닙니다.

동일한 Ornith 파일, GPU 자동 적재, Q8 KV, Flash Attention, CPU 보조 스레드 2개에서 22토큰 입력·64토큰 생성(temperature 0, seed 42, EOS 무시, 프롬프트 캐시 비활성)을 비교했습니다. Hermes와 채팅 템플릿을 거치지 않는 직접 생성입니다.

| 문맥 한도 | 최종 GPU 적재 | 생성 속도 | 주요 메모리 |
| --- | --- | --- | --- |
| 262,144 | 17/33층 | 10.99 tok/s | CPU 모델 2,553.89 MiB, CPU/GPU KV 각각 2,176 MiB, GPU 계산 버퍼 1,138 MiB |
| 65,536 | 33/33층 | 66.08 tok/s | GPU KV 1,088 MiB, GPU 계산 버퍼 168.29 MiB |

확인된 생성 병목은 큰 문맥 공간을 확보하면서 메모리 자동 맞춤이 모델의 많은 층을 CPU에 배치한 것입니다. 새 대화의 입력이 작아도 로딩 시 정한 적재 배치는 유지됩니다. 검사 전 현재 실행기를 직접 호출해도 11.40 tok/s·CPU 약 두 코어를 사용했습니다. 실사용 엔진 로그 6.35 tok/s와 화면 6.6 tok/s도 일치하는 편입니다. 66.08은 짧은 직접 생성의 측정이며 실제 긴 에이전트 작업 속도를 보장하지 않습니다.

원래 설정을 복사한 임시 원본 worker의 실제 HTTP 요청을 가짜 응답 서버에서 캡처한 뒤, 실행 중인 Ornith의 apply-template/tokenize로 토큰을 셌습니다. 토큰 수를 문자 수로 추정한 것이 아닙니다.

| 요청 구성 | 전체 입력 토큰 | 추가량 |
| --- | ---: | ---: |
| 짧은 사용자 입력·채팅 형식 | 15 | 15 |
| 시스템 지침 포함 | 5,250 | 5,235 |
| 도구 설명 포함 | 13,338 | 8,088 |

시스템 메시지는 19,049자, 도구 23개의 JSON 설명은 32,613자였습니다. 새 대화도 원본 시스템 지침·프로젝트 문맥·스킬 안내·도구 스키마를 포함합니다. CPU 실행이 입력 토큰 수를 늘리는 것은 아닙니다. 캡처는 새 임시 홈의 짧은 입력이며 실제 화면의 대화 기록과 정확히 같은 요청은 아닙니다.

어댑터 worker.py의 tools.tool_search.defer 기본값 []는 원본의 선별 지연 로딩 목록을 덮어씁니다. 원본 tools/tool_search.py와 hermes_cli/config_defaults.py의 의미를 확인하고, 임시 환경에서만 원본 목록으로 비교한 결과 11,763토큰이었습니다(약 1,575토큰 절약). 이것만으로 13,000토큰 전부를 제거할 수는 없습니다. 도구 기능을 삭제한 비교가 아니라 tool_search/tool_describe/tool_call을 통한 지연 제공입니다. 영구 defer 설정은 변경하지 않았습니다.

Thinking 제어층은 원본 agent/reasoning_params.py·reasoning_effort.py에 있습니다. 현재 설정의 요청 캡처에는 thinking·reasoning·reasoning_effort·enable_thinking·출력 상한 강제값이 없었습니다. 하지만 Ornith의 apply-template은 기본적으로 열린 <think>로 끝나며 chat_template_kwargs.enable_thinking=false를 보냈을 때만 빈 thinking 구간을 닫았습니다. 따라서 현재는 모델 템플릿의 기본 thinking 경로를 따릅니다. Thinking을 끄는 영구 변경은 하지 않았습니다. Thinking 템플릿을 쓰지 않는 직접 생성도 느렸으므로 확인된 주병목과 구분합니다.

단순 대화 캡처는 모델 요청 1회였습니다. 작업 후 검토는 추가 비용이 될 수 있지만 이번 직접 생성 병목의 원인은 아닙니다. auxiliary.goal_judge에 과거 주소가 남았지만 일반 대화는 이 경로를 사용하지 않고 goal/loop 진입 시 현재 연결로 갱신하는 코드도 확인했습니다.

재현 소스: verification/probe_generation.py(현재 모델 직접 생성), capture_policy.py(임시 홈·가짜 응답으로 요청 캡처 및 실제 tokenizer 측정, --native-deferral로 원본 지연 로딩 비교), profile_allocation.py(현재 모델을 잠시 내리고 두 조건 검사 후 원래 연결 복원). 모두 프로젝트 루트에서 실행합니다. 정책 캡처는 modules/hermes/.venv/Scripts/python.exe, 나머지는 .venv/platform/Scripts/python.exe를 사용합니다. 모델 작업 중에는 실행하지 않습니다. profile_allocation.py는 모델 연결을 잠시 중단합니다.

원시 JSON·할당 로그는 Git 제외 runtime/ai_agent/Hermes/verification/performance/에 있습니다. 검사 후 원래 262,144 문맥의 모델 준비 완료를 확인했고 임시 포트만 재할당됐습니다. 사용자 대화 기록·모델 원본·영구 문맥/추론 정책은 변경하지 않았습니다. 속도 복구나 설정 UI 추가를 완료했다는 뜻은 아닙니다.


## 설정 복구·사용자 제어 적용 — 2026-10-18

용도: 위 조사에서 확인한 병목을 수정하고 실제 실행을 재확인한 현재 구현입니다.

- runtime_policy.py가 모델별 context_length·thinking_mode(auto/on/off)를 검증·보존합니다. settings API로 저장하며 다른 모델에 해당 값이 전파되지 않습니다. 로컬 로더는 선택 모델의 문맥을 사용하고 원본 config.yaml과 일치시킵니다. 0은 모델 기본값입니다.
- 어댑터가 강제로 넣던 defer: []를 제거했습니다. tool_loading은 native(원본 기본값)·lazy(필요한 설명 검색)·eager(처음부터 모두 제공)를 지원합니다. lazy는 원본 registry와 tool_search/tool_describe/tool_call을 사용하며 사용 가능한 도구를 삭제하지 않습니다. 읽기 모드는 기존 허용 목록의 두 읽기 도구를 직접 제공하고 원본 권한 차단을 유지합니다.
- 모델 화면의 ModelRuntimeControls.tsx에서 문맥·Thinking·도구 설명 전달 방식을 바꾸고 저장·적용합니다. 문맥/Thinking은 현재 모델별, 도구 전달은 작업 환경 공통 설정입니다. 실행 중 변경은 기존 idle 보호로 거절합니다. 로컬 모델이 적재 중이면 저장 후 다시 불러오며, 모델 변경 없이 도구 전달만 바꾸는 API 저장도 가능합니다.
- Thinking은 로컬 서버의 chat_template_kwargs.enable_thinking에 원본 request_overrides로 연결하며 기존 다른 요청값을 보존합니다. auto는 덮어쓰지 않습니다. 외부 제공자의 thinking 설정을 이 로컬 전용 필드로 강제하지 않습니다.

적용 당시 이 PC의 Ornith에 65,536 문맥·Thinking auto·도구 전달 lazy를 저장했습니다. 이후 사용자가 화면에서 변경할 수 있습니다. 직접 생성 59.77 tok/s, 실제 플랫폼 채팅 60.5 tok/s, 실제 파일 작업 60.7 tok/s를 확인했습니다. 새 작업 요청을 실제 tokenizer로 다시 센 값은 사용자/형식 15토큰 → 시스템 포함 3,411토큰 → 도구 포함 4,549토큰입니다. 모델에 처음 제공하는 도구 스키마는 검색·설명·호출의 3개이며 나머지는 검색 가능합니다. 원본 지침·스킬 기능을 강제로 끄지 않았습니다.

실제 파일 작업은 알 수 없는 임의 문자열이 든 input.txt를 도구 검색 후 읽고 copied.txt로 저장했습니다. 첫 저장에 행 번호를 잘못 포함했지만 모델이 추가 명령으로 스스로 수정했고 최종 파일 내용이 원본과 일치했습니다. 채팅 13.2초/출력 353토큰, 파일 작업 71.2초/5회 요청/출력 3,795토큰이었습니다. 생성 속도 개선과 전체 작업 시간은 구분합니다. Thinking 자동 모드의 길이·작업 판단 품질까지 개선했다고 주장하지 않습니다.

확인 자료: runtime/ai_agent/Hermes/verification/performance/agent-after-fix.json, direct-generation.json, hermes-request-policy.json. verification/verify_agent_runtime.py는 생성한 검사 대화를 보관 처리하고 임시 파일을 정리합니다. 사용자 대화·원본 모델·금융 작업은 변경하지 않았습니다. 모델별 옵션·thinking 요청 병합·도구 제공·권한/재시작·원본 엔진 회귀 26개와 TypeScript·Vite 빌드가 통과했습니다. 브라우저 확인 결과는 프론트 모델 README에 기록합니다.

마지막 추가 단문 검사는 사용자 작업이 실행 중이어서 중단 전송 없이 보류했습니다. 위 채팅/파일 실측은 앞서 완료한 독립 검사 결과이며 현재 사용자의 작업 결과를 가져다 쓴 것이 아닙니다.
