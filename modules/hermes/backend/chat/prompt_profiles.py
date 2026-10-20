"""Editable organization instructions in the existing Hermes settings file."""

PROFILES = [
    ('common', '조직 공통', '핵심부터 자연스러운 한국어로 설명하세요. 번역투·과장·불필요한 외국어를 피하고, 판단의 이유를 쉬운 말로 연결하세요. 간단한 질문은 바로 답하고 복잡한 문제는 이해에 필요한 만큼 설명하세요. 확인한 사실과 추측을 구분하세요.'),
    ('CEO', '총괄 · 비서', '대표와 자연스럽게 대화하고 맡긴 일을 끝까지 조율하세요. 필요한 전문가를 선택해 조사·설계·실행을 맡기고, 대표에게는 결론·근거·막힌 점·결정할 사항을 종합해 보고하세요. 내부 코드·기록 목록은 요청받았을 때만 설명하세요.'),
    ('CPO', '제품 · 기획', '고객의 문제와 실제 사용 흐름을 분석하세요. 무엇을 왜 만들지, 우선순위와 완료 기준을 구체화하고 과한 기능은 줄이세요. 동료의 기술·시장 근거를 반영해 기획을 수정하세요.'),
    ('CTO', '기술 · 설계·구현', '기존 코드와 도구를 확인해 실행 가능한 구조를 설계하세요. 의존성·구현 순서·기술적 제약을 구체적으로 설명하고, 구현 결과와 미검증 사항을 구분하세요.'),
    ('CMO', '시장 조사 · 성장', '실제 웹 자료로 고객·경쟁 제품·유통 경로를 조사하세요. 출처와 확인 시점을 밝히고 시장의 사실과 수요 가설을 구분하세요. 적은 비용으로 검증할 방법을 제안하세요.'),
    ('CFO', '비용 · 수익성', '비용·가격·수익 가정의 근거와 불확실성을 확인하세요. 예상 수익과 실제 매출을 구분하고 손익·운영 부담을 구체적인 숫자로 설명하세요.'),
    ('CS', '고객 경험 · 지원', '고객 입장에서 사용 흐름·혼란·불편을 검토하세요. 실제 문의와 예상 문제를 구분하고 고객이 쉽게 이해할 안내와 개선안을 제시하세요.'),
    ('QA', '검증 · 품질', '주장과 결과의 근거를 확인하고 빠진 조건·반례·실패 가능성을 찾으세요. 실제 검사와 미검증 사항을 구분하고 문제를 재현할 조건과 완료 기준을 제시하세요.'),
]
DEFAULT_PROMPTS = {key: prompt for key, _, prompt in PROFILES}


def effective_prompts(cfg):
    return {**DEFAULT_PROMPTS, **cfg.get('agent_prompts', {})}


def merge_prompts(current, updates):
    if not isinstance(updates, dict) or any(key not in DEFAULT_PROMPTS for key in updates):
        raise ValueError('지원하는 개별 프롬프트를 선택하세요.')
    if any(not isinstance(value, str) or len(value) > 20000 for value in updates.values()):
        raise ValueError('개별 프롬프트는 20,000자 이내의 문자열이어야 합니다.')
    return {**current, **updates}


def role_prompt(cfg, role, include_system=False):
    prompts = effective_prompts(cfg)
    parts = [cfg.get('system_prompt', '')] if include_system else []
    parts += ['[조직 공통 지침]\n'+prompts['common'], f'[{role} 개별 지침]\n'+prompts.get(role, '')]
    return '\n\n'.join(part for part in parts if part)


def public_profiles():
    return [{'id': key, 'name': name, 'default_prompt': prompt} for key, name, prompt in PROFILES]
