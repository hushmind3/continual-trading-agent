"""Interpret local document references without searching unrelated directories."""
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


def document_file(path, root):
    raw = unquote(str(path)).strip().strip('`"')
    if raw.startswith(('\\\\', '//')):
        raise ValueError('네트워크 경로는 문서 미리보기 대상이 아닙니다.')
    if raw.startswith('file:'):
        uri = urlsplit(raw)
        if uri.netloc and uri.netloc != 'localhost':
            raise ValueError('로컬 문서만 열 수 있습니다.')
        raw = uri.path
        if len(raw) > 2 and raw[0] == '/' and raw[2] == ':':
            raw = raw[1:]
    if os.name == 'nt':
        raw = re.sub(r'^/([a-zA-Z])/', lambda match: match[1] + ':/', raw)
    raw = re.sub(r'#L?\d+(?:-L?\d+)?$', '', raw)
    raw = re.sub(r'(\.[a-zA-Z0-9]+):\d+(?::\d+)?$', r'\1', raw)

    def resolve(value):
        file = Path(value).expanduser()
        return (file if file.is_absolute() else root / file).resolve()

    file = resolve(raw)
    # Prefer a literal existing filename; otherwise recognize Git porcelain status.
    if not file.is_file() and (match := re.fullmatch(r'[ MARCUD?!]{1,2}\s+(.+)', raw)):
        file = resolve(match[1].strip('"'))
    return file
