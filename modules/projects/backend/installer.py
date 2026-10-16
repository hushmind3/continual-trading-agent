"""Persistent, verified installation transactions; failed updates retain the active version."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from platform_modules import ROOT
from . import adapters, runtime
from .github import repository
from .store import LOCK, STATE, identifier, read, records, save

JOBS = {}
RESTARTING = False
ACTIVE_STAGES = {'queued', 'download', 'analyze', 'adapter', 'dependencies', 'verify', 'publish'}


def run_command(command, folder, log, cancelled, timeout=180, environment=None):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('a', encoding='utf8') as output:
        process = subprocess.Popen(command, cwd=folder, stdout=output, stderr=subprocess.STDOUT,
            env={**os.environ, **(environment or {}), 'PYTHONUTF8': '1', 'GIT_TERMINAL_PROMPT': '0'})
        deadline = time.monotonic() + timeout
        while process.poll() is None:
            if cancelled.is_set() or time.monotonic() > deadline:
                import psutil
                try:
                    parent = psutil.Process(process.pid)
                    for child in parent.children(recursive=True):
                        try: child.kill()
                        except psutil.Error: pass
                    parent.kill()
                except psutil.Error: pass
                process.wait(timeout=10)
                raise ValueError('설치를 취소했습니다.' if cancelled.is_set() else '실행 시간이 초과됐습니다.')
            time.sleep(.2)
        if process.returncode:
            detail = log.read_text(encoding='utf8', errors='replace')[-5000:]
            raise ValueError(f'실행 실패 (종료 코드 {process.returncode})\n{detail}')


def busy_reason():
    with LOCK:
        return '실행 중인 프로젝트 설치·변환' if JOBS else runtime.busy_reason()


def public(record):
    value = {key: item for key, item in record.items() if key != 'environment'}
    value['environment_keys'] = sorted(record.get('environment', {}))
    for secret in record.get('environment', {}).values():
        if secret:
            for key in ('error', 'detail', 'log'):
                if isinstance(value.get(key), str): value[key] = value[key].replace(secret, '••••')
    return value


def installed():
    from menu_registry import MODULE_ENTRIES
    loaded = {item['id']: item.get('install_revision') for item, _ in MODULE_ENTRIES}
    result = []
    for record in records():
        record['can_open'] = record.get('module_id') in loaded and record['stage'] != 'removed'
        if record['stage'] == 'awaiting_activation' and record.get('module_id') in loaded and loaded[record['module_id']] == record.get('install_revision'):
            record.update(stage='ready', detail='실행 확인과 메뉴 연결을 마쳤습니다.', finished_at=time.time())
            save(record)
        elif record['stage'] in ACTIVE_STAGES and record['id'] not in JOBS:
            import psutil
            try:
                owner = psutil.Process(record.get('install_pid', 0))
                alive = abs(owner.create_time() - record.get('install_process_created', 0)) < .01
            except psutil.Error: alive = False
            if not alive:
                record.update(stage='failed', error='서버 종료로 설치가 중단됐습니다. 다시 시도하면 저장된 설정으로 재설치합니다.')
                save(record)
        if record.get('adapter', {}).get('kind') == 'native':
            entry = next((entry for item, entry in MODULE_ENTRIES if item['id'] == record.get('module_id')), None)
            if entry:
                menus = getattr(entry, 'MENUS', None) or getattr(entry, 'GROUP', {}).get('menus') or (entry.MENU,)
                record['menu'] = menus[0]['id']
        result.append(public(record))
    managed = {item.get('module_id') for item in result}
    for metadata, entry in MODULE_ENTRIES:
        if metadata['id'] == 'projects' or metadata['id'] in managed: continue
        menus = getattr(entry, 'MENUS', None) or getattr(entry, 'GROUP', {}).get('menus') or (entry.MENU,)
        result.append({'id': metadata['id'], 'module_id': metadata['id'], 'title': getattr(entry, 'MENU', {}).get('title') or metadata['group']['title'],
            'repository': '플랫폼에 포함된 모듈', 'url': '', 'stage': 'ready', 'builtin': True, 'group_title': metadata['group']['title'],
            'menu': menus[0]['id'], 'active_source': str(metadata['folder']),
            'detail': '기존 기능이 연결돼 있습니다.' + (' 공용 코드가 남아 있어 독립 분리는 별도 작업입니다.' if metadata.get('legacy_shared_code') else '')})
    return result


def start(url, source_override=None):
    global RESTARTING
    repo = repository(url)
    key = identifier('p_' + re.sub('[^a-z0-9_-]', '_', repo.lower())[:65] + '_' + hashlib.sha256(repo.lower().encode()).hexdigest()[:8])
    with LOCK:
        if RESTARTING: raise ValueError('서버 적용 중입니다. 잠시 뒤 등록하세요.')
        if JOBS: raise ValueError('진행 중인 설치가 있습니다. 완료하거나 취소한 뒤 등록하세요.')
        try: old = read(key)
        except ValueError: old = {}
        if old.get('stage') == 'awaiting_activation': raise ValueError('현재 설치본의 메뉴 연결을 기다리고 있습니다.')
        import psutil
        record = {**old, 'id': key, 'repository': repo, 'url': 'https://github.com/' + repo,
            'title': repo.split('/')[-1], 'stage': 'queued', 'detail': '설치를 준비합니다.',
            'error': '', 'started_at': time.time(), 'environment': old.get('environment', {}),
            'install_pid': os.getpid(), 'install_process_created': psutil.Process().create_time()}
        save(record); cancelled = threading.Event(); JOBS[key] = cancelled
        threading.Thread(target=install, args=(record, cancelled, source_override), daemon=True).start()
    return public(record)


def install(record, cancelled, source_override=None):
    key = record['id']; version = STATE / 'projects' / key / 'versions' / uuid.uuid4().hex[:12]
    source = version / 'source'
    log = version / 'install.log'; published = None; backup = None
    def progress(stage, detail, **extra):
        record.update(stage=stage, detail=detail, **extra); save(record)
    def run(command, folder, timeout=180):
        if cancelled.is_set(): raise ValueError('설치를 취소했습니다.')
        run_command(command, folder, log, cancelled, timeout)
    try:
        version.mkdir(parents=True)
        progress('download', 'GitHub에서 소스를 내려받습니다.', install_log=str(log), source=str(source))
        if source_override is not None:
            shutil.copytree(source_override, source)  # private local fixture entry; HTTP never accepts this argument
        else:
            run(['git', '-c', 'core.hooksPath=NUL', 'clone', '--depth', '1', '--', record['url'] + '.git', str(source)], version, 600)
        progress('analyze', 'README·의존성과 실제 실행 진입점을 확인합니다.')
        spec = adapters.detect(source)
        if spec is None and record.get('adapter'):
            try: spec = adapters.validate(source, record['adapter'])
            except ValueError: pass
        if spec is None:
            spec = adapters.generate_with_hermes(source, '자동 탐지로 실행 진입점을 확인하지 못했습니다.', cancelled, progress, key)
        progress('dependencies', '설치된 실행 환경을 재사용하고 필요한 의존성과 화면을 준비합니다.', detected=spec['kind'])
        def prepare_and_verify():
            adapters.prepare(source, spec, run)
            progress('verify', '원본 실행 결과를 확인합니다. 성공한 설치본만 연결합니다.')
            runtime.verify(source, spec, record.get('environment', {}))
            if spec['kind'] == 'python-cli': runtime.run_cli({**record, 'active_source': str(source), 'adapter': spec}, ['--help'])
            return runtime.verify_ui(source, spec, record.get('environment', {}), run, key)
        try: ui_verified = prepare_and_verify()
        except Exception as original:
            if cancelled.is_set() or spec['kind'] == 'native': raise
            try:
                spec = adapters.generate_with_hermes(source, str(original), cancelled, progress, key)
                ui_verified = prepare_and_verify()
            except Exception as adaptation:
                raise ValueError(f'실행 확인 실패: {original}\n자동 변환: {adaptation}') from adaptation
        module_id = 'external_' + key
        if spec['kind'] == 'native':
            metadata = json.loads((source / 'module.json').read_text(encoding='utf8'))
            module_id = identifier(metadata['id'])
            candidate = source
        else:
            candidate = version / 'module'; (candidate / 'backend').mkdir(parents=True); (candidate / 'frontend').mkdir()
            metadata = {'schema': 1, 'id': module_id, 'group': {'id': module_id, 'title': record['title']},
                'backend': {'namespace': 'platform_plugins.' + module_id.replace('-', '_'), 'entry': 'register'},
                'frontend': {'entry': 'frontend/register.ts'}, 'data': ['runtime/projects/manage/projects/' + key], 'order': 60}
            (candidate / 'module.json').write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf8')
            menu = {'id': 'projects/app/' + key, 'title': record['title'], 'operations': []}
            (candidate / 'backend/register.py').write_text('from fastapi import APIRouter\nMENU=' + repr(menu) + '\nrouter=APIRouter()\n', encoding='utf8')
            (candidate / 'frontend/register.ts').write_text(
                "import {createElement,lazy} from 'react';\nimport {Package} from 'lucide-react';\n"
                "import type {MenuItem} from '@platform/shell/menu_groups/menu_types';\n"
                "const component=lazy(()=>import('../../projects/frontend/ProjectApp').then(m=>({default:()=>createElement(m.ProjectApp,{projectId:"
                + json.dumps(key) + "})})));\nexport const menus:MenuItem[]=[{hash:"
                + json.dumps('projects/app/' + key) + ',name:' + json.dumps(record['title']) + ',group:' + json.dumps(record['title'])
                + ",icon:Package,required:[],component}];\n", encoding='utf8')
        if record.get('module_id') and record['module_id'] != module_id:
            raise ValueError('업데이트에서 모듈 ID가 바뀌었습니다. 기존 모듈은 유지합니다.')
        destination = ROOT / 'modules' / identifier(module_id)
        if destination.exists():
            if record.get('module_id') != module_id: raise ValueError('같은 이름의 다른 모듈이 이미 있습니다.')
            backup = version / 'previous-module'; destination.rename(backup)
        published = destination
        shutil.copytree(candidate, destination, ignore=shutil.ignore_patterns('.git', '__pycache__', '.venv'))
        metadata['install_revision'] = version.name
        (destination / 'module.json').write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf8')
        progress('publish', '전체 연결을 사전 확인하고 새 메뉴를 준비합니다.')
        run([sys.executable, '-B', '-c', 'import sys;sys.path.insert(0,"backend");import web_api'], ROOT, 120)
        node = shutil.which('node')
        run([node, str(ROOT / 'node_modules/typescript/bin/tsc'), '--noEmit'], ROOT / 'frontend', 120)
        run([node, str(ROOT / 'node_modules/vite/bin/vite.js'), 'build', '--emptyOutDir', 'false'], ROOT / 'frontend', 180)
        # The common watcher performs guarded application after the install transaction releases its busy hook.
        record.update(active_source=str(source), adapter=spec, module_id=module_id, install_revision=version.name, menu='projects/app/' + key,
            verification={'entry_executed': spec['kind'] in ('fastapi', 'python-cli'), 'original_ui_rendered': ui_verified},
            stage='awaiting_activation', detail='실행 확인 완료 · 공통 실행기가 메뉴 연결을 적용합니다.', published_at=time.time())
        save(record)
    except Exception as exc:
        if published and published.exists():
            trash = ROOT / '휴지통/modules' / (published.name + '-' + uuid.uuid4().hex[:8]); trash.parent.mkdir(parents=True, exist_ok=True)
            published.rename(trash)
        if backup and backup.exists(): backup.rename(ROOT / 'modules' / record['module_id'])
        record.update(stage='cancelled' if cancelled.is_set() else 'failed', error=str(exc), detail='설치를 완료하지 못했습니다. 기존 사용 데이터와 설치본은 보존했습니다.', finished_at=time.time())
        save(record)
    finally:
        with LOCK: JOBS.pop(key, None)


def cancel(key):
    with LOCK:
        event = JOBS.get(identifier(key))
        if not event: raise ValueError('진행 중인 설치가 없습니다.')
        event.set()
    return {'requested': True}
