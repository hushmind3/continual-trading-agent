from pathlib import Path
import ast,json,os,re,subprocess
R=Path(r'C:\Users\hushm\Desktop\금융매매모델');os.chdir(R)
names=subprocess.check_output([r'C:\Program Files\Git\cmd\git.exe','ls-files','-z']).decode().split('\0')
mapping={'stockrl.rea':'rea','stockrl.web_api':'web_api','stockrl.menu_registry':'menu_registry','stockrl.api_context':'api_context','stockrl.api_transport':'api_transport'}
def rename(name):
 for a,b in mapping.items():
  if name==a or name.startswith(a+'.'):return b+name[len(a):]
 return name
moves={'backend/stockrl/rea':'backend/rea',**{f'backend/stockrl/{name}.py':f'backend/{name}.py' for name in ('web_api','menu_registry','api_context','api_transport')}}
def relocated(path):
 for a,b in moves.items():
  if path==a or path.startswith(a+'/'):return b+path[len(a):]
 return path
owners={}
for f in R.glob('backend/stockrl/*/*/handlers.py'):
 module=f.relative_to(R/'backend').with_suffix('').as_posix().replace('/','.')
 for n in ast.parse(f.read_text(encoding='utf8')).body:
  if isinstance(n,(ast.FunctionDef,ast.ClassDef)):owners[n.name]=module
updates={}
for name in names:
 p=R/name
 if not name or not p.is_file() or name.startswith(('FinRL-X/','configs/')) or p.suffix not in ('.py','.ts','.tsx','.md','.cmd','.mjs'):continue
 s=p.read_text(encoding='utf-8-sig');new=relocated(name)
 if name in ('backend/stockrl/platform/system_operations.py','backend/stockrl/trading/control/operations_runtime.py'):
  lines=s.splitlines(True);edits=[]
  for n in ast.walk(ast.parse(s)):
   if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
   links=[i for i in ast.walk(n) if isinstance(i,ast.ImportFrom) and any(a.name=='web_api' and a.asname=='api' for a in i.names)]
   if not links:continue
   attrs={i.attr for i in ast.walk(n) if isinstance(i,ast.Attribute) and isinstance(i.value,ast.Name) and i.value.id=='api'}
   missing=attrs-set(owners)
   if missing:raise RuntimeError(f'Unresolved API helper references: {name}: {missing}')
   modules={owners[a] for a in attrs};aliases={m:'_'+m.split('.')[-2]+'_api' for m in modules}
   start=n.lineno-1;body=''.join(lines[start:n.end_lineno])
   for link in links:
    old=ast.get_source_segment(s,link);value=('\n'+' '*link.col_offset).join('from '+m.rsplit('.',1)[0]+' import handlers as '+aliases[m] for m in sorted(modules));body=body.replace(old,value)
   body=re.sub(r'\bapi\.(\w+)',lambda m:aliases[owners[m.group(1)]]+'.'+m.group(1),body)
   edits.append((start,n.end_lineno,body))
  for a,b,body in sorted(edits,reverse=True):lines[a:b]=[body]
  s=''.join(lines)
 if p.suffix=='.py':
  pkg=name.removeprefix('backend/').removesuffix('.py').replace('/','.').split('.')
  if p.name!='__init__.py':pkg=pkg[:-1]
  lines=s.splitlines(True);edits=[]
  for n in ast.walk(ast.parse(s)):
   if not isinstance(n,ast.ImportFrom) or n.module=='__future__':continue
   parents=pkg[:-(n.level-1)] if n.level>1 else pkg
   base='.'.join([*parents,*([n.module] if n.module else [])]) if n.level else (n.module or '')
   force=name!=new and bool(n.level)
   if not (force or rename(base)!=base or any(rename(base+'.'+a.name)!=base+'.'+a.name for a in n.names)):continue
   output=[]
   for a in n.names:
    child=base+'.'+a.name;target=rename(child)
    if child in mapping:
     parent,sep,member=target.rpartition('.')
     statement=('from '+parent+' import '+member if sep else 'import '+target)+(' as '+a.asname if a.asname else '')
    else:statement='from '+rename(base)+' import '+a.name+(' as '+a.asname if a.asname else '')
    output.append(statement)
   text=('\n'+' '*n.col_offset).join(output);edits.append((n.lineno-1,n.col_offset,n.end_lineno-1,n.end_col_offset,text))
  for a,c,b,d,text in sorted(edits,reverse=True):lines[a:b+1]=[lines[a].encode('utf8')[:c].decode('utf8')+text+lines[b].encode('utf8')[d:].decode('utf8')]
  s=''.join(lines)
 for a,b in mapping.items():s=re.sub(r'(?<![\w.])'+re.escape(a)+r'(?![\w])',lambda m:b,s)
 for a,b in moves.items():s=s.replace(a,b)
 if p.read_text(encoding='utf-8-sig')!=s or name!=new:updates[new]=s
 # Model and official algorithm files have not been moved; this only adjusts required imports.
