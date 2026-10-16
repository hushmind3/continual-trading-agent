"""Prepare the configured Hermes provider without replacing an active task."""
import time


def ensure_ready(bridge, cancelled, progress, timeout=180):
    status = bridge.call('status')
    if status.get('job', {}).get('state') in ('starting', 'running', 'stopping'):
        raise ValueError('Hermes가 다른 작업을 진행 중입니다. 작업이 끝난 뒤 다시 시도하세요.')
    settings = bridge.call('settings')
    if not settings.get('local_model'):
        if not settings.get('base_url') or not settings.get('model'):
            raise ValueError('자동 변환에 사용할 모델이 지정되지 않았습니다. Hermes 모델 설정에서 선택하세요.')
        return
    state = status.get('local_model', {})
    if state.get('state') == 'ready':
        return
    progress('adapter', '설정된 로컬 모델을 GPU 실행기로 준비합니다.')
    if cancelled.is_set(): raise ValueError('설치를 취소했습니다.')
    if state.get('state') != 'loading':
        bridge.call('model/load', {'path': settings['local_model']})
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cancelled.is_set(): raise ValueError('설치를 취소했습니다.')
        state = bridge.call('status').get('local_model', {})
        if state.get('state') == 'ready': return
        if state.get('state') not in ('starting', 'loading'):
            raise ValueError(state.get('error') or '자동 변환 모델을 불러오지 못했습니다. Hermes 모델 실행 로그를 확인하세요.')
        cancelled.wait(.5)
    raise ValueError('자동 변환 모델 준비 시간이 초과됐습니다. 모델 준비 후 다시 시도하세요.')
