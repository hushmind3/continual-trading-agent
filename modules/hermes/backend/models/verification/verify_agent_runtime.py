"""Exercise the production agent with a scoped fixture; archive its test conversations."""
import json
from pathlib import Path
import tempfile
import time
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[5]
OUTPUT=ROOT/'runtime/ai_agent/Hermes/verification/performance'
def api(operation,payload=None):
    request=urllib.request.Request('http://127.0.0.1:8766/api',data=json.dumps({'operation':'ai_agent/Hermes/'+operation,'payload':payload or {}}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)

def task(prompt,workspace):
    started=time.monotonic()
    state=api('chat',{'message':prompt,'workspace':str(workspace),'read_only':False})
    session=state['job']['session_id'];deadline=started+90
    try:
        while time.monotonic()<deadline:
            state=api('status');job=state['job']
            if job.get('session_id')!=session:raise RuntimeError('Test no longer owns the active job')
            if job.get('approval'):
                approval=job['approval'];detail=approval['detail'].replace('\\\\','/').replace('\\','/')
                api('answer',{'allow':approval['kind']=='tool' and str(workspace).replace('\\','/') in detail})
            if job['state'] not in ('starting','running','stopping'):
                if job['state']!='complete':raise RuntimeError(job.get('error') or job['state'])
                return {'seconds':round(time.monotonic()-started,3),'metrics':job.get('metrics'),
                        'tools':[e['detail'][:220] for e in job.get('events',[]) if e['name']=='tool_start']}
            time.sleep(.25)
        raise RuntimeError('Scoped agent check timed out')
    finally:
        state=api('status')
        if state['job'].get('session_id')==session and state['job']['state'] in ('starting','running','stopping'):
            api('stop')
            for _ in range(60):
                if api('status')['job']['state'] not in ('starting','running','stopping'):break
                time.sleep(.25)
        api('session/archive',{'id':session})

def main():
    state=api('status')
    if state['job']['state'] in ('starting','running','stopping'):raise RuntimeError('Hermes is busy')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    report={}
    with tempfile.TemporaryDirectory(dir=OUTPUT) as temporary:
        folder=Path(temporary)
        report['chat']=task('1부터 80까지 쉼표로 구분해서 한 줄로 쓰고 끝내. 도구는 쓸 필요 없어.',ROOT)
        nonce='HERMES_'+uuid.uuid4().hex
        (folder/'input.txt').write_text(nonce,encoding='utf8')
        report['file_task']=task('작업 폴더의 input.txt를 도구로 읽어서 내용을 그대로 copied.txt에 저장해. 필요한 도구는 검색해서 사용하고, 저장 결과를 확인한 뒤 짧게 답해.',folder)
        target=folder/'copied.txt'
        report['file_task']['exact_copy']=target.is_file() and target.read_text(encoding='utf8').strip()==nonce
        (OUTPUT/'agent-after-fix.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(report,ensure_ascii=False),flush=True)
        if not report['file_task']['exact_copy']:raise RuntimeError('Agent did not copy the unknown fixture contents')

if __name__=='__main__':main()
