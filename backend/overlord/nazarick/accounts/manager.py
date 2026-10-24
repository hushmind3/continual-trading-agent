"""Shared settings submenu behind the platform's single API."""
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from . import browser, state, vault

MENU = {'id': 'overlord/nazarick/accounts', 'title': '공용 설정',
        'operations': ['overlord/nazarick/accounts/']}
router = APIRouter(prefix='/api/overlord/nazarick/accounts')


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Service(Strict):
    id: str = Field(default_factory=lambda: uuid4().hex, pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=8, max_length=2000)
    login: Literal['google', 'github', 'email', 'other'] = 'google'
    status: Literal['pending', 'working', 'waiting_user', 'registered', 'key_ready', 'failed'] = 'pending'
    notes: str = Field(default='', max_length=1000)

    @field_validator('url')
    @classmethod
    def validate_url(cls, value):
        return browser.public_url(value)


class Batch(Strict):
    items: list[Service] = Field(min_length=1, max_length=100)


class Open(Strict):
    target: str = Field(min_length=1, max_length=80)


class Credential(Strict):
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    secret: SecretStr


class BrowserChoice(Strict):
    browser_id: str = Field(min_length=1, max_length=40)


class BrowserStart(Strict):
    mode: Literal['login', 'automation'] = 'login'


def guarded(action):
    try:
        return action()
    except (ValueError, OSError) as error:
        raise HTTPException(409, str(error)) from error


@router.get('/status')
def status():
    from .integration import status as agent_status
    return {'browser': browser.status(), 'services': state.listing(),
            'vault': {'available': vault.supported(), 'name': 'macOS 키체인'},
            'agents': agent_status()}


@router.post('/browser/start')
def start(value: BrowserStart):
    return guarded(lambda: browser.start(value.mode))


@router.post('/browser/select')
def choose_browser(value: BrowserChoice):
    return guarded(lambda: browser.choose(value.browser_id))


@router.post('/browser/open')
def open_target(value: Open):
    def open_account():
        from . import providers
        account = next((item for item in providers.accounts() if item['id'] == value.target), None)
        if account:
            saved = next(item for item in browser.status()['accounts'] if item['id'] == value.target)['state'] == 'saved'
            url = account['account_url'] if saved else account['login_url']
        else:
            url = state.find(value.target)['url']
        return browser.open_page(url)
    return guarded(open_account)


@router.post('/services/save')
def save(value: Service):
    return state.save(value.model_dump())


@router.post('/services/import')
def import_services(value: Batch):
    # Deterministic IDs can be supplied by importers to make repeated imports idempotent.
    return {'items': [state.save(item.model_dump()) for item in value.items]}


@router.post('/credential')
def credential(value: Credential):
    def store():
        state.find(value.id)
        secret = value.secret.get_secret_value()
        if not 1 <= len(secret) <= 16384:
            raise ValueError('API 키 길이를 확인하세요.')
        vault.save(value.id, secret)
        with state.database() as db:
            db.execute('UPDATE services SET credential_saved=1,updated_at=? WHERE id=?', (state.now(), value.id))
        return {'saved': True, 'storage': 'macOS Keychain'}
    return guarded(store)


@router.post('/agents/connect')
def connect():
    from .integration import connect as apply
    return guarded(apply)