updates['tests/test_state_integrity.py']=updates.get('tests/test_state_integrity.py',(R/'tests/test_state_integrity.py').read_text(encoding='utf8')).replace("{'web_api':api}","{'stockrl.finrl.policy_learning.handlers':api}")
s=updates.get('scripts/start_server.py',(R/'scripts/start_server.py').read_text(encoding='utf8'))
s=s.replace("'web_api:app' in command", "any(arg.rsplit('.',1)[-1]=='web_api:app' for arg in command)")
updates['scripts/start_server.py']=s
# REA owns its dependencies and lifecycle; finance shutdown closes only finance resources.
for folder in ('analysis','project_browser'):
 file=f'backend/rea/{folder}/handlers.py';s=updates[file]
 s=s.replace('from api_context import APIRouter, FiniteJSONResponse, HTTPException','from fastapi import APIRouter,HTTPException\nfrom api_transport import FiniteJSONResponse')
 s=s.replace('    from stockrl.management.diagnostics.handlers import stop\n','')
 if folder=='analysis':s+='\n\n@router.on_event("shutdown")\ndef close_analysis():\n    from rea.analysis.operations import connection\n    connection.close()\n'
 updates[file]=s
file='backend/stockrl/management/diagnostics/handlers.py';s=updates.get(file,(R/file).read_text(encoding='utf8')).replace('    from rea.analysis.operations import connection\n    connection.close()\n','');updates[file]=s
file='backend/menu_registry.py';s=updates[file].replace('def register_api(api):','def register_api(api,app):').replace('        for router in routers:api.include_router(router)','        for router in routers:\n            api.include_router(router)\n            app.router.on_startup.extend(router.on_startup)\n            app.router.on_shutdown.extend(router.on_shutdown)');updates[file]=s
updates['backend/web_api.py']=updates['backend/web_api.py'].replace('register_api(private_api)','register_api(private_api,app)')
# Inventory the relocated platform and REA without treating them as financial modules.
file='backend/stockrl/platform/framework_operations.py';s=updates.get(file,(R/file).read_text(encoding='utf8'))
s=s.replace("roots=[('stockrl',ROOT/'backend/stockrl'),", "roots=[('stockrl',ROOT/'backend/stockrl'),('REA',ROOT/'backend/rea'),('Platform',ROOT/'backend'),")
s=s.replace('        for directory,folders,files in os.walk(root):','        for directory,folders,files in os.walk(root):\n            if framework==\'Platform\':folders[:]=[]')
s=s.replace("    for module in ('web_api','__main__'", "    roots['Platform:web_api']=[]\n    for module in ('__main__'")
s=s.replace("            elif imported.startswith('stockrl.'):", "            elif imported.startswith('rea.'):target='REA:'+imported[4:]\n            elif imported in ('web_api','menu_registry','api_context','api_transport'):target='Platform:'+imported\n            elif imported.startswith('stockrl.'):")
old="item['imported']=bool(imported and imported.get('imported')) or (('src' if item['framework']=='FinRL-X' else 'finrl' if item['framework']=='FinRL' else 'stockrl')+'.'+item['id'].split(':',1)[1]) in sys.modules"
new="namespace={'FinRL-X':'src','FinRL':'finrl','stockrl':'stockrl','REA':'rea','Platform':''}[item['framework']]\n        module_name='.'.join(part for part in (namespace,item['id'].split(':',1)[1]) if part)\n        item['imported']=bool(imported and imported.get('imported')) or module_name in sys.modules"
if old not in s:raise RuntimeError('Inventory import-state contract changed')
s=s.replace(old,new);updates[file]=s
file='frontend/src/pages/shared/frameworks/FrameworkWorkspace.tsx';s=updates.get(file,(R/file).read_text(encoding='utf8')).replace("['all','FinRL','FinRL-X','stockrl']","['all','FinRL','FinRL-X','stockrl','REA','Platform']").replace("owner:'전체 공식'","owner:'전체'");updates[file]=s
file='.gitignore';s=(R/file).read_text(encoding='utf8');s+='\n/backend/rea/node_modules/\n';updates[file]=s
updates['backend/README.md']='''# Backend platform\n\n- web_api.py: single /api entry; imports the menu coordinator.\n- menu_registry.py: collects independent large-menu registrations and their router lifecycle callbacks.\n- api_context.py: shared HTTP objects and existing finance service references.\n- api_transport.py: gateway forwarding and React static delivery.\n- stockrl/: existing finance project and its trading/FinRL/extension modules.\n- rea/: independent REA project; analysis/ and project_browser/ are its small menus.\n- rea_projects/: saved source and inferred analysis outputs; not executable project registration and excluded from Git.\n\nRegistration: feature → submenu_manager → large-menu registration → menu_registry → web_api.\nRead each project and small-menu README before source files. Source/module/structural filenames use English ASCII. New features register through their own managers.\n'''
updates['backend/stockrl/README.md']='''# StockRL finance project\n\nFinance implementation stays in this package. Its project folders are trading/, finrl/, extensions/ and management/. Read each small-menu README first.\n\nThe platform entry and overall menu coordinator are ../web_api.py and ../menu_registry.py. REA is the independent sibling ../rea/; its implementation is outside this finance package.\n\nplatform/ and root expert_*/moe_* modules are shared financial execution/model contracts. Existing policy class import names are retained. Models, settings, accounts and market data are not moved.\n'''
updates['backend/stockrl/MENU_MAP.md']='''# Finance menu map\n\n- trading/: control/, paper_account/\n- finrl/: policy_learning/, tools/\n- extensions/: moe/, project_modules/\n- management/: connection_settings/, diagnostics/, backend_browser/\n\nEach project uses submenu_manager.py then its large-menu registration file. The overall coordinator is ../menu_registry.py; API entry is ../web_api.py. Independent REA is ../rea/.\n'''
file='backend/rea/README.md';s=updates.get(file,'');s=s.replace('../../rea_projects/','../rea_projects/');s+='\nIndependent backend project: backend/rea/. Its large-menu registration is imported by backend/menu_registry.py, and API delivery is backend/web_api.py. Installed node_modules remain inside this REA project.\n';updates[file]=s
file='AGENTS.md';s=(R/file).read_text(encoding='utf8');s=s.replace('- 백엔드와 프론트엔드는 분리하고,','- 실제 백엔드 위치: `backend/stockrl/`은 기존 금융 프로젝트로 유지하고, REA는 독립 `backend/rea/`에 둔다. 전체 메뉴 매니저 `backend/menu_registry.py`와 API 진입점 `backend/web_api.py`는 백엔드 루트에 둔다. 독립 프로젝트를 금융 프로젝트 폴더에 중첩하지 않는다.\n- 백엔드와 프론트엔드는 분리하고,');updates[file]=s
temp=Path(os.environ['TEMP']);(temp/'separate_rea_moves.json').write_text(json.dumps(moves,ensure_ascii=False),encoding='utf8');(temp/'separate_rea_updates.json').write_text(json.dumps(updates,ensure_ascii=False),encoding='utf8')
print(json.dumps({'physical_moves':len(moves),'source_reference_updates':len(updates),'rea_new_root':'backend/rea','finance_root_unchanged':'backend/stockrl'}))
