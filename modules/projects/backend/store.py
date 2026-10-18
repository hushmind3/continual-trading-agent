"""Durable installation records; application state never lives in module folders."""
from pathlib import Path
import json
import os
import re
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
    return owned(STATE,'projects/'+identifier(record['id']))


def install_folder(record):
    return owned(project_folder(record),'application')
