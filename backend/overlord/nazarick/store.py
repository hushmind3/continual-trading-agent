"""Menu-owned connection definitions and factual execution history."""
from contextlib import contextmanager
import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4
from platform_modules import ROOT

STATE = ROOT / 'runtime/overlord/nazarick'


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def database():
    STATE.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(STATE / 'foundation.sqlite3', timeout=15)
    db.row_factory = sqlite3.Row
    try:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS connections (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
                adapter TEXT NOT NULL, target TEXT NOT NULL, notes TEXT NOT NULL,
                status TEXT NOT NULL, checked_at TEXT, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS activity (
                id TEXT PRIMARY KEY, connection_id TEXT, name TEXT NOT NULL,
                action TEXT NOT NULL, status TEXT NOT NULL, detail TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        ''')
        with db:
            yield db
    finally:
        db.close()


def event(db, connection, action, status, detail):
    db.execute('INSERT INTO activity VALUES (?,?,?,?,?,?,?)', (
        uuid4().hex, connection['id'], connection['name'], action, status,
        json.dumps(detail, ensure_ascii=False), now()))


def connections():
    with database() as db:
        return [dict(row) for row in db.execute('SELECT * FROM connections ORDER BY created_at DESC, id')]


def activity():
    with database() as db:
        rows = [dict(row) for row in db.execute('SELECT * FROM activity ORDER BY created_at DESC, id LIMIT 100')]
    for row in rows:
        row['detail'] = json.loads(row['detail'])
    return rows
