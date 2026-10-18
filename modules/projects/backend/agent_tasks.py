"""Generic installed-project -> agent adapter; no per-repository UI integration."""
from pathlib import Path
import threading
from . import node_mcp, store


def link(record, remove=False):
    if record.get('adapter', {}).get('kind') != 'node-mcp' and not (remove and record.get('detected') == 'node-mcp'): return None
    from ai_agent.Hermes.engine.bridge import bridge
    payload = {'id': record['id'], 'remove': remove}
    if not remove:
        source = store.owned(store.project_folder(record), str(Path(record['active_source']).relative_to(store.project_folder(record))))
        command = node_mcp.command(source, record['adapter'])
        payload['server'] = {'command': command[0], 'args': command[1:], 'env': record.get('environment', {})}
    return bridge.call('mcp/project', payload, timeout=90)


def start(request):
    from ai_agent.Hermes.engine.bridge import bridge
    from .agent_setup import ensure_ready
    record = store.read(request.get('id', ''))
    if record['stage'] != 'ready': raise ValueError('설치와 연결이 완료된 프로젝트를 선택하세요.')
    if record.get('adapter', {}).get('kind') != 'node-mcp': raise ValueError('이 프로젝트는 원본 실행 화면에서 사용하세요.')
    message = str(request.get('message') or '').strip()
    target = str(request.get('target') or '').strip()
    if not message or len(message) > 16000: raise ValueError('작업 요청을 입력하세요. 최대 16,000자입니다.')
    workspace = Path(target).expanduser().resolve() if target else None
    if workspace and not workspace.exists(): raise ValueError('분석할 파일·폴더가 존재하지 않습니다.')
    connection = link(record)
    ensure_ready(bridge, threading.Event(), lambda *args, **kwargs: None)
    import re
    words = set(re.findall('[a-z]{3,}', (message + ' ' + target).lower()))
    names = connection.get('tool_names', [])
    ranked = sorted(names, key=lambda name: -sum(word in name.lower() for word in words))
    hints = '\n'.join(ranked[:24])
    prompt = (
        f'Use the installed project {record["repository"]} for this user task. '
        f'Its MCP server {connection["name"]} is connected. Discover its relevant tools with tool_search and tool_describe, then execute them. '
        'Do not claim analysis succeeded without actual tool results. Use the installed tools rather than replacing them with shell commands. '
        'The following are real tools already discovered for this project. Choose an exact relevant name as a single tool_search query, then tool_describe and execute it. Avoid broad multi-query searches.\n'
        f'{hints}\n'
        'Respond in Korean, explain evidence and limitations, and include clickable exact local paths for any report. '
        'Do not modify the analysis target unless the user explicitly requests changes. '
        f'User target: {target or "not specified"}\nUser request: {message}'
    )
    payload = {'message': prompt, 'read_only': False}
    if workspace: payload['workspace'] = str(workspace if workspace.is_dir() else workspace.parent)
    result = bridge.call('chat', payload)
    return {'session_id': result['job']['session_id'], 'connection': connection}


def link_when_idle(record, cancelled, progress, timeout=600):
    from ai_agent.Hermes.engine.bridge import bridge
    import time
    deadline = time.monotonic() + timeout
    while bridge.busy_reason():
        if cancelled.is_set(): raise ValueError('설치를 취소했습니다.')
        if time.monotonic() > deadline: raise ValueError('기존 에이전트 작업이 끝나지 않아 연결을 보류했습니다. 설치 파일은 보존합니다.')
        progress('agent_link', '기존 에이전트 작업이 끝나면 자동 연결합니다. 설치 취소도 가능합니다.')
        cancelled.wait(1)
    if cancelled.is_set(): raise ValueError('설치를 취소했습니다.')
    return link(record)
