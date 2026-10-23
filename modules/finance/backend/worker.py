"""Private ASGI/JSON-line worker; no HTTP listener and no host business imports."""
from __future__ import annotations
import asyncio,base64,importlib,importlib.util,json,os,sys,traceback
from pathlib import Path
MODULE=Path(__file__).resolve().parents[1]
META=json.loads((MODULE/'module.json').read_text(encoding='utf8'))
SPEC=META['runtime']; NAME=SPEC['package']
sys.stdin.reconfigure(encoding='utf8')
sys.stdout.reconfigure(encoding='utf8')
sys.stderr.reconfigure(encoding='utf8',errors='replace')
PROTOCOL=sys.stdout;sys.stdout=sys.stderr
spec=importlib.util.spec_from_file_location(NAME,MODULE/'backend/__init__.py',submodule_search_locations=[str(MODULE/'backend')])
package=importlib.util.module_from_spec(spec);sys.modules[NAME]=package;spec.loader.exec_module(package)
from fastapi import FastAPI,APIRouter
from pydantic import TypeAdapter
entry=importlib.import_module(NAME+'.'+SPEC['entry'])
if NAME=='stockrl':
 context=importlib.import_module(NAME+'.api_context');app=context.app;api=context.private_api
else:
 app=FastAPI();api=APIRouter()
for router in entry.ROUTERS:
 api.include_router(router)
 app.router.on_startup.extend(router.on_startup);app.router.on_shutdown.extend(router.on_shutdown)
app.include_router(api)
if NAME=='stockrl':context.system.command_router=api

def fields(values):
 properties={};required=[]
 for field in values:
  schema=TypeAdapter(field.field_info.annotation).json_schema();schema['title']=field.alias
  if field.field_info.description:schema['description']=field.field_info.description
  properties[field.alias]=schema
  if field.required:required.append(field.alias)
 return {'type':'object','properties':properties,'required':required}

def describe():
 routes=[]
 for route in api.routes:
  if not hasattr(route,'endpoint'):continue
  body=TypeAdapter(route.body_field.field_info.annotation).json_schema() if route.body_field else {'type':'object','additionalProperties':True}
  routes.append({'path':route.path,'methods':sorted(route.methods or []),'name':route.endpoint.__name__,
   'module':route.endpoint.__module__,'description':route.description or '',
   'schemas':{'path_schema':fields(route.dependant.path_params),'query_schema':fields(route.dependant.query_params),'body_schema':body}})
 return {'group':entry.GROUP,'routes':routes,'python':sys.executable,'prefix':sys.prefix,'source':str(package.__file__),'module':str(MODULE),'dependencies':{name:str(getattr(sys.modules[name],'__file__','')) for name in ('fastapi','torch') if name in sys.modules}}

def hook(name):
 if NAME=='stockrl':
  if name=='actions':return importlib.import_module(NAME+'.platform.framework_operations').action_list()
  if name=='busy':return context.busy()
  if name=='reserve_restart':
   if reason:=context.busy():raise RuntimeError(' · '.join(reason))
   context.system.restarting=True
  elif name=='cancel_restart':context.system.restarting=False
  elif name=='cancel':context.system.cancel()
  elif name=='invalidate_states':context.system.invalidate_states()
 else:
  if name=='actions':return []
  if name in ('busy','reserve_restart'):
   state=importlib.import_module(NAME+'.program_analysis.extract').analysis_status()
   active=state.get('active') or state.get('running') or state.get('busy') or state.get('state') in ('running','starting','stopping')
   if name=='busy':return ['실행 중인 REA 분석'] if active else []
   if active:raise RuntimeError('실행 중인 REA 분석')
 return None

async def request(message):
 body=base64.b64decode(message.get('body',''));path=message['path']
 headers=[(key.lower().encode('latin1'),value.encode('latin1')) for key,value in message.get('headers',{}).items()
  if key.lower() not in ('content-length','connection','host')]
 scope={'type':'http','asgi':{'version':'3.0'},'http_version':'1.1','method':message['method'],'scheme':'http',
  'path':path,'raw_path':path.encode(),'root_path':'','query_string':message.get('query','').encode(),
  'headers':headers,'client':('127.0.0.1',0),'server':('127.0.0.1',8766),'extensions':{'http.response.pathsend':{}}}
 result={'status':500,'headers':{}};parts=[];sent=False;size=0
 async def receive():
  nonlocal sent
  if not sent:sent=True;return {'type':'http.request','body':body,'more_body':False}
  await asyncio.sleep(3600);return {'type':'http.disconnect'}
 async def send(event):
  nonlocal size
  if event['type']=='http.response.start':
   result.update(status=event['status'],headers={k.decode('latin1'):v.decode('latin1') for k,v in event.get('headers',[])
    if k.lower() not in (b'content-length',b'transfer-encoding',b'content-encoding')})
  elif event['type']=='http.response.body':
   data=event.get('body',b'');size+=len(data)
   parts.append(data)
  elif event['type']=='http.response.pathsend':result['file']=event['path']
 await app(scope,receive,send)
 result['body']=base64.b64encode(b''.join(parts)).decode();return result

async def dispatch(message):
 try:
  op=message['operation'];payload=message.get('payload',{})
  if op=='describe':result=describe()
  elif op=='hook':result=await asyncio.to_thread(hook,payload['name'])
  elif op=='request':result=await request(payload)
  else:raise ValueError('지원하지 않는 모듈 명령입니다: '+op)
  response={'id':message['id'],'result':result}
 except Exception as exc:
  traceback.print_exc(file=sys.stderr);response={'id':message.get('id'),'error':str(exc)}
 PROTOCOL.write(json.dumps(response,ensure_ascii=False)+'\n');PROTOCOL.flush()

async def main():
 tasks=set()
 async with app.router.lifespan_context(app):
  while line:=await asyncio.to_thread(sys.stdin.readline):
   message=json.loads(line)
   if message.get('operation')=='shutdown':
    PROTOCOL.write(json.dumps({'id':message['id'],'result':True})+'\n');PROTOCOL.flush();break
   task=asyncio.create_task(dispatch(message));tasks.add(task);task.add_done_callback(tasks.discard)
  if tasks:await asyncio.gather(*tasks,return_exceptions=True)
if __name__=='__main__':asyncio.run(main())
