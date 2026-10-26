"""Real local-model -> installed MCP -> evidence, with a disposable target."""
import json
import argparse
from pathlib import Path
import tempfile
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'runtime/projects/manage/verification'
OUTPUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser(description='Explicit opt-in for actual local-model integration verification')
parser.add_argument('--allow-local-model', action='store_true')
if not parser.parse_args().allow_local_model:
    parser.error('실제 로컬 모델을 실행합니다. 사용자가 명시적으로 검사를 요청한 경우에만 --allow-local-model을 사용하세요.')
STARTED = time.time()


def release_target(folder):
    """Close only test-created worker descendants holding the disposable cwd on Windows."""
    import psutil
    worker = str(ROOT / 'backend/ai_agent/choki/engine/worker.py').replace('\\', '/').lower()
    for process in psutil.process_iter(['cwd', 'create_time']):
        try:
            if process.info['create_time'] < STARTED or not process.info['cwd'] or Path(process.info['cwd']).resolve() != folder.resolve(): continue
            owned = any(any(argument.replace('\\', '/').lower() == worker for argument in parent.cmdline()) for parent in process.parents())
            if not owned: continue
            process.terminate()
            try: process.wait(timeout=5)
            except psutil.TimeoutExpired: process.kill(); process.wait(timeout=5)
        except (psutil.Error, OSError): pass


def api(operation, payload=None):
    request = Request('http://127.0.0.1:8766/api', data=json.dumps({'operation': operation, 'payload': payload or {}}).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=240) as response: return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(exc.read().decode('utf8', errors='replace')[:2000]) from exc


with tempfile.TemporaryDirectory(prefix='agent-target-', dir=OUTPUT) as temporary:
    folder = Path(temporary)
    (folder / 'package.json').write_text('{"name":"agent-verification","type":"module"}')
    (folder / 'main.js').write_text('export function sumNumbers(a,b){return a+b;}\n')
    result = api('projects/agent/start', {'id': 'p_morluto_rea_a5b6cf30', 'target': str(folder),
        'message': '이 JavaScript 프로젝트를 설치된 REA의 실제 분석 도구로 분석하고, 발견한 함수 이름과 파일 이름을 한국어로 알려줘. 소스는 수정하지 마. 도구 결과를 확인한 뒤 짧게 답해.'})
    session = result['session_id']; deadline = time.monotonic() + 480
    print(json.dumps({'session_id': session, 'connected_tools': result['connection']['tools']}), flush=True)
    try:
        while time.monotonic() < deadline:
            job = api('ai_agent/choki/status')['job']
            if job['session_id'] != session: raise RuntimeError('The verification session was replaced')
            if job['state'] not in ('starting', 'running', 'stopping'): break
            time.sleep(2)
        else:
            api('ai_agent/choki/stop'); raise TimeoutError('Agent verification exceeded 480 seconds')
        (OUTPUT / 'agent-workflow.json').write_text(json.dumps(job, ensure_ascii=False), encoding='utf8')
        assert job['state'] == 'complete', job.get('error')
        calls = [json.loads(event['detail'])[1] for event in job.get('events', []) if event.get('name') == 'tool_start']
        assert any('analyze_javascript_application' in name for name in calls), 'Agent did not execute the installed analysis tool'
        assert 'sumNumbers' in job.get('text', ''), 'Agent did not report the function from actual analysis'
        assert (folder / 'main.js').read_text() == 'export function sumNumbers(a,b){return a+b;}\n'
        print(json.dumps({'state': job['state'], 'text': job.get('text', '')[-1400:],
            'tools_executed': calls}, ensure_ascii=False), flush=True)
    finally:
        status = api('ai_agent/choki/status')['job']
        if status.get('session_id') == session and status.get('state') in ('starting', 'running', 'stopping'):
            api('ai_agent/choki/stop')
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and api('ai_agent/choki/status')['job'].get('state') in ('starting', 'running', 'stopping'):
                time.sleep(1)
        release_target(folder)
