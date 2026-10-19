"""App-owned reviewed execution plans; approval and dependent native jobs share one DB."""
import json

PHASES={'requirements':'CPO','design':'CTO','implementation':'CTO','verification':'QA','research':None}
ROLES={'CPO','CTO','CMO','CFO','CS','QA'}

def initialize(db):
    with db.LOCK,db.connect() as con:
        con.execute("CREATE TABLE IF NOT EXISTS platform_meeting_plans (meeting_id TEXT PRIMARY KEY, status TEXT NOT NULL, summary TEXT NOT NULL, tasks_json TEXT NOT NULL, jobs_json TEXT NOT NULL DEFAULT '[]', report_message_id TEXT NOT NULL DEFAULT '')")

        columns={row['name'] for row in con.execute('PRAGMA table_info(platform_meeting_plans)').fetchall()}
        if 'report_message_id' not in columns:con.execute("ALTER TABLE platform_meeting_plans ADD COLUMN report_message_id TEXT NOT NULL DEFAULT ''")

def attach_report(db,mid,message_id):
    with db.LOCK,db.connect() as con:
        con.execute('UPDATE platform_meeting_plans SET report_message_id=? WHERE meeting_id=?',(message_id,mid))

def parse(raw):
    value=json.loads(raw)
    summary=value.get('summary');tasks=value.get('tasks')
    if not isinstance(summary,str) or not 1<=len(summary.strip())<=1200:raise ValueError('CEO 실행안 요약을 확인하세요.')
    if not isinstance(tasks,list) or not 1<=len(tasks)<=8:raise ValueError('승인할 구체적인 업무가 없습니다.')
    clean=[];seen=set()
    for task in tasks:
        phase=task.get('phase');role=task.get('role')
        if phase not in PHASES or role not in ROLES or PHASES[phase] and PHASES[phase]!=role:
            raise ValueError('업무 단계와 담당 역할이 일치하지 않습니다.')
        if phase=='research' and role not in {'CMO','CFO','CS'}:raise ValueError('시장·비용·고객 조사의 담당을 확인하세요.')
        fields={}
        for key in ('title','brief','deliverable','acceptance'):
            text=task.get(key)
            if not isinstance(text,str) or not 1<=len(text.strip())<=(160 if key=='title' else 1800):raise ValueError('업무의 산출물·완료 기준이 없습니다.')
            fields[key]=text.strip()
        if phase=='implementation' and not {'requirements','design'}<=seen:raise ValueError('제작 전에 기획·설계가 필요합니다.')
        if phase=='verification' and 'implementation' not in seen:raise ValueError('제작 결과 없이 검증할 수 없습니다.')
        seen.add(phase);clean.append({'phase':phase,'role':role,**fields})
    if 'implementation' in seen and 'verification' not in seen:raise ValueError('제작 업무에는 QA 검증이 필요합니다.')
    return summary.strip(),clean

def save(db,mid,summary,tasks):
    with db.LOCK,db.connect() as con:
        con.execute("INSERT INTO platform_meeting_plans(meeting_id,status,summary,tasks_json) VALUES(?,?,?,?)",(mid,'pending',summary,json.dumps(tasks,ensure_ascii=False)))

def latest(db):
    rows=db.many('SELECT * FROM platform_meeting_plans ORDER BY rowid DESC LIMIT 20')
    for row in rows:
        row['tasks']=json.loads(row.pop('tasks_json'));row['jobs']=json.loads(row.pop('jobs_json'))
        for job in row['jobs']:
            current=db.one('SELECT status,error FROM jobs WHERE id=?',(job['id'],))
            job.update(current or {'status':'missing','error':'업무 기록이 없습니다.'})
    return rows

