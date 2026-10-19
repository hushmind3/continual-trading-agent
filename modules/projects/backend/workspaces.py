"""Explicit, installation-owned original UI tabs; no repository-name dispatch."""
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from urllib.request import urlopen
from . import store


def connect(key, config):
    from . import harness, installer, runtime
    with store.LOCK, runtime.LOCK:
        if installer.JOBS or runtime.busy_reason(): raise ValueError('실행 중인 작업이 끝난 뒤 연결하세요.')
        record = store.read(key)
        revision = str(config.get('revision', ''))
        path = PurePosixPath(str(config.get('path', '')))
        tabs = config.get('tabs', [])
        if not re.fullmatch('[a-f0-9]{40}', revision) or path.is_absolute() or '..' in path.parts or path.suffix != '.html':
            raise ValueError('고정 Git 커밋과 원본 HTML 경로가 필요합니다.')
        if not isinstance(tabs, list) or not 1 <= len(tabs) <= 8: raise ValueError('화면 탭은 1~8개입니다.')
        if any(not isinstance(t, dict) or not re.fullmatch('[a-z][a-z0-9_-]{0,40}', str(t.get('id', ''))) or not isinstance(t.get('title'), str) or not 1 <= len(t['title']) <= 40 for t in tabs):
            raise ValueError('탭 ID와 제목을 확인하세요.')
        if len({t['id'] for t in tabs}) != len(tabs): raise ValueError('중복 탭 ID입니다.')
        navigation = str(config.get('navigation', ''))
        if navigation != 'data-tab': raise ValueError('원본 data-tab 화면 전환 규격을 확인하세요.')
        url = f'https://raw.githubusercontent.com/{record["repository"]}/{revision}/{path}'
        with urlopen(url, timeout=20) as response: content = response.read(2 * 1024 * 1024 + 1)
        if len(content) > 2 * 1024 * 1024: raise ValueError('원본 화면 크기가 너무 큽니다.')
        text = content.decode('utf-8')
        if '<html' not in text.lower(): raise ValueError('HTML 화면이 아닙니다.')
        target = store.owned(store.project_folder(record), 'integrations/hermes/owner.html')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        harness.configure(record, True)
        record['workspace_ui'] = {'host': 'hermes/chat', 'document': 'integrations/hermes/owner.html',
            'revision': revision, 'url': url, 'sha256': hashlib.sha256(content).hexdigest(), 'tabs': tabs,
            'navigation': navigation}
        worker = runtime.WORKERS.pop(key, None)
        if worker: worker.close()
        store.save(record)
        return {'id': key, 'revision': revision, 'tabs': tabs, 'shared_settings': 'hermes'}


def tabs():
    result = []
    for record in store.records():
        ui = record.get('workspace_ui', {})
        if record.get('stage') != 'ready' or ui.get('host') != 'hermes/chat': continue
        if not store.owned(store.project_folder(record), ui.get('document', '')).is_file(): continue
        result.extend({'id': record['id'] + ':' + t['id'], 'view': t['id'], 'title': t['title'],
            'src': '/assets/projects/' + record['id'] + '/_platform-workspace.html', 'revision': ui['revision']}
            for t in ui.get('tabs', []))
    return {'items': result}


def document(record):
    ui = record.get('workspace_ui', {})
    if ui.get('host') != 'hermes/chat': raise ValueError('연결된 화면이 없습니다.')
    content = store.owned(store.project_folder(record), ui['document']).read_bytes()
    if hashlib.sha256(content).hexdigest() != ui['sha256']: raise ValueError('원본 화면 무결성 확인 실패')
    config = json.dumps({'navigation': ui['navigation'], 'views': [t['id'] for t in ui['tabs']]}, ensure_ascii=False).replace('<', '\\u003c')
    script = Path(__file__).with_name('workspace_embed.js').read_text(encoding='utf-8')
    return content.decode('utf-8').replace('</body>', '<script>window.platformWorkspace=' + config + ';' + script + '</script></body>')
