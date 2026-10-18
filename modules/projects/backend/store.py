"""Durable installation records; application state never lives in module folders."""
from pathlib import Path
import json
import os
import re
import shutil
import stat
import threading
import time
import uuid
from platform_modules import ROOT

STATE = ROOT / 'runtime/projects/manage'
LOCK = threading.RLock()


def identifier(value):
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,100}', str(value)):
        raise ValueError('프로젝트 ID가 올바르지 않습니다.')
    return value


def read(key):
    with LOCK:
        path = STATE / 'registry' / (identifier(key) + '.json')
        if not path.is_file():
            raise ValueError('등록된 프로젝트가 없습니다.')
        return json.loads(path.read_text(encoding='utf8'))


def save(value):
    with LOCK:
        path = STATE / 'registry' / (identifier(value['id']) + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')
        try:
            for attempt in range(40):
                try:
                    os.replace(temp, path); break
                except PermissionError:
                    if attempt == 39: raise
                    time.sleep(.05)
        finally: temp.unlink(missing_ok=True)
    return value


def records():
    with LOCK:
        return [json.loads(path.read_text(encoding='utf8')) for path in sorted((STATE / 'registry').glob('*.json'))]


def owned(base, relative):
    base = Path(base).resolve()
    path = (base / relative).resolve()
    if not path.is_relative_to(base):
        raise ValueError('프로젝트 폴더 밖의 경로입니다.')
    return path


def project_folder(record):
    """One existing management-owned parent for every imported app."""
    return owned(STATE,'projects/'+identifier(record.get('folder_name') or record['id']))


def assign_folder(record):
    """Stable readable directory, separate from old public IDs. Called only while idle."""
    if record.get('builtin') or record.get('folder_name'): return record
    name = re.sub(r'[^a-z0-9_-]+', '-', record.get('repository', record['id']).split('/')[-1].lower()).strip('-_')
    if not name or not name[0].isalpha(): name = 'app-' + name
    name = name[:80]
    reserved = {r.get('folder_name') or r['id'] for r in records() if r['id'] != record['id']}
    if name in reserved or (STATE/'projects'/name).exists():
        owner = re.sub(r'[^a-z0-9_-]+', '-', record.get('repository', 'app').split('/')[0].lower())
        name = ('app-' + owner + '-' + name)[:100]
    target = owned(STATE, 'projects/' + identifier(name))
    previous = project_folder(record)
    if target.exists(): raise ValueError('같은 이름의 앱 폴더가 있습니다. 덮어쓰지 않습니다.')
    if record.get('stage') == 'removed': raise ValueError('분리한 앱은 다시 연결한 뒤 업데이트하세요.')
    updated = dict(record); copied = False
    if previous.exists():
        if previous.is_symlink(): raise ValueError('연결된 외부 폴더는 이동하지 않습니다.')
        target.parent.mkdir(parents=True, exist_ok=True)
        try: previous.rename(target)
        except PermissionError:
            # Windows can refuse directory rename while descendants are watched.
            # Keep the complete original until the copied tree and registry are ready.
            try: shutil.copytree(previous, target, symlinks=True)
            except Exception:
                if target.exists(): shutil.rmtree(target)
                raise
            copied = True
        def rewrite(value):
            if isinstance(value, str): return value.replace(str(previous), str(target)).replace(previous.as_posix(), target.as_posix())
            if isinstance(value, list): return [rewrite(v) for v in value]
            if isinstance(value, dict): return {k: rewrite(v) for k,v in value.items()}
            return value
        updated = rewrite(updated)
    updated['folder_name'] = name
    manifest = owned(ROOT / 'modules', identifier(record.get('module_id') or 'unregistered')) / 'module.json'
    original = manifest.read_bytes() if manifest.is_file() else None
    try:
        if original:
            metadata = json.loads(original)
            old_data = previous.relative_to(ROOT).as_posix()
            metadata['data'] = [target.relative_to(ROOT).as_posix() if item == old_data else item for item in metadata.get('data', [])]
            manifest.write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf8')
        save(updated)
    except Exception:
        if original: manifest.write_bytes(original)
        if copied: shutil.rmtree(target)
        elif target.exists() and not previous.exists(): target.rename(previous)
        raise
    if copied:
        def writable(function, path, error):
            if not isinstance(error[1], PermissionError): raise error[1]
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD); function(path)
        try: shutil.rmtree(previous, onerror=writable)
        except OSError:
            updated['legacy_folder_name'] = previous.name
            save(updated)
    record.clear(); record.update(updated)
    return record


def install_folder(record):
    return owned(project_folder(record),'application')
