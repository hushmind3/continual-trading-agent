"""Original company UI/DB as records for native Hermes; no provider or execution loop."""
import json
from pathlib import Path
import re
from contextlib import contextmanager


def install(app, data_root, activity=lambda delta: None):
    import database as db
    import server
    import operations as ops
    import ai_provider as ai
    from fastapi import Header, HTTPException
    if not getattr(db.connect, '_platform_closing', False):
        original = db.connect
        @contextmanager
        def connect():
            connection = original()
            try:
                with connection: yield connection
            finally: connection.close()
        connect._platform_closing = True
        db.connect = connect

    base = Path(data_root).resolve() / 'workspaces'
    base.mkdir(parents=True, exist_ok=True)
    roles = {'CEO', 'CPO', 'CTO', 'CMO', 'CFO', 'CS', 'QA'}
    async def retired_loop(shutdown):
        await shutdown.wait()
    async def retired_provider(*args, **kwargs):
        raise RuntimeError('회사 대화와 실행은 연결된 Hermes 영구 세션을 사용하세요.')
    async def native_status():
        return {'mode': 'platform', 'name': 'Hermes 공유 모델', 'endpoint': ''}
    ops.worker_loop = retired_loop
    ai.compose = retired_provider
    ai.status = native_status

    def venture(key):
        if not re.fullmatch('[A-Za-z0-9_-]{1,100}', str(key)): raise ValueError('사업 ID를 확인하세요.')
        row = db.one('SELECT * FROM ventures WHERE id=?', (key,))
        if not row: raise ValueError('사업안을 찾을 수 없습니다.')
        return row

    def records(command, owner=False):
        action = command.get('action', 'overview')
        if action == 'run_start':
            key = db.uid('job')
            with db.LOCK, db.connect() as c:
                c.execute('INSERT INTO jobs(id,created_at,started_at,type,role,status,title,arguments,mode) VALUES(?,?,?,?,?,?,?,?,?)',
                          (key, db.now(), db.now(), 'agent_task', 'CEO', 'running', str(command.get('body', ''))[:100], json.dumps({'native_session': command.get('_session')}, ensure_ascii=False), 'hermes-native'))
            return {'job_id': key}
        if action == 'run_finish':
            row = db.one('SELECT * FROM jobs WHERE id=?', (str(command.get('job_id', '')),))
            if not row or json.loads(row['arguments']).get('native_session') != command.get('_session'):
                raise ValueError('총괄 실행 소유권이 다릅니다.')
            error = command.get('error') or ('' if command.get('state') == 'complete' else '총괄 실행 '+str(command.get('state'))+'; 결과를 재확인해야 합니다.')
            db.finish_job(row['id'], command.get('body', ''), mode='hermes-native', error=error)
            # Interrupted/unfinished employee records must not remain falsely running.
            for task in db.many("SELECT * FROM jobs WHERE status='running' AND mode='hermes-native'"):
                if json.loads(task['arguments']).get('native_session') == command.get('_session'):
                    db.finish_job(task['id'], task.get('result', ''), mode='incomplete', error='총괄 실행이 종료됐지만 담당 업무의 최종 결과가 기록되지 않았습니다.')
            return {'job_id': row['id'], 'state': command.get('state'), 'error': error}
        if action == 'overview':
            # A status query must not stuff every historical report into the model prompt.
            result = {'ventures': db.many('SELECT id,name,status,substr(proposal_json,1,4000) AS proposal_json FROM ventures ORDER BY rowid DESC LIMIT 8'),
                    'jobs': db.many('SELECT id,role,title,status,mode,substr(error,1,1000) AS error,substr(result,1,600) AS summary FROM jobs ORDER BY rowid DESC LIMIT 12'),
                    'meetings': db.many('SELECT id,topic,status,substr(summary,1,1200) AS summary FROM ceo_meetings ORDER BY rowid DESC LIMIT 4'),
                    'workspace': str(base),
                    'execution': 'native Hermes session; no separate model or fixed employee pipeline'}
            if command.get('venture_id'): result['selected_venture'] = venture(command['venture_id'])
            return result
        if action == 'propose':
            title = str(command.get('title', '')).strip(); proposal = command.get('proposal')
            if not title or not isinstance(proposal, dict) or not proposal: raise ValueError('구체적인 사업 이름과 제안이 필요합니다.')
            key = db.uid('venture')
            with db.LOCK, db.connect() as c:
                c.execute('INSERT INTO ventures(id,created_at,name,proposal_json,status,mode) VALUES(?,?,?,?,?,?)',
                          (key, db.now(), title[:200], json.dumps(proposal, ensure_ascii=False), 'pending', 'hermes'))
            return {'venture_id': key, 'status': 'pending', 'instruction': 'Owner approval is required before implementation.'}
        if action == 'decision':
            if not owner or type(command.get('approve')) is not bool: raise ValueError('소유자 승인 경로만 사용할 수 있습니다.')
            row = venture(command.get('venture_id'))
            status = 'approved' if command['approve'] else 'rejected'
            with db.LOCK, db.connect() as c:
                c.execute('UPDATE ventures SET status=?,decided_at=? WHERE id=?', (status, db.now(), row['id']))
            return {'venture_id': row['id'], 'status': status, 'name': row['name'], 'proposal': json.loads(row['proposal_json'])}
        if action == 'begin':
            key = command.get('venture_id')
            row = venture(key) if key else None
            if row and row['status'] != 'approved': raise ValueError('승인된 사업의 작업만 시작할 수 있습니다.')
            role, title = command.get('role'), str(command.get('title', '')).strip()
            if role not in roles or not title: raise ValueError('담당 역할과 실제 작업 제목이 필요합니다.')
            scope = row['id'] if row else 'owner-tasks'
            target = base / scope; target.mkdir(exist_ok=True)
            # Native tasks start running immediately; the old app scheduler never claims them.
            with db.LOCK, db.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                arguments = json.dumps({'venture_id': key or '', 'native_session': command.get('_session')}, ensure_ascii=False)
                old = c.execute("SELECT id FROM jobs WHERE mode='hermes-native' AND status='running' AND role=? AND title=? AND arguments=?", (role, title, arguments)).fetchone()
                key = old['id'] if old else db.uid('job')
                if not old:
                    c.execute('INSERT INTO jobs(id,created_at,started_at,type,role,status,title,arguments,mode) VALUES(?,?,?,?,?,?,?,?,?)',
                              (key, db.now(), db.now(), 'agent_task', role, 'running', title, arguments, 'hermes-native'))
            return {'job_id': key, 'workspace': str(target), 'role': role, 'instruction': 'Use native Hermes tools to do this task; this call only records the assignment.'}
        if action == 'finish':
            row = db.one('SELECT * FROM jobs WHERE id=?', (str(command.get('job_id', '')),))
            if not row or row['mode'] != 'hermes-native': raise ValueError('현재 Hermes 업무가 아닙니다.')
            result, error = str(command.get('body', '')).strip(), str(command.get('error', '')).strip()
            if not result and not error: raise ValueError('실제 산출물·검증 근거나 실패 원인을 남기세요.')
            db.finish_job(row['id'], result, mode='hermes-native', error=error)
            return {'job_id': row['id'], 'status': 'failed' if error else 'completed', 'result': result, 'error': error}
        if action == 'meeting':
            key = db.uid('meeting'); minutes = command.get('minutes', [])
            if not isinstance(minutes, list) or not command.get('body'): raise ValueError('회의 의견과 요약이 필요합니다.')
            with db.LOCK, db.connect() as c:
                c.execute('INSERT INTO ceo_meetings(id,created_at,topic,venture_id,status,minutes_json,summary) VALUES(?,?,?,?,?,?,?)',
                          (key, db.now(), str(command.get('title', '팀 논의')), str(command.get('venture_id', '')), 'completed', json.dumps(minutes, ensure_ascii=False), command['body']))
            return {'meeting_id': key, 'summary': command['body']}
        raise ValueError('지원하지 않는 회사 기록 요청입니다.')

    @app.post('/api/admin/hermes/records')
    async def endpoint(command: dict, x_project_zero_token: str | None = Header(None)):
        server.require_admin(x_project_zero_token)
        try: return records(command, owner=command.get('_owner') is True)
        except ValueError as exc: raise HTTPException(409, str(exc)) from exc

    # The pinned company UI navigates into Hermes. Retire its second CEO planner.
    for route in list(app.routes):
        if getattr(route, 'path', '').startswith('/api/admin/ceo/chat'):
            app.routes.remove(route)
