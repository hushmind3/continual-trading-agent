"""Original company UI/DB as records for native Hermes; no provider or execution loop."""
import json
from pathlib import Path
import re
from contextlib import contextmanager


def recall(db, command):
    """Search existing organization tables; no new database, index or model call."""
    query = str(command.get('query', ''))[:512].lower()
    ignored = {'이어서', '계속', '이전', '지난번', '하던거', '진행', '작업', '해줘', '해주세요', '기억', '어디까지', '다시'}
    words = [t for t in re.findall(r'[a-z0-9_가-힣]{2,}', query) if t not in ignored]
    grams = [word[i:i+3] for word in words if re.fullmatch('[가-힣]{5,}',word) for i in range(len(word)-2)]
    terms = list(dict.fromkeys(t for t in words+grams if t not in ignored))[:16]
    scope = str(command.get('venture_id') or '')
    if scope and not db.one('SELECT id FROM ventures WHERE id=?', (scope,)):
        raise ValueError('사업안을 찾을 수 없습니다.')
    job_scope = "COALESCE(NULLIF(json_extract(CASE WHEN json_valid(j.arguments) THEN j.arguments ELSE '{}' END,'$.venture_id'),''),'owner')"
    note_meta = "CASE WHEN substr(origin,1,14)='hermes-native|' AND json_valid(substr(origin,15)) THEN substr(origin,15) ELSE '{}' END"
    sources = f"""
      SELECT 'venture' kind,id,id scope,name title,proposal_json body,status,created_at FROM ventures
      UNION ALL SELECT 'job',j.id,{job_scope},j.title,COALESCE(j.error,'')||char(10)||COALESCE(j.result,''),j.status,j.created_at FROM jobs j
      UNION ALL SELECT 'meeting',id,COALESCE(NULLIF(venture_id,''),'owner'),topic,summary,status,created_at FROM ceo_meetings
      UNION ALL SELECT COALESCE(json_extract({note_meta},'$.kind'),'lesson'),id,
        COALESCE(json_extract({note_meta},'$.scope'),'unscoped'),COALESCE(json_extract({note_meta},'$.key'),role),insight,'saved',created_at FROM ceo_lessons l WHERE substr(origin,1,14)<>'hermes-native|' OR NOT EXISTS (SELECT 1 FROM ceo_lessons newer WHERE newer.origin=l.origin AND newer.rowid>l.rowid)
      UNION ALL SELECT 'experience',e.id,{job_scope},j.title,e.detail,e.outcome,e.created_at FROM ceo_experiences e JOIN jobs j ON j.id=e.job_id
    """
    def search(selected, limit=8):
        filters, params = [], []
        if selected:
            filters.append("(scope=? OR (scope='owner' AND kind IN ('decision','constraint')))"); params.append(selected)
        if terms:
            filters.append('('+' OR '.join("instr(lower(title||' '||body),?)>0" for _ in terms)+" OR kind='constraint')")
            params.extend(terms)
        else:
            filters.append("(kind IN ('decision','constraint','working','experience','venture') OR (kind='job' AND status IN ('running','queued','failed')))")
        score = '+'.join("(instr(lower(title||' '||body),?)>0)" for _ in terms) or '(0+0)'
        return db.many('WITH entries AS ('+sources+') SELECT kind,id,scope,title,status,created_at,substr(body,1,1200) body FROM entries WHERE '
                       +' AND '.join(filters)+' ORDER BY '+score+' DESC,created_at DESC,id DESC LIMIT ?', tuple(params+terms+[limit]))
    found = search(scope)
    if not scope:
        # One continuation stays in one business; organization-wide constraints still apply.
        scoped = next((r['scope'] for r in found if r['scope'] not in ('owner','unscoped') and (not terms or any(t in (r['title']+' '+r['body']).lower() for t in terms))), '')
        if scoped: scope=scoped; found=search(scope)
        else: found=[r for r in found if r['scope'] in ('owner','unscoped')]
    items, seen = [], set()
    for row in found:
        key=(row['kind'],row['scope'],row['title'])
        if row['kind'] in ('decision','constraint','lesson') and key in seen: continue
        seen.add(key)
        items.append({**row,'body':row['body'][:420]})
    result={'scope':scope or 'owner','terms':terms,'items':items,'source':'existing organization records'}
    while len(json.dumps(result,ensure_ascii=False))>4200 and result['items']: result['items'].pop()
    return result


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
        if action == 'recall': return recall(db, command)
        if action == 'remember':
            kind = command.get('kind'); body = str(command.get('body', '')).strip()
            if kind not in ('decision','constraint','experience','working') or not body or len(body)>1600:
                raise ValueError('기억 종류와 1~1600자의 구체적인 근거가 필요합니다.')
            scope = command.get('venture_id') or 'owner'
            if scope != 'owner': venture(scope)
            key = str(command.get('memory_key') or db.uid('topic'))[:80]
            origin = 'hermes-native|' + json.dumps({'kind':kind,'scope':scope,'key':key},ensure_ascii=False)
            db.record_lesson('CEO',body,origin,0)
            return {'saved':True,'scope':scope,'kind':kind,'memory_key':key}
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
            if not db.one('SELECT id FROM ceo_experiences WHERE job_id=?',(row['id'],)): db.record_experience(row['id'])
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
