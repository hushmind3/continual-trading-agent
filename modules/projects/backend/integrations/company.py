"""Explicit company-queue contract adapter, copied into the selected app's data."""
import asyncio
import json
import os
from pathlib import Path
import re
import shutil
from contextlib import contextmanager

def close_connections(db):
    if getattr(db.connect, '_platform_closing', False): return
    original = db.connect
    @contextmanager
    def connect():
        connection = original()
        try:
            with connection: yield connection
        finally: connection.close()
    connect._platform_closing = True
    db.connect = connect


def install(app, data_root, activity=lambda delta: None):
    import ai_provider as ai
    import database as db
    import operations as ops
    import server
    import venture_engine as ventures
    from fastapi import Header, HTTPException
    close_connections(db)
    base = Path(data_root).resolve() / 'workspaces'
    original_decide, original_process = ventures.decide, ops.process_one

    def folder(venture_id):
        if not re.fullmatch('[A-Za-z0-9_-]{1,100}', venture_id): raise ValueError('사업 ID가 올바르지 않습니다.')
        path = (base / venture_id).resolve()
        if not path.is_relative_to(base.resolve()): raise ValueError('사업 작업 경계를 벗어났습니다.')
        return path

    def enqueue(venture_id, pending=False):
        target = folder(venture_id)
        with db.LOCK, db.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row = c.execute('SELECT * FROM ventures WHERE id=?', (venture_id,)).fetchone()
            if not row or row['status'] not in (('pending',) if pending else ('approved',)):
                raise ValueError('승인 가능한 사업안이 아닙니다.')
            existing = [dict(r) for r in c.execute("SELECT * FROM jobs WHERE type='agent_task' ORDER BY rowid")
                        if json.loads(r['arguments']).get('company_flow') == venture_id]
            if existing:
                if not any(r['status'] in ('running','queued') for r in existing):
                    for row in existing:
                        if row['status']=='failed':c.execute("UPDATE jobs SET status='queued',started_at=NULL,finished_at=NULL,error='',mode='',result='' WHERE id=?",(row['id'],))
                return [r['id'] for r in existing]
            if pending: c.execute("UPDATE ventures SET status='approved',decided_at=? WHERE id=?", (db.now(), venture_id))
            target.mkdir(parents=True, exist_ok=True)
            (target / 'approved-proposal.json').write_text(row['proposal_json'], encoding='utf-8')
            jobs = []; previous = ''
            for role, phase, title in [('CPO', 'requirements', '승인 제품 요구사항 작성'), ('CTO', 'implementation', '승인 제품 로컬 MVP 제작'), ('QA', 'verification', '제작물 실제 테스트·빌드')]:
                jid = db.uid('job')
                args = {'company_flow': venture_id, 'phase': phase, 'role': role, 'depends_on': previous,
                        'brief': title, 'owner_approved': True}
                c.execute('INSERT INTO jobs(id,created_at,type,role,status,title,arguments) VALUES(?,?,?,?,?,?,?)',
                          (jid, db.now(), 'agent_task', role, 'queued', title, json.dumps(args, ensure_ascii=False)))
                jobs.append(jid); previous = jid
        return jobs

    def decide(venture_id, approval):
        if not approval: return original_decide(venture_id, approval)
        row = db.one('SELECT * FROM ventures WHERE id=?',(venture_id,))
        plan = json.loads(row['proposal_json']) if row else {}
        if plan.get('name','').strip().lower()=='dealpage' and any(word in plan.get('product','') for word in ('제안서','견적')):
            return original_decide(venture_id,approval)
        jobs = enqueue(venture_id, pending=True)
        reply = '사업안을 승인했습니다. CPO 요구사항 작성 → CTO 로컬 MVP 제작 → QA 실제 테스트·빌드를 순서대로 실행합니다. 검증 전에는 제작 완료나 서비스 공개로 표시하지 않습니다.'
        db.save_ceo_message('owner', '사업 초안 승인: ' + db.one('SELECT name FROM ventures WHERE id=?', (venture_id,))['name'])
        db.save_ceo_message('ceo', reply)
        return {'id': venture_id, 'status': 'approved', 'jobs': jobs, 'reply': reply, 'released': False, 'product_url': None}

    def claim():
        with db.LOCK, db.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            for row in c.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at,rowid").fetchall():
                args = json.loads(row['arguments'])
                if args.get('company_flow') and args.get('depends_on'):
                    previous = c.execute('SELECT status FROM jobs WHERE id=?', (args['depends_on'],)).fetchone()
                    if not previous or previous['status'] == 'failed':
                        c.execute("UPDATE jobs SET status='failed',mode='blocked',finished_at=?,error=? WHERE id=?",
                                  (db.now(), '선행 제작 단계가 실패해 실행하지 않았습니다.', row['id']))
                        continue
                    if previous['status'] != 'completed': continue
                c.execute("UPDATE jobs SET status='running',started_at=? WHERE id=?", (db.now(), row['id']))
                return dict(row)
        return None

    original_task = ops.ACTIONS['agent_task']
    async def task(args):
        if not args.get('company_flow'): return await original_task(args)
        venture_id = args['company_flow']; target = folder(venture_id); phase = args['phase']
        proposal = db.one('SELECT proposal_json FROM ventures WHERE id=?', (venture_id,))
        meeting=db.one("SELECT summary FROM ceo_meetings WHERE venture_id=? AND status='completed' ORDER BY rowid DESC LIMIT 1",(venture_id,))
        requirements = (target / 'requirements.md').read_text(encoding='utf-8') if (target / 'requirements.md').is_file() else ''
        instructions = {
            'requirements': '승인 초안으로 구현 가능한 로컬 MVP 요구사항과 인수 조건을 requirements.md 파일에 실제로 작성하세요. 제작→실제 테스트→사용자 검증 순서로 정리하고 아직 없는 제품의 무료 체험 실적을 요구하지 마세요.',
            'implementation': 'requirements.md를 읽고 이 폴더에 실제 실행 가능한 React+Vite+Tailwind MVP를 제작하세요. package.json에 build/test 스크립트, src/App.tsx, src/tailwind.css, 자동 검사를 작성하고 의존성을 이 폴더에 설치하세요. Vite base는 ./ 로 설정하세요. 계획 문서만 쓰고 완료하지 마세요.',
            'verification': '실제 제작 소스와 요구사항을 비교해 자동 테스트를 실행하고 오류를 수정하세요. npm test -- --run 및 npm run build가 성공해야 합니다. 확인하지 않은 성공·고객·매출·공개를 주장하지 마세요.'}
        system = ('당신은 승인된 로컬 제작의 ' + args['role'] + ' 담당입니다. 연결된 Hermes 파일/터미널 도구로 실제 산출물을 만드세요. '
                  '작업 폴더 안에서만 수정하세요. 다른 플랫폼 소스를 수정하거나 외부 공개·계정 생성·결제·광고·유료 서비스 호출을 하지 마세요. '
                  '도구가 실제 실패하면 오류를 그대로 보고하세요. 한국어로 결과와 생성 파일을 간결히 보고하세요.')
        token = ai.platform_request_options.set({'workspace': str(target), 'context_scope': 'native', 'execution': True})
        try:
            result = await ai.compose(system, json.dumps({'task': instructions[phase], 'approved_proposal': json.loads(proposal['proposal_json']),
                                                         'requirements': requirements, 'meeting_summary': meeting['summary'] if meeting else '', 'workspace': str(target)}, ensure_ascii=False))
        finally: ai.platform_request_options.reset(token)
        if not result: raise ValueError('실행 결과가 없습니다.')
        if phase == 'requirements' and (not (target / 'requirements.md').is_file() or (target / 'requirements.md').stat().st_size < 50):
            raise ValueError('요구사항 파일을 실제로 작성하지 않았습니다.')
        if phase == 'implementation':
            for name in ('package.json', 'src/App.tsx', 'src/tailwind.css'):
                if not (target / name).is_file(): raise ValueError('필수 제작물이 없습니다: ' + name)
            scripts = json.loads((target / 'package.json').read_text(encoding='utf-8')).get('scripts', {})
            if not all(scripts.get(key) for key in ('build', 'test')): raise ValueError('실제 build/test 실행 스크립트가 없습니다.')
        if phase == 'verification':
            node = shutil.which('node'); npm = shutil.which('npm.cmd') or shutil.which('npm')
            cli = Path(npm).parent / 'node_modules/npm/bin/npm-cli.js' if npm else None
            if not node or not cli or not cli.is_file(): raise ValueError('공유 Node/npm 실행기를 찾지 못했습니다.')
            checks = []
            for command in (['test', '--', '--run'], ['run', 'build']):
                process = await asyncio.create_subprocess_exec(node, str(cli), *command, cwd=target, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
                try: output, _ = await asyncio.wait_for(process.communicate(), 180)
                except BaseException:
                    process.kill(); await process.communicate(); raise
                checks.append({'command': 'npm ' + ' '.join(command), 'exit_code': process.returncode, 'output': output.decode('utf-8', errors='replace')[-8000:]})
                if process.returncode: raise ValueError('실제 검증 실패: ' + checks[-1]['command'] + '\n' + checks[-1]['output'])
            if not (target / 'dist/index.html').is_file(): raise ValueError('실행할 빌드 결과가 없습니다.')
            (target / 'verification.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
        return result, 'hermes'

    async def process():
        jid = await original_process()
        if not jid: return jid
        job = db.one('SELECT * FROM jobs WHERE id=?', (jid,)); args = json.loads(job['arguments'])
        if not args.get('company_flow'): return jid
        if job['status'] == 'failed':
            with db.LOCK, db.connect() as c:
                for row in c.execute("SELECT id,arguments FROM jobs WHERE status='queued'").fetchall():
                    if json.loads(row['arguments']).get('company_flow') == args['company_flow']:
                        c.execute("UPDATE jobs SET status='failed',mode='blocked',finished_at=?,error=? WHERE id=?", (db.now(), '선행 제작 단계 실패로 실행하지 않았습니다.', row['id']))
                c.execute("UPDATE jobs SET mode='incomplete' WHERE id=?", (jid,))
            db.save_ceo_message('ceo', '제작 단계가 실패해 후속 실행을 중단했습니다. ' + job['title'] + ': ' + job['error'])
        elif args['phase'] == 'verification':
            prefix='/assets/projects/'+os.environ.get('PLATFORM_PROJECT_ID','fixture')+'/_platform-output/'+args['company_flow']+'/'
            db.save_ceo_message('ceo', '로컬 MVP 제작과 실제 테스트·빌드를 완료했습니다. 외부 서비스 공개와 매출 검증은 하지 않았습니다.\n\n[로컬 원형 보기]('+prefix+'dist/index.html) · [요구사항]('+prefix+'requirements.md) · [검증 기록]('+prefix+'verification.json)')
        return jid

    async def managed_task(args):
        if not args.get('company_flow'): return await original_task(args)
        activity(1)
        try: return await task(args)
        finally: activity(-1)

    @app.post('/api/admin/ventures/{venture_id}/build')
    async def resume(venture_id: str, x_project_zero_token: str | None = Header(None)):
        server.require_admin(x_project_zero_token)
        try:
            jobs=enqueue(venture_id)
            key='company_flow_started:'+venture_id
            if not db.settings().get(key):
                with db.LOCK,db.connect() as c:c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO NOTHING',(key,'true'))
                db.save_ceo_message('ceo','승인된 사업의 제작을 이어갑니다. 앞선 도구 미지원 안내는 원본 앱의 고정 안내였습니다. 연결된 Hermes 도구로 CPO 요구사항 → CTO 로컬 MVP → QA 실제 테스트·빌드를 순서대로 진행하고 실패하면 후속 단계를 중단합니다.')
            return {'jobs':jobs,'released':False}
        except ValueError as exc: raise HTTPException(409, str(exc)) from exc

    ventures.decide = decide
    db.claim_job = claim
    ops.ACTIONS['agent_task'] = managed_task
    ops.process_one = process
