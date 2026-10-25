"""Use the installed official tools' JSON commands, without another usage DB."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from platform_modules import ROOT

_lock = threading.Lock()
_cached = None
_cached_at = 0.0

def installed_engine():
    home = Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')
    candidates = []
    for file in (home / 'plugins/cache').glob('*/token-optimizer/*/skills/token-optimizer/scripts/measure.py'):
        manifest = file.parents[3] / '.codex-plugin/plugin.json'
        if manifest.is_file():
            version = json.loads(manifest.read_text(encoding='utf8')).get('version', '')
            if version and all(part.isdigit() for part in version.split('.')):
                candidates.append((tuple(map(int, version.split('.'))), file, version))
    if not candidates:
        raise RuntimeError('Token Optimizer가 설치되어 있지 않습니다. Codex 플러그인 설치를 확인하세요.')
    _, file, version = max(candidates)
    return file, version

def run_json(command):
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf8',
            env={**os.environ, 'TOKEN_OPTIMIZER_RUNTIME': 'codex', 'PYTHONUTF8': '1'}, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('토큰 기록 집계 시간이 초과됐습니다. 잠시 뒤 새로고침하세요.') from exc
    if result.returncode:
        raise RuntimeError('설치된 토큰 도구의 집계 명령이 실패했습니다. 도구 연결을 확인하세요.')
    try:
        value = json.loads(result.stdout)
    except ValueError as exc:
        raise RuntimeError('토큰 도구가 유효한 JSON 집계를 반환하지 않았습니다.') from exc
    if not isinstance(value, dict):
        raise RuntimeError('토큰 도구의 집계 형식이 바뀌었습니다.')
    return value

def snapshot(refresh=False):
    global _cached, _cached_at
    with _lock:
        if _cached is not None and not refresh and time.monotonic() - _cached_at < 60:
            return _cached
        script, version = installed_engine()
        command = [sys.executable, str(script)]
        usage = run_json([*command, 'trends', '--days', '7', '--json'])
        quick = run_json([*command, 'quick', '--json'])
        rtk_path = shutil.which('rtk')
        rtk = {'available': False, 'summary': None, 'error': None}
        if rtk_path:
            try:
                summary = run_json([rtk_path, 'gain', '--format', 'json']).get('summary', {})
                rtk = {'available': True, 'summary': {key: summary.get(key) for key in
                    ('total_commands', 'total_input', 'total_output', 'total_saved', 'avg_savings_pct')}, 'error': None}
            except (OSError, RuntimeError) as exc:
                rtk['error'] = str(exc)
        keys = ('period_days', 'session_count', 'total_input_tokens', 'total_output_tokens',
                'total_fresh_input', 'total_cache_read', 'total_cache_create', 'total_messages',
                'total_cost_usd', 'cost_coverage_pct')
        _cached = {'collected_at': datetime.now(timezone.utc).isoformat(), 'version': version,
            'usage': {key: usage.get(key) for key in keys},
            'startup': {key: quick.get(key) for key in ('overhead_tokens', 'overhead_pct')},
            'daily': [{key: day.get(key) for key in ('date', 'sessions', 'total_input', 'total_output')}
                      for day in usage.get('daily', [])], 'rtk': rtk}
        _cached_at = time.monotonic()
        return _cached
