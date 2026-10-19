"""Native Hermes wire verification with a local fake API, not the user's model."""
import json,os,sys,tempfile,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'modules/hermes/backend/engine/upstream')]
from platform_modules import mount_namespaces
mount_namespaces()
from ai_agent.Hermes.engine.runtime_policy import bind_discussion_context,apply_response_contract
requests=[]
class API(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
        self.wfile.write(json.dumps({'data':[{'id':'context-probe','object':'model'}]}).encode())
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));requests.append(body)
        self.send_response(200)
        if body.get('stream'):
            self.send_header('Content-Type','text/event-stream');self.end_headers()
            for delta,reason in [({'content':'검토 완료'},None),({},'stop')]:
                chunk={'id':'probe','object':'chat.completion.chunk','model':'context-probe','choices':[{'index':0,'delta':delta,'finish_reason':reason}]}
                self.wfile.write(('data: '+json.dumps(chunk)+'\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
        else:
            self.send_header('Content-Type','application/json');self.end_headers()
            self.wfile.write(json.dumps({'id':'probe','object':'chat.completion','model':'context-probe','choices':[{'index':0,'message':{'role':'assistant','content':'검토 완료'},'finish_reason':'stop'}],'usage':{'prompt_tokens':30,'completion_tokens':5,'total_tokens':35}}).encode())

def probe(folder):
    home=Path(folder)/'home';home.mkdir();workspace=Path(folder)/'financial-host-sentinel';workspace.mkdir()
    (workspace/'AGENTS.md').write_text('DO NOT LEAK: unrelated-trading-sentinel',encoding='utf-8')
    os.environ['HERMES_HOME']=str(home);os.environ['TERMINAL_CWD']=str(workspace)
    server=ThreadingHTTPServer(('127.0.0.1',0),API);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        from run_agent import AIAgent
        agent=AIAgent(model='context-probe',provider='custom',api_mode='chat_completions',api_key='fake',base_url=f'http://127.0.0.1:{server.server_port}/v1',quiet_mode=True,enabled_toolsets=[],cwd=str(workspace),skip_context_files=True,skip_memory=True,skip_background_review=True,max_iterations=2)
        bind_discussion_context(agent,{'application_context_scope':'focused_discussion','application_system_prompt':'당신은 CPO입니다. 카페 홈페이지 요구사항만 검토하세요.','system_prompt':'한국어로 답하세요.'})
        apply_response_contract(agent,'',True)
        result=agent.run_conversation('카페 홈페이지의 요구사항을 검토하세요.')
        assert not result.get('error'),result.get('error')
        assert requests,'Native agent never reached fake API'
        wire=json.dumps([r.get('messages',[]) for r in requests],ensure_ascii=False)
        for forbidden in ('financial-host-sentinel','unrelated-trading-sentinel','금융매매모델','Current working directory','Hermes runtime environment'):
            assert forbidden not in wire,forbidden
        assert 'CPO' in wire and '카페 홈페이지' in wire
        report={'native_transport':True,'fake_api_calls':len(requests),'user_model_calls':0,'host_context_in_wire':False,'application_role_retained':True}
        (Path(folder).parent/'project-zero-context.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report))
    finally:server.shutdown();server.server_close()

def main():
    import subprocess
    base=ROOT/'runtime/projects/manage/verification';base.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='context-',dir=base) as folder:
        # Hermes owns a process-lifetime log lock on Windows; exit the child before cleanup.
        subprocess.run([sys.executable,'-X','utf8','-B',__file__,'--child',folder],check=True,timeout=90)
if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--child':probe(sys.argv[2])
    else:main()
