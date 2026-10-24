"""Report saved authentication metadata, never read or export cookie values."""
from contextlib import closing
import json
import sqlite3
import time
from . import providers


def status(location, engine):
    definitions = providers.accounts()
    states = {item['id']: 'unsupported' if engine != 'chromium' else 'missing' for item in definitions}
    if engine == 'chromium':
        folder = 'Default'
        try:
            folder = json.loads((location / 'Local State').read_text()).get('profile', {}).get('last_used', folder)
        except (OSError, ValueError):
            pass
        if not isinstance(folder, str) or not folder or '/' in folder or '\\' in folder or folder in ('.', '..'):
            folder = 'Default'
        root = location / folder
        database = next((p for p in (root / 'Network/Cookies', root / 'Cookies') if p.is_file()), None)
        if database:
            try:
                # Read the live WAL through SQLite. Do not copy, decrypt or select token columns.
                with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True, timeout=.2)) as db:
                    expires = int((time.time() + 11644473600) * 1_000_000)
                    for item in definitions:
                        names = sorted({name for group in item['cookie_groups'] for name in group})
                        domains = item['cookie_domains']
                        query = ('SELECT DISTINCT name FROM cookies WHERE host_key IN (' + ','.join('?' for _ in domains)
                                 + ') AND name IN (' + ','.join('?' for _ in names)
                                 + ') AND (expires_utc=0 OR expires_utc>?)'
                                 + ' AND (length(encrypted_value)>0 OR length(value)>0)')
                        saved = {row[0] for row in db.execute(query, [*domains, *names, expires])}
                        states[item['id']] = 'saved' if any(set(group) <= saved for group in item['cookie_groups']) else 'missing'
            except sqlite3.Error:
                states = {item['id']: 'unknown' for item in definitions}
    return [{'id': item['id'], 'name': item['name'], 'description': item['description'],
             'state': states[item['id']]} for item in definitions]
