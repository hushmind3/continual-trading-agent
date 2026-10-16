"""Preserve upstream execution policy and settle its review before releasing ownership."""
from __future__ import annotations


def request_policy(settings: dict, request: dict) -> dict:
    """A chat's explicit switch overrides the legacy workspace default."""
    enabled = request.get('read_only', settings.get('read_only', False))
    if type(enabled) is not bool:
        raise ValueError('읽기 모드는 켜기/끄기로 선택하세요.')
    return {**settings, 'read_only': enabled}


def context_window(native: dict, model: str) -> int:
    section = native.get('model') or {}
    if isinstance(section, str):
        return 0
    configured = section.get('context_length')
    if configured is not None:
        try:
            configured = int(configured)
            if configured <= 0:
                raise ValueError
        except (TypeError, ValueError) as error:
            raise ValueError('원본 model.context_length는 양의 정수여야 합니다.') from error
    default = section.get('default')
    if isinstance(default, dict):
        from hermes_cli.config import split_model_config_default
        default, _ = split_model_config_default(default)
    # A pin for another model must not be carried to the selected GGUF.
    if default and default != model:
        return 0
    return configured or 0


def bind_model(native: dict, model: str, base_url: str, context: int) -> dict:
    section = native.get('model') or {}
    config = {**native, 'model': dict(section) if isinstance(section, dict) else {}}
    config['model'].update(default=model, provider='custom', base_url=base_url)
    if context:
        config['model']['context_length'] = context
    else:
        config['model'].pop('context_length', None)
    return config


def settle_review(worker) -> None:
    """Keep stop/restart/model ownership until the original review acknowledges exit."""
    agent = worker.agent
    announced = cancelled = False
    while (review := getattr(agent, '_background_review_run', None)) is not None:
        if not announced:
            with worker.lock:
                worker.job['phase'] = 'reviewing'
            worker.event('status', ['작업 후 기억·스킬 검토 중'])
            announced = True
        if worker.stopping and not cancelled:
            from agent.background_review import cancel_background_review_for_live_turn
            cancel_background_review_for_live_turn(agent, message='Platform user stopped the review', tool_reason='stopped')
            cancelled = True
        review.request_done.wait(timeout=0.2)
