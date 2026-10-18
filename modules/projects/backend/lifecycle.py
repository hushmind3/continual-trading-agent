"""Detach/reconnect reusable modules; uninstall only the selected project's owned files."""
import json
import os
from pathlib import Path
import shutil
import stat
import uuid
from . import installer, runtime, store


def module_folder(record):
    name = record.get('module_id')
    if not name: return None
    folder = store.owned(store.ROOT / 'modules', store.identifier(name))
    if folder.exists():
        manifest = folder / 'module.json'
        if not manifest.is_file() and record.get('stage') == 'removal_failed' and record.get('install_revision'): return folder
        metadata = json.loads(manifest.read_text(encoding='utf8'))
        builtin=record.get('builtin') and name in {'finance','rea','hermes'}
        if metadata.get('id') != name or not (metadata.get('install_revision') or builtin):
            raise ValueError('이 설치기가 소유한 프로젝트 모듈이 아닙니다.')
    return folder


def idle(record):
    from menu_registry import MODULE_ENTRIES
    if installer.RESTARTING or installer.JOBS or runtime.busy_reason(): raise ValueError('진행 중인 작업이 끝난 뒤 다시 시도하세요.')
    entry = next((entry for metadata, entry in MODULE_ENTRIES if metadata['id'] == record.get('module_id')), None)
    if entry:
        if callback := getattr(entry, 'busy_reason', None):
            if reason := callback(): raise ValueError(reason)
        if callback := getattr(entry, 'reserve_restart', None): callback()
        if callback := getattr(entry, 'close', None): callback()
    worker = runtime.WORKERS.pop(record['id'], None)
    if worker: worker.close()


def detached(record):
    base = store.project_folder(record)
    if record.get('detached_module'):
        candidate = store.owned(base, str(Path(record['detached_module']).relative_to(base)))
        if candidate.is_dir(): return candidate
    # Compatibility with modules detached by the old trash-based implementation.
    if record.get('module_id'):
        for path in (store.ROOT / '휴지통/modules').glob(store.identifier(record['module_id']) + '-*'):
            path = store.owned(store.ROOT / '휴지통/modules', path.name)
            manifest = path / 'module.json'
            if manifest.is_file() and json.loads(manifest.read_text(encoding='utf8')).get('id') == record['module_id']:
                return path
    return None


def detach(key):
    with store.LOCK, runtime.LOCK:
        record = store.read(key)
        if not record.get('active_source'): raise ValueError('실행 가능한 설치본이 없습니다. 제거로 정리하세요.')
        folder = module_folder(record)
        if not folder or not folder.is_dir(): raise ValueError('연결된 모듈이 없습니다.')
        idle(record)
        from .agent_tasks import link
        link(record, remove=True)
        target = store.owned(store.project_folder(record), 'detached/' + uuid.uuid4().hex)
        target.parent.mkdir(parents=True, exist_ok=True)
        folder.rename(target)
        try:
            record.update(stage='removed', detached_module=str(target), detail='연결만 분리했습니다. 파일·설정·기록은 보관하며 다시 연결할 수 있습니다.')
            store.save(record)
        except Exception:
            target.rename(folder)
            raise
        return installer.public(record)


def reconnect(key):
    with store.LOCK, runtime.LOCK:
        record = store.read(key)
        if record['stage'] != 'removed': raise ValueError('분리된 프로젝트만 다시 연결할 수 있습니다.')
        if record.get('builtin'):
            idle(record)
            from .detachment import reconnect_builtin
            return reconnect_builtin(record)
        source = store.owned(store.project_folder(record), str(Path(record.get('active_source') or '').relative_to(store.project_folder(record))))
        candidate = detached(record)
        if not source.is_dir() or not candidate: raise ValueError('보관된 설치 파일이 없습니다. 다시 설치하세요.')
        folder = module_folder(record)
        if not folder or folder.exists(): raise ValueError('같은 모듈이 이미 연결돼 있습니다.')
        idle(record)
        from .agent_tasks import link
        link(record)
        candidate.rename(folder)
        try:
            metadata = json.loads((folder / 'module.json').read_text(encoding='utf8'))
            record.update(stage='awaiting_activation', install_revision=metadata['install_revision'], error='',
                detail='보관된 설치본을 다시 연결합니다. 다운로드·AI 변환은 실행하지 않습니다.')
            store.save(record)
        except Exception:
            folder.rename(candidate)
            raise
        return installer.public(record)


def remove(key):
    with store.LOCK, runtime.LOCK:
        key = store.identifier(key); record = store.read(key)
        folder = module_folder(record)
        idle(record)
        from .agent_tasks import link
        link(record, remove=True)
        paths = [store.project_folder(record)]
        if record.get('legacy_folder_name') == key:
            paths.append(store.owned(store.STATE, 'projects/' + key))
        if folder and folder.exists(): paths.insert(0, folder)
        # Delete only this project's legacy detached modules, never unrelated trash.
        if record.get('module_id'):
            for candidate in (store.ROOT / '휴지통/modules').glob(store.identifier(record['module_id']) + '-*'):
                manifest = candidate / 'module.json'
                if manifest.is_file() and json.loads(manifest.read_text(encoding='utf8')).get('id') == record['module_id']:
                    paths.append(candidate)
        registry = store.owned(store.STATE, 'registry/' + key + '.json')
        root = store.ROOT.resolve()
        if not store.STATE.resolve().is_relative_to(root) or any(not path.resolve().is_relative_to(root) or path.is_symlink() for path in [*paths, registry]):
            raise ValueError('프로젝트 작업 경계 밖의 파일은 제거하지 않습니다.')
        def writable(function, path, error):
            if not isinstance(error[1], PermissionError): raise error[1]
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD); function(path)
        try:
            for path in paths:
                if path.is_dir(): shutil.rmtree(path, onerror=writable)
            registry.unlink()
        except OSError as exc:
            record.update(stage='removal_failed', error=str(exc), detail='일부 파일을 제거하지 못했습니다. 실행 중인 파일을 닫고 제거를 다시 누르세요.')
            store.save(record)
            raise ValueError(record['detail']) from exc
        return {'id': key, 'deleted': True, 'permanent': True}
