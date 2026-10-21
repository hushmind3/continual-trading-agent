"""Filesystem module registration. Program folders never own persistent state."""
from __future__ import annotations
import hashlib
import importlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import re
import sys
import types
from functools import lru_cache
from platform_native import native_runtime_path

ROOT = Path(__file__).resolve().parents[1]
MODULES = Path(os.environ.get('PLATFORM_MODULES_DIR') or ROOT / 'modules').resolve()


def discover(directory=None):
    records = []
    seen = set()
    namespaces = set()
    for path in sorted(Path(directory or MODULES).glob('*/module.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data.get('resources'), dict):
            data['resources'] = {key:native_runtime_path(value) if isinstance(value,str) else value
                                 for key,value in data['resources'].items()}
        identifier = data.get('id', '')
        if data.get('schema') != 1 or not re.fullmatch(r'[a-z][a-z0-9_-]*', identifier):
            raise ValueError(f'Invalid module manifest: {path}')
        if identifier in seen:
            raise ValueError(f'Duplicate module id: {identifier}')
        seen.add(identifier)
        if data.get('enabled', True) is False:
            continue
        namespace = data['backend']['namespace']
        if not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', namespace):
            raise ValueError(f'Invalid module namespace: {identifier}')
        if any(namespace == used or namespace.startswith(used + '.') or used.startswith(namespace + '.') for used in namespaces):
            raise ValueError(f'Module namespace collision: {identifier} ({namespace})')
        namespaces.add(namespace)
        source = (path.parent / data['backend'].get('path', 'backend')).resolve()
        if not source.is_relative_to(path.parent.resolve()) or not source.is_dir():
            raise ValueError(f'Module backend is missing or outside its folder: {identifier}')
        if data.get('install_revision'):
            data = {**data, 'group': {'id': 'projects', 'title': 'GitHub'}}
        records.append({**data, 'folder': path.parent.resolve(), 'source': source})
    return records


def mount_namespaces(records=None):
    for item in records if records is not None else discover():
        namespace = item['backend']['namespace']
        parts = namespace.split('.')
        for index in range(1, len(parts)+1):
            name = '.'.join(parts[:index])
            if name in sys.modules:
                continue
            package = types.ModuleType(name)
            parent_source = ROOT / 'backend' / Path(*parts[:index])
            package.__path__ = [str(item['source'])] if index == len(parts) else ([str(parent_source)] if parent_source.is_dir() else [])
            package.__package__ = name
            package.__spec__ = importlib.util.spec_from_loader(name, loader=None, is_package=True)
            sys.modules[name] = package
            if index > 1:
                setattr(sys.modules['.'.join(parts[:index-1])], parts[index-1], package)


@lru_cache(maxsize=1)
def registrations():
    records = discover()
    mount_namespaces(records)
    result=[]
    for item in records:
        try:entry=importlib.import_module(item['backend']['namespace']+'.'+item['backend'].get('entry', 'register'))
        except Exception as exc:
            from fastapi import APIRouter
            entry=types.SimpleNamespace(router=APIRouter(),load_error=str(exc),
                MENU={'id':item['id'],'title':item['group']['title'],'operations':[]})
        result.append((item,entry))
    return result


def busy_reasons():
    result = []
    for item, entry in registrations():
        callback = getattr(entry, 'busy_reason', None)
        if callback:
            try:
                if reason := callback():result.append(reason)
            except Exception as exc:
                result.append(f"{item['id']} 작업 상태 확인 실패: {exc}")
    return result


def lifecycle(method):
    completed = []
    try:
        for item, entry in registrations():
            callback = getattr(entry, method, None)
            if callback:
                callback()
                completed.append(entry)
    except Exception:
        if method == 'reserve_restart':
            for entry in reversed(completed):
                cancel = getattr(entry, 'cancel_restart', None)
                if cancel:
                    try:cancel()
                    except Exception as exc:logging.getLogger(__name__).warning('Restart reservation rollback failed: %s',exc)
        raise


def signature(directory=None):
    digest = hashlib.sha256()
    for path in sorted(Path(directory or MODULES).glob('*/module.json')):
        digest.update(path.parent.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
