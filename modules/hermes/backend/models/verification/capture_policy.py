"""Capture request metadata using a temporary Hermes home and a fake model response."""
from pathlib import Path
import http.server
import importlib.util
import json
import sys
import tempfile
import threading
import time
from ruamel.yaml import YAML
import urllib.request

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'backend'))
from ai_agent.Hermes.engine.bridge import WorkerBridge

class Capture(http.server.BaseHTTPRequestHandler):
    calls=[]
    def log_message(self,*args):pass
    def do_GET(self):
        self.send_response(200);self.end_headers()
        self.wfile.write(json.dumps({'object':'list','data':[{'id':'Ornith-1.5-9B.Q4_K_M.gguf','context_length':262144}]}).encode())
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.calls.append(body)
        self.send_response(200)
        if body.get('stream'):
            self.send_header('Content-Type','text/event-stream');self.end_headers()
            for delta,finish in [({'role':'assistant','content':'ok'},None),({},'stop')]:
                self.wfile.write(('data: '+json.dumps({'id':'capture','object':'chat.completion.chunk','choices':[{'index':0,'delta':delta,'finish_reason':finish}]})+'\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
        else:
            self.send_header('Content-Type','application/json');self.end_headers()
            self.wfile.write(json.dumps({'id':'capture','object':'chat.completion','choices':[{'index':0,'message':{'role':'assistant','content':'ok'},'finish_reason':'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':1,'total_tokens':101}}).encode())

def main():
    output=ROOT/'runtime/ai_agent/Hermes/verification/performance';output.mkdir(parents=True,exist_ok=True)
    settings=json.loads((ROOT/'runtime/ai_agent/Hermes/platform-settings.json').read_text(encoding='utf8'))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Capture)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(dir=output) as temporary:
            folder=Path(temporary);home=folder/'home';home.mkdir()
            yaml=YAML(typ='safe')
            native=yaml.load((ROOT/'runtime/ai_agent/Hermes/config.yaml').read_text(encoding='utf8')) or {}
            native_deferral='--native-deferral' in sys.argv
            if native_deferral:
                sys.path.insert(0,str(ROOT/'modules/hermes/backend/engine/upstream'))
                from hermes_cli.config_defaults import DEFAULT_CONFIG
                native.setdefault('tools',{}).setdefault('tool_search',{})['defer']=list(DEFAULT_CONFIG['tools']['tool_search']['defer'])
            mcp_count=len(native.pop('mcp_servers',{}) or {})
            native.setdefault('model',{}).update(base_url=f'http://127.0.0.1:{server.server_port}/v1')
            with (home/'config.yaml').open('w',encoding='utf8') as stream:yaml.dump(native,stream)
            bridge=WorkerBridge(home)
            try:
                bridge.call('settings/save',{k:settings[k] for k in ('model','workspace','max_iterations','toolsets','system_prompt','tool_loading') if k in settings}|{'base_url':f'http://127.0.0.1:{server.server_port}/v1','api_key':'local'}|({'tool_loading':'native'} if native_deferral else {}))
                bridge.call('chat',{'message':'Hi. Reply briefly.','read_only':False})
                deadline=time.monotonic()+45
                while time.monotonic()<deadline:
                    status=bridge.call('status')
                    if status['job']['state'] not in ('starting','running','stopping'):break
                    time.sleep(.2)
                else:raise RuntimeError('Policy capture did not complete')
                summaries=[]
                for body in Capture.calls:
                    summaries.append({'parameters':{k:v for k,v in body.items() if k not in ('messages','tools')},
                        'messages':[{'role':m['role'],'chars':len(json.dumps(m.get('content'),ensure_ascii=False))} for m in body.get('messages',[])],
                        'tools':[t.get('function',{}).get('name') for t in body.get('tools',[])],
                        'tools_chars':len(json.dumps(body.get('tools',[]),ensure_ascii=False))})
                def post(url,data):
                    req=urllib.request.Request(url,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
                    with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)
                live=post('http://127.0.0.1:8766/api',{'operation':'ai_agent/Hermes/status','payload':{}})
                base=live['local_model']['base_url'].removesuffix('/v1')
                counts={}
                body=Capture.calls[0]
                variants={'user_only':{'messages':[m for m in body['messages'] if m['role']=='user']},
                          'with_system':{'messages':body['messages']},
                          'with_tools':{'messages':body['messages'],'tools':body.get('tools',[])}}
                for name,payload in variants.items():
                    prompt=post(base+'/apply-template',{**payload,'add_generation_prompt':True})['prompt']
                    counts[name]=len(post(base+'/tokenize',{'content':prompt,'add_special':False,'parse_special':True})['tokens'])
                summaries[0]['token_counts']=counts
                report={'state':status['job']['state'],'error':status['job'].get('error'),'native_deferral':native_deferral,'native_config_keys':list(native),'mcp_servers_omitted':mcp_count,'requests':summaries}
                filename='hermes-native-deferral.json' if native_deferral else 'hermes-request-policy.json'
                (output/filename).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
                print(json.dumps(report,ensure_ascii=False))
            finally:bridge.close()
    finally:server.shutdown();server.server_close()

if __name__=='__main__':main()
