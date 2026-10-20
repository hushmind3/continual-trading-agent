"""UI adapter for the original Hermes Codex OAuth provider; no second agent."""
import threading


class CodexConnection:
    def __init__(self):
        self.lock = threading.RLock()
        self.login = {'state': 'idle'}

    def status(self):
        from hermes_cli.auth import get_codex_auth_status
        auth = get_codex_auth_status()
        with self.lock:
            return {**self.login, 'connected': bool(auth.get('logged_in'))}

    def start(self):
        from hermes_cli.auth_codex import _codex_request_device_code, CODEX_OAUTH_CLIENT_ID
        with self.lock:
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
        from hermes_cli.codex_models import get_codex_model_ids
        from hermes_cli.models_catalog_static import CuratedFallbackModels
        creds = resolve_codex_runtime_credentials(read_only=True)
        models = get_codex_model_ids(access_token=creds['api_key'], base_url=creds['base_url'])
        return {'models': [{'id': model} for model in models],
                'catalog_live': not isinstance(models, CuratedFallbackModels)}


def runtime(settings):
    if settings.get('provider') != 'openai-codex':
        return {'provider': 'custom', 'api_mode': 'chat_completions',
                'base_url': settings['base_url'], 'api_key': settings.get('api_key') or 'local'}
    from hermes_cli.auth_codex import resolve_codex_runtime_credentials
    creds = resolve_codex_runtime_credentials()
    return {'provider': 'openai-codex', 'api_mode': 'codex_responses',
            'base_url': creds['base_url'], 'api_key': creds['api_key']}
