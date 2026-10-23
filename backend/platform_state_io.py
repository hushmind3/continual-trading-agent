"""Serialize writers and tolerate short Windows file-sharing conflicts."""
from __future__ import annotations

import json
import errno
import os
from copy import deepcopy
from pathlib import Path
import threading
import time
import tempfile
from contextlib import contextmanager
from weakref import WeakValueDictionary

_locks = WeakValueDictionary()
_guard = threading.Lock()
_listeners = set()


def subscribe_updates(callback):
    with _guard:_listeners.add(callback)


def read_json(path: str | Path, fallback=None):
    """Read persisted state; each failure returns a caller-owned default."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return deepcopy(fallback) if fallback is not None else {}


@contextmanager
def json_transaction(path: str | Path):
    """Serialize the entire read/modify/write operation across threads and processes."""
    path = Path(path)
    with _guard:
        key = str(path.resolve())
        lock = _locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _locks[key] = lock
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.with_name(path.name + '.lock').open('a+b') as guard:
            guard.seek(0, os.SEEK_END)
            if guard.tell() == 0:guard.write(b'\0');guard.flush()
            if os.name == 'nt':
                import msvcrt
                while True:
                    try:
                        guard.seek(0);msvcrt.locking(guard.fileno(),msvcrt.LK_NBLCK,1);break
                    except OSError as exc:
                        if exc.errno not in (errno.EACCES,errno.EAGAIN,errno.EDEADLK):raise
                        time.sleep(.025)
            else:
                import fcntl
                fcntl.flock(guard.fileno(),fcntl.LOCK_EX)
            try:yield path
            finally:
                if os.name == 'nt':
                    guard.seek(0);msvcrt.locking(guard.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(guard.fileno(),fcntl.LOCK_UN)


def _write_json(value,path,default=None):
    serialized=json.dumps(value, ensure_ascii=False, indent=2, default=default)
    descriptor,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
    temporary=Path(name)
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8') as stream:stream.write(serialized)
        for attempt in range(8):
            try:
                os.replace(temporary,path);break
            except PermissionError:
                if attempt==7:raise
                time.sleep(.025*(attempt+1))
    finally:temporary.unlink(missing_ok=True)
    return serialized


def _notify(path,serialized):
    with _guard:listeners=tuple(_listeners)
    for callback in listeners:callback(path,serialized)


def atomic_json(value, path: str | Path, default=None) -> None:
    with json_transaction(path) as target:serialized=_write_json(value,target,default)
    _notify(target,serialized)


def update_json(path,update,fallback=None):
    with json_transaction(path) as target:
        value=read_json(target,fallback)
        updated=update(value)
        if updated is None:return value
        serialized=_write_json(updated,target)
    _notify(target,serialized)
    return updated
