"""Project installation submenu, behind the existing /api envelope."""
from pathlib import Path
import shlex
import re
from fastapi import APIRouter, HTTPException
from . import github, installer, runtime
from .store import LOCK, ROOT, STATE, identifier, read, save

router = APIRouter(prefix='/api/projects')


def call(function, *args):
    try: return function(*args)
    except (ValueError, RuntimeError, OSError) as exc: raise HTTPException(400, str(exc)) from exc


@router.get('/search')
def search(q: str, page: int = 1): return call(github.search, q, page)


@router.get('/installed')
def installed(): return {'items': installer.installed()}


@router.post('/install')
def install(request: dict): return call(installer.start, request.get('url', ''))


@router.post('/cancel')
def cancel(request: dict): return call(installer.cancel, request.get('id', ''))


@router.get('/detail')
def detail(id: str):
    record = call(read, id); value = installer.public(record)
    log = Path(record.get('install_log') or STATE / 'absent')
    if log.is_file() and log.resolve().is_relative_to(STATE.resolve()):
        with log.open('rb') as stream:
            stream.seek(0, 2); stream.seek(max(0, stream.tell() - 30000))
            value['log'] = stream.read().decode('utf8', errors='replace')
        value = installer.public({**record, **value})
    return value


@router.post('/settings')
def settings(request: dict):
    def update():
        key = identifier(request.get('id', '')); environment = request.get('environment', {})
        if not isinstance(environment, dict) or not all(re.fullmatch(r'[A-Za-z_]\w*', name) and isinstance(value, str)
            and len(value) <= 16000 for name, value in environment.items()):
            raise ValueError('환경 설정의 이름과 값을 확인하세요.')
        with LOCK, runtime.LOCK:
            if key in installer.JOBS or runtime.busy_reason(): raise ValueError('실행이 끝난 뒤 설정을 저장하세요.')
            worker = runtime.WORKERS.pop(key, None)
            if worker: worker.close()
            record = read(key); record['environment'] = {**record.get('environment', {}), **environment}; save(record)
        return installer.public(record)
    return call(update)


@router.post('/invoke')
def invoke(request: dict):
    if len(str(request.get('body', ''))) > 2 * 1024 * 1024: raise HTTPException(413, '요청 본문이 너무 큽니다.')
    return call(runtime.invoke, call(read, request.get('id', '')), request)


@router.post('/run')
def run(request: dict):
    arguments = request.get('arguments', '')
    if isinstance(arguments, str): arguments = shlex.split(arguments)
    return call(runtime.run_cli, call(read, request.get('id', '')), arguments)


@router.post('/remove')
def remove(request: dict):
    def detach():
        import uuid
        from menu_registry import MODULE_ENTRIES
        key = identifier(request.get('id', ''))
        with LOCK, runtime.LOCK:
            if installer.busy_reason(): raise ValueError('실행 중인 작업을 마친 뒤 분리하세요.')
            record = read(key); module_id = identifier(record.get('module_id', ''))
            entry = next((entry for item, entry in MODULE_ENTRIES if item['id'] == module_id), None)
            if entry:
                if callback := getattr(entry, 'busy_reason', None):
                    if reason := callback(): raise ValueError(reason)
                if callback := getattr(entry, 'reserve_restart', None): callback()
                if callback := getattr(entry, 'close', None): callback()
            worker = runtime.WORKERS.pop(key, None)
            if worker: worker.close()
            folder = ROOT / 'modules' / module_id
            if folder.exists():
                trash = ROOT / '휴지통/modules' / (module_id + '-' + uuid.uuid4().hex[:8]); trash.parent.mkdir(parents=True, exist_ok=True)
                folder.rename(trash)
            record.update(stage='removed', detail='메뉴에서 분리했습니다. 소스·설정·설치 기록은 보존했습니다.')
            save(record)
        return installer.public(record)
    return call(detach)
