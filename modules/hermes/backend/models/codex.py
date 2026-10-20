"""UI adapter for the original Hermes Codex OAuth provider; no second agent."""
import threading
import time


class CodexConnection:
    def __init__(self):
        self.lock = threading.RLock()
        self.login = {'state': 'idle'}
        self.catalog = None
        self.catalog_at = 0

    def status(self):
        from hermes_cli.auth import get_codex_auth_status
        auth = get_codex_auth_status()
        with self.lock:
            return {**self.login, 'connected': bool(auth.get('logged_in'))}

    def start(self):
        from hermes_cli.auth_codex import _codex_request_device_code, CODEX_OAUTH_CLIENT_ID
        with self.lock:
            if self.status()['connected']:
                self.login = {'state': 'complete'}
                return self.status()
            if self.login['state'] == 'pending':
                return self.status()
            data = _codex_request_device_code('https://auth.openai.com', CODEX_OAUTH_CLIENT_ID)
            self.login = {'state': 'pending', 'url': 'https://auth.openai.com/codex/device',
                          'code': data['user_code']}
            threading.Thread(target=self._complete, args=(data,), daemon=True).start()
            return self.status()

    def _complete(self, data):
        from hermes_cli.auth_codex import (_codex_poll_authorization_code,
            _codex_exchange_authorization_code, _save_codex_tokens, CODEX_OAUTH_CLIENT_ID)
        try:
            code = _codex_poll_authorization_code('https://auth.openai.com',
                device_auth_id=data['device_auth_id'], user_code=data['user_code'], poll_interval=data['interval'])
            tokens = _codex_exchange_authorization_code('https://auth.openai.com', CODEX_OAUTH_CLIENT_ID, code)
            # Independent grant in this module's HERMES_HOME. Never copy Codex CLI refresh tokens.
            _save_codex_tokens({k: tokens.get(k, '') for k in ('access_token', 'refresh_token')}, set_active=False)
            result = {'state': 'complete'}
        except Exception as error:
            # Exception bodies may contain provider secrets. Only a stable error code reaches the UI.
            result = {'state': 'failed', 'error': 'ChatGPT 로그인 실패: ' + str(getattr(error, 'code', 'authentication_failed'))}
        with self.lock:
            self.login = result

    def models(self):
        from hermes_cli.auth_codex import resolve_codex_runtime_credentials
        from agent.codex_headers import codex_account_headers
        from agent.model_metadata import fetch_codex_catalog_entries
        from agent.reasoning_effort import codex_supported_efforts
        from hermes_cli.codex_models import _add_context_variants
        import httpx
        creds = resolve_codex_runtime_credentials(read_only=True)
        headers = {'Authorization': 'Bearer ' + creds['api_key'], **codex_account_headers(creds['api_key'])}
        entries, status = fetch_codex_catalog_entries(
            lambda url: httpx.get(url, headers=headers, timeout=12), base_url=creds['base_url'])
        if status != 200 or not entries:
            raise ValueError('계정 모델 목록을 조회하지 못했습니다. 로그인 상태를 확인하고 다시 불러오세요.')
        models = []
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get('slug') or entry.get('visibility') in ('hide', 'hidden'):
                continue
            wire = codex_supported_efforts(entry['slug'])
            efforts = [{'value': row['effort'], 'description': row.get('description', ''),
                        'available': row['effort'] in wire}
                       for row in entry.get('supported_reasoning_levels', []) if isinstance(row, dict) and row.get('effort')]
            models.append({'id': entry['slug'], 'name': entry.get('display_name') or entry['slug'],
                           'aliases': [alias for alias in _add_context_variants([entry['slug']]) if alias != entry['slug']],
                           'reasoning_efforts': efforts, 'default_reasoning_effort': entry.get('default_reasoning_level')})
        with self.lock:
            self.catalog, self.catalog_at = models, time.monotonic()
        return {'models': models, 'catalog_live': True}

    def reasoning(self, model, selected='auto'):
        with self.lock:
            models = self.catalog if time.monotonic() - self.catalog_at < 60 else None
        if models is None:
            models = self.models()['models']
        row = next((row for row in models if row['id'] == model or model in row.get('aliases', [])), None)
        if not row:
            raise ValueError('계정 모델 목록에서 선택한 모델을 찾지 못했습니다. 모델 목록을 새로 불러오세요.')
        effort = row['default_reasoning_effort'] if selected == 'auto' else selected
        if not effort:
            return None
        choice = next((item for item in row['reasoning_efforts'] if item['value'] == effort), None)
        if not choice or not choice['available']:
            raise ValueError('선택한 추론 수준은 현재 Hermes 전송에서 지원하지 않습니다. Codex의 자동 위임 모드를 일반 추론 수준으로 낮춰 실행하지 않습니다.')
        return {'enabled': True, 'effort': effort}


def runtime(settings):
    if settings.get('provider') != 'openai-codex':
        return {'provider': 'custom', 'api_mode': 'chat_completions',
                'base_url': settings['base_url'], 'api_key': settings.get('api_key') or 'local'}
    from hermes_cli.auth_codex import resolve_codex_runtime_credentials
    creds = resolve_codex_runtime_credentials()
    return {'provider': 'openai-codex', 'api_mode': 'codex_responses',
            'base_url': creds['base_url'], 'api_key': creds['api_key']}


def goal_reasoning(worker, native, settings, options):
    """Restore the user's previous auxiliary reasoning when leaving the Codex route."""
    from copy import deepcopy
    key = '_platform_codex_goal_reasoning'
    if settings.get('provider') != 'openai-codex' and key not in native:
        return
    section = native.setdefault('auxiliary', {}).setdefault('goal_judge', {})
    extra = dict(section.get('extra_body') or {})
    if settings.get('provider') == 'openai-codex':
        reasoning = worker.codex.reasoning(settings['model'], options['reasoning_effort'])
        native.setdefault(key, {'present': 'reasoning' in extra, 'value': deepcopy(extra.get('reasoning'))})
        if reasoning:extra['reasoning'] = reasoning
        else:extra.pop('reasoning', None)
    else:
        previous = native.pop(key)
        if previous['present']:extra['reasoning'] = previous['value']
        else:extra.pop('reasoning', None)
    section['extra_body'] = extra
