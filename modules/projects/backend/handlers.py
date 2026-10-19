"""Project installation submenu, behind the existing /api envelope."""
from pathlib import Path
import shlex
import re
from fastapi import APIRouter, HTTPException, Request
from . import github, installer, runtime, lifecycle, localization
from .store import LOCK, STATE, identifier, read, save

router = APIRouter(prefix='/api/projects')


def call(function, *args):
    try: return function(*args)
    except (ValueError, RuntimeError, OSError) as exc: raise HTTPException(400, str(exc)) from exc


@router.get('/search')
def search(q: str, page: int = 1, sort: str = ''): return call(github.search, q, page, sort)


@router.get('/installed')
def installed():
    from menu_registry import MODULE_ENTRIES
    return {'items': installer.installed(), 'active_module_ids': [metadata['id'] for metadata, _ in MODULE_ENTRIES]}


@router.post('/cleanup')
def cleanup_projects():
    from .cleanup import clean
    return call(clean)


@router.post('/folder/open')
def open_folder(request:dict):
    def open_owned():
        import os
        key=identifier(request.get('id',''))
        try:record=read(key)
        except ValueError:
            from .detachment import builtin_record
            record=builtin_record(key)
        from .store import project_folder
        folder=Path(record.get('standalone_path') or (record.get('active_source') if record.get('builtin') else project_folder(record))).resolve()
        from .store import ROOT
        if not folder.is_dir() or not folder.is_relative_to(ROOT.resolve()):raise ValueError('앱 폴더가 없습니다.')
        if os.name!='nt':raise ValueError('폴더 열기는 현재 Windows에서 지원합니다.')
        os.startfile(str(folder))
        return {'path':str(folder)}
    return call(open_owned)


@router.post('/install')
def install(request: dict): return call(installer.start, request.get('url', ''), None, False, request.get('allow_agent') is True)


@router.post('/cancel')
def cancel(request: dict): return call(installer.cancel, request.get('id', ''))


@router.post('/retry')
def retry(request: dict):
    record = call(read, request.get('id', ''))
    return call(installer.start, record['url'], None, True, request.get('allow_agent') is True)


@router.get('/detail')
def detail(id: str):
    def record_for():
        try:return read(id)
        except ValueError:
            from .detachment import builtin_record
            return builtin_record(id)
    record = call(record_for); value = installer.public(record)
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
            record = read(key); record['environment'] = {**record.get('environment', {}), **environment}
            if 'use_harness' in request:
                from .harness import configure
                configure(record, request['use_harness'])
            if isinstance(request.get('allow_agent'), bool): record['allow_agent'] = request['allow_agent']
            save(record)
        return installer.public(record)
    return call(update)


@router.get('/harness')
def harness_status(id: str):
    from .harness import status
    return call(status, id)


@router.post('/harness')
def harness_control(request: dict):
    from .harness import control
    return call(control, request.get('id', ''), request)


@router.post('/invoke')
def invoke(request: dict, connection: Request):
    if len(str(request.get('body', ''))) > 2 * 1024 * 1024: raise HTTPException(413, '요청 본문이 너무 큽니다.')
    return call(runtime.invoke, call(read, request.get('id', '')), request, connection)


@router.post('/run')
def run(request: dict):
    arguments = request.get('arguments', '')
    if isinstance(arguments, str): arguments = shlex.split(arguments)
    return call(runtime.run_cli, call(read, request.get('id', '')), arguments)


@router.get('/interface')
def project_interface(id:str):
    from .cli_schema import describe
    return call(describe,call(read,id))


@router.post('/action')
def project_action(request:dict):
    from .cli_schema import execute
    return call(execute,call(read,request.get('id','')),request.get('command',''),request.get('values',{}))


@router.get('/setup')
def setup_details(id:str):
    from .powershell_app import describe
    return call(describe,call(read,id))


@router.post('/setup')
def setup_start(request:dict):
    from .powershell_app import start
    return call(start,call(read,request.get('id','')),request.get('values',{}))


@router.get('/setup/status')
def setup_status(id:str):
    from .powershell_app import state
    return call(state,call(read,id))


@router.post('/setup/stop')
def setup_stop(request:dict):
    from .powershell_app import stop
    return call(stop,request.get('id',''))


@router.post('/setup/folder')
def setup_folder(request:dict):
    from .powershell_app import choose_folder
    record=call(read,request.get('id',''))
    if record.get('adapter',{}).get('kind')!='powershell':raise HTTPException(400,'Windows 설치 프로그램이 아닙니다.')
    return call(choose_folder)


@router.post('/remove')
def remove(request: dict):
    return call(lifecycle.remove, request.get('id', ''))


@router.post('/detach')
def detach(request: dict):
    from .detachment import start
    return call(start,request.get('id',''))


@router.post('/reconnect')
def reconnect(request: dict): return call(lifecycle.reconnect, request.get('id', ''))


@router.post('/localize')
def localize(request: dict): return call(localization.localize, request.get('texts', []))


@router.post('/export')
def export_project(request: dict):
    from .packages import export
    return call(export, request.get('id', ''))


@router.post('/import')
def import_project(request: dict):
    from .package_import import install
    return call(install, request.get('archive', ''))


@router.post('/agent/connect')
def agent_connect(request: dict):
    from .agent_tasks import link
    return call(link, call(read, request.get('id', '')))


@router.post('/agent/start')
def agent_start(request: dict):
    from .agent_tasks import start
    return call(start, request)