def decide(db,mid,approve):
    if type(approve) is not bool:raise ValueError('승인 여부는 참/거짓이어야 합니다.')
    with db.LOCK,db.connect() as con:
        con.execute('BEGIN IMMEDIATE')
        row=con.execute('SELECT * FROM platform_meeting_plans WHERE meeting_id=?',(mid,)).fetchone()
        if not row or row['status']!='pending':raise ValueError('승인 대기 중인 실행안이 아닙니다.')
        meeting=con.execute('SELECT status FROM ceo_meetings WHERE id=?',(mid,)).fetchone()
        if not meeting or meeting['status']!='completed':raise ValueError('완료된 회의의 실행안만 승인할 수 있습니다.')
        jobs=[]
        if approve:
            for index,task in enumerate(json.loads(row['tasks_json'])):
                jid=db.uid('job');brief=(task['brief']+'\n산출물: '+task['deliverable']+'\n완료 기준: '+task['acceptance']+
                    '\n이 승인 범위 안에서 실제 도구로 작업하고 결과 파일 경로와 검증 근거를 보고하세요. 별도 지출·외부 공개·메일은 추가 승인 전 실행하지 마세요.')
                args={'brief':brief,'role':task['role'],'owner_instruction':row['summary'],'owner_approved':True,'meeting_plan_id':mid}
                con.execute('INSERT INTO jobs(id,created_at,type,role,status,title,arguments) VALUES(?,?,?,?,?,?,?)',
                            (jid,db.now(),'agent_task',task['role'],'queued' if index==0 else 'blocked',task['title'],json.dumps(args,ensure_ascii=False)))
                jobs.append({'id':jid,'role':task['role'],'title':task['title']})
        status='approved' if approve else 'rejected'
        con.execute('UPDATE platform_meeting_plans SET status=?,jobs_json=? WHERE meeting_id=?',(status,json.dumps(jobs,ensure_ascii=False),mid))
    db.save_ceo_message('owner',('실행안 승인: ' if approve else '실행안 보류: ')+row['summary'].splitlines()[0])
    db.save_ceo_message('ceo','승인된 업무 '+str(len(jobs))+'개를 순서대로 실행합니다. 선행 업무가 실패하면 후속 실행을 멈춥니다.' if approve else '실행안을 보류했습니다. 업무를 실행하지 않았습니다.')
    return {'status':status,'jobs':jobs}

def advance(db):
    """Original worker calls this before claiming each job; never add a second worker."""
    notices=[]
    with db.LOCK,db.connect() as con:
        for row in con.execute("SELECT * FROM platform_meeting_plans WHERE status='approved'").fetchall():
            ids=json.loads(row['jobs_json']);records=[con.execute('SELECT * FROM jobs WHERE id=?',(j['id'],)).fetchone() for j in ids]
            failed=any(not j or j['status']=='failed' for j in records)
            if failed:
                for j in records:
                    if j and j['status'] in ('blocked','queued'):
                        con.execute("UPDATE jobs SET status='failed',error=?,finished_at=? WHERE id=?",('선행 업무 실패로 실행하지 않았습니다.',db.now(),j['id']))
                con.execute("UPDATE platform_meeting_plans SET status='failed' WHERE meeting_id=?",(row['meeting_id'],))
                notices.append('승인된 실행안의 선행 업무가 실패했습니다. 후속 실행은 중단했습니다. 업무 화면에서 실제 오류를 확인하세요.')
            elif records and all(j['status']=='completed' for j in records):
                con.execute("UPDATE platform_meeting_plans SET status='completed' WHERE meeting_id=?",(row['meeting_id'],))
                notices.append('승인된 실행안의 직원 업무·검증이 끝났습니다. 업무 결과에 실제 산출물과 검증 기록이 있습니다. 매출·외부 배포 성공을 뜻하지 않습니다.')
            else:
                for index,j in enumerate(records):
                    if j['status']=='blocked' and all(prev['status']=='completed' for prev in records[:index]):
                        args=json.loads(j['arguments']);inputs='\n\n선행 담당자의 실제 결과:\n'+'\n'.join(prev['role']+': '+(prev['result'] or '')[:6000] for prev in records[:index])
                        args['brief']+=inputs
                        con.execute("UPDATE jobs SET status='queued',arguments=? WHERE id=?",(json.dumps(args,ensure_ascii=False),j['id']))
                        break
    for text in notices:db.save_ceo_message('ceo',text)
