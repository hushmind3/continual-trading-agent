"""Local metadata only. Passwords/cookies/API keys never enter SQLite."""
from contextlib import contextmanager
from pathlib import Path
import json
import os
import sqlite3
from ..store import STATE as PARENT, now

STATE = PARENT / 'accounts'


def private_directory():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE, 0o700)
    return STATE


def write_json(path: Path, value):
    private_directory()
    temporary = path.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
    os.replace(temporary, path)


@contextmanager
def exclusive(name):
    """Coordinate API and independently launched MCP/CLI processes."""
    path = private_directory() / (name + '.lock')
    with path.open('a+b') as handle:
        os.chmod(path, 0o600)
        if os.name == 'nt':
            import msvcrt
            handle.write(b'\0'); handle.flush(); handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


@contextmanager
def database():
    path = private_directory() / 'accounts.sqlite3'
    db = sqlite3.connect(path, timeout=10)
    os.chmod(path, 0o600)
    db.row_factory = sqlite3.Row
    try:
        db.execute('''CREATE TABLE IF NOT EXISTS services (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL,
          login TEXT NOT NULL, status TEXT NOT NULL, notes TEXT NOT NULL,
          credential_saved INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL)''')
        with db:
            yield db
    finally:
        db.close()


def listing():
    with database() as db:
        return [dict(row) for row in db.execute('SELECT * FROM services ORDER BY name COLLATE NOCASE')]


def find(key):
    with database() as db:
        row = db.execute('SELECT * FROM services WHERE id=?', (key,)).fetchone()
    if row is None:
        raise ValueError('등록된 업체를 찾을 수 없습니다.')
    return dict(row)


def save(value):
    with database() as db:
        db.execute('''INSERT INTO services (id,name,url,login,status,notes,updated_at)
          VALUES (:id,:name,:url,:login,:status,:notes,:updated_at)
          ON CONFLICT(id) DO UPDATE SET name=excluded.name,url=excluded.url,
          login=excluded.login,status=excluded.status,notes=excluded.notes,updated_at=excluded.updated_at''',
          {**value, 'updated_at': now()})
    return find(value['id'])
