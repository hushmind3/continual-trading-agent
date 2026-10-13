from pathlib import Path
import ast,json,os,re,subprocess
from datetime import datetime,timezone

ROOT=Path(r'C:\Users\hushm\Desktop\금융매매모델')
os.chdir(ROOT)
git=r'C:\Program Files\Git\cmd\git.exe'
tracked=subprocess.check_output([git,'ls-files','-z'],cwd=ROOT).decode().split('\0')
original={p:(ROOT/p).read_text(encoding='utf-8-sig') for p in tracked if p and (ROOT/p).is_file() and Path(p).suffix in ('.py','.ts','.tsx','.md','.cmd','.mjs','.toml') and not p.startswith(('FinRL-X/','configs/'))}
moves={}
groups={'trading':{'control':'운영 제어','paper_account':'가상계좌 · 주문'},'finrl':{'policy_learning':'정책 학습','tools':'FinRL 모듈 · 도구'},'extensions':{'moe':'MoE','project_modules':'프로젝트 모듈'},'management':{'connection_settings':'연결 · 설정','diagnostics':'진단 · 로그 · 코드 적용','backend_browser':'백엔드 기능 전체'},'rea':{'analysis':'프로그램 분석','project_browser':'프로젝트 탐색'}}
menu_map={'trading_control_menu':('trading','control'),'paper_account_menu':('trading','paper_account'),'policy_learning_menu':('finrl','policy_learning'),'finrl_tools_menu':('finrl','tools'),'moe_menu':('extensions','moe'),'project_modules_menu':('extensions','project_modules'),'connection_settings_menu':('management','connection_settings'),'diagnostics_menu':('management','diagnostics'),'backend_browser_menu':('management','backend_browser'),'rea_tools_menu':('rea','analysis')}
for old,(group,small) in menu_map.items():moves[f'backend/stockrl/{group}/{old}.py']=f'backend/stockrl/{group}/{small}/menu.py'
for old,new in {'platform/operations_runtime.py':'trading/control/operations_runtime.py','platform/operations_settings.py':'trading/control/operations_settings.py','paper_account.py':'trading/paper_account/paper_account.py','provider_credentials.py':'management/connection_settings/provider_credentials.py','official_cli.py':'finrl/policy_learning/official_cli.py','rea/operations.py':'rea/analysis/operations.py','rea/projects.py':'rea/analysis/extract.py','rea/bridge.mjs':'rea/analysis/bridge.mjs','rea/artifacts.mjs':'rea/analysis/artifacts.mjs'}.items():moves['backend/stockrl/'+old]='backend/stockrl/'+new
front_dirs={'operations':'trading/control','paper':'trading/paper_account','training':'finrl/policy_learning','model':'extensions/moe','settings':'management/connection_settings','system':'management/diagnostics','frameworks':'shared/frameworks'}
for p in original:
 for old,new in front_dirs.items():
  if p.startswith('frontend/src/pages/'+old+'/'):moves[p]=p.replace('/pages/'+old+'/', '/pages/'+new+'/')
moves['frontend/src/pages/frameworks/FeatureWorkspace.tsx']='frontend/src/pages/management/backend_browser/FeatureWorkspace.tsx'
moves['frontend/src/pages/rea/REAWorkspace.tsx']='frontend/src/pages/rea/analysis/REAWorkspace.tsx'
for group in groups:moves[f'frontend/src/shell/menu_groups/{group}_menu_manager.ts']=f'frontend/src/pages/{group}/{group}_menu_manager.ts'
def module(path):return path.removeprefix('backend/').removesuffix('.py').replace('/','.').removesuffix('.__init__')
module_map={module(a):module(b) for a,b in moves.items() if a.endswith('.py')}
def moved_module(name):
 for old,new in sorted(module_map.items(),key=lambda x:-len(x[0])):
  if name==old or name.startswith(old+'.'):return new+name[len(old):]
 return name
def python_imports(text,old_path,force=False):
 tree=ast.parse(text);lines=text.splitlines(True);edits=[]
 pkg=module(old_path).split('.') if old_path.endswith('/__init__.py') else module(old_path).split('.')[:-1]
 for n in ast.walk(tree):
  if isinstance(n,ast.ImportFrom) and n.module!='__future__':
   parts=pkg[:-(n.level-1)] if n.level>1 else pkg
   base='.'.join([*parts,*([n.module] if n.module else [])]) if n.level else (n.module or '')
   changed=force and n.level or moved_module(base)!=base or any(moved_module(base+'.'+a.name)!=base+'.'+a.name for a in n.names)
   if not changed:continue
   stmts=[]
   for a in n.names:
    child=base+'.'+a.name;target=moved_module(child)
    if target!=child and child in module_map:parent,_,member=target.rpartition('.')
    else:parent=moved_module(base);member=a.name
    stmts.append('from '+parent+' import '+member+(' as '+a.asname if a.asname else ''))
   edits.append((n.lineno-1,n.col_offset,n.end_lineno-1,n.end_col_offset,('\n'+' '*n.col_offset).join(stmts)))
  elif isinstance(n,ast.Import):
   if any(moved_module(a.name)!=a.name for a in n.names):
    val='import '+', '.join(moved_module(a.name)+(' as '+a.asname if a.asname else '') for a in n.names)
    edits.append((n.lineno-1,n.col_offset,n.end_lineno-1,n.end_col_offset,val))
 for a,c,b,d,val in sorted(edits,reverse=True):
  # AST offsets are UTF-8 byte offsets; decode the preserved prefix/suffix.
  prefix=lines[a].encode('utf8')[:c].decode('utf8');suffix=lines[b].encode('utf8')[d:].decode('utf8')
  lines[a:b+1]=[prefix+val+suffix]
 return ''.join(lines)
result={}
for old,text in original.items():
 new=moves.get(old,old)
 if old.endswith('.py'):text=python_imports(text,old,old in moves or old=='backend/stockrl/web_api.py')
 if Path(old).suffix in ('.ts','.tsx'):
  def relative(m):
   quote,spec=m.group(1),m.group(2)
   if not spec.startswith('.'):return m.group(0)
   resolved=Path(os.path.normpath(str(Path(old).parent/spec))).as_posix()
   found=next((v for v in [resolved,resolved+'.tsx',resolved+'.ts',resolved+'.css',resolved+'/index.tsx',resolved+'/index.ts'] if v in original or (ROOT/v).is_file()),None)
   if not found:return m.group(0)
   target=moves.get(found,found);relative=os.path.relpath(target,Path(new).parent).replace('\\','/')
   if Path(target).suffix in ('.ts','.tsx'):relative=relative.rsplit('.',1)[0]
   if not relative.startswith('.'):relative='./'+relative
   return quote+relative+quote
  text=re.sub(r"(['\"])([^'\"\n]+)\1",relative,text)
 # Update explicit module names in workers, installed-engine scripts and recorded source references.
 for before,after in sorted(module_map.items(),key=lambda x:-len(x[0])):
  text=re.sub(r'(?<![\w.])'+re.escape(before)+r'(?![\w])',lambda m:after,text)
 for before,after in sorted(moves.items(),key=lambda x:-len(x[0])):text=text.replace(before,after)
 result[new]=text

# Separate existing HTTP handlers by their actual menu; preserve bodies and contracts.
api=result['backend/stockrl/web_api.py'];tree=ast.parse(api)
owners={}
sets={
 'finrl/policy_learning':'RunRequest algorithms source_settings model_state replay_metadata saved_replay checkpoints currency_models preflight check launch train checkpoint_download restore_checkpoint download',
 'extensions/moe':'ChampionRequest Selection Registration expert_descriptor expert_state champions champion_create select register library_job model_files stop_library open_model_directory',
 'trading/control':'ControlRequest operation_control start_system stop_system',
 'trading/paper_account':'OrderRequest paper_order',
 'management/connection_settings':'CredentialRequest connections provider connect_provider check_provider public_feed disconnect_provider operational_settings save_operational_settings',
 'management/diagnostics':'now file_info database capabilities health modules menu_catalog state_stamp state_view state logs stop apply_changes restart_blockers prepare_restart system_check close_operations',
 'management/backend_browser':'framework_catalog framework_providers framework_provider_save framework_task framework_result framework_artifact',
 'rea/analysis':'rea_pick rea_analyze rea_stop',
 'rea/project_browser':'rea_projects rea_project_tree rea_project_file rea_project_open',
 'transport':'local_writes react_index'}
for where,names in sets.items():
 for name in names.split():owners[name]=where
defs={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
assert set(defs)==set(owners),(set(defs)-set(owners),set(owners)-set(defs))
imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) and 'menu_registry' not in ast.unparse(n)]
context=[ast.get_source_segment(api,n) for n in imports]
context+= [ast.get_source_segment(api,n) for n in tree.body if isinstance(n,ast.Assign) and not ast.unparse(n).startswith('system.command_router')]
context='"""Shared HTTP context; menu implementations live in their own folders."""\n'+'\n'.join(context)+'\n'
context=context.replace('title="FinRL local workspace"','title="Local project platform"')
context_names=set()
for n in ast.parse(context).body:
 if isinstance(n,(ast.Import,ast.ImportFrom)):
  context_names.update(a.asname or (a.name.split('.')[0] if isinstance(n,ast.Import) else a.name) for a in n.names)
 elif isinstance(n,ast.Assign):context_names.update(t.id for t in n.targets if isinstance(t,ast.Name))
result['backend/stockrl/api_context.py']=context
def handler_module(where):return 'stockrl.'+where.replace('/','.')+'.handlers' if where!='transport' else 'stockrl.api_transport'
def transform_node(node,where):
 start=min([node.lineno,*[d.lineno for d in node.decorator_list]])-1;lines=api.splitlines(True)[start:node.end_lineno]
 used={n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}
 cross={name for name in used if name in owners and owners[name]!=where}
 top=set()
 if isinstance(node,ast.ClassDef):top=cross;cross=set()
 else:
  expressions=[*node.decorator_list,*node.args.defaults,*[v for v in node.args.kw_defaults if v],*[a.annotation for a in [*node.args.args,*node.args.kwonlyargs,*node.args.posonlyargs] if a.annotation]]
  if node.returns:expressions.append(node.returns)
  top={n.id for e in expressions for n in ast.walk(e) if isinstance(n,ast.Name)}&cross;cross-=top
 if cross:
  body=node.body[0];insert=body.end_lineno if isinstance(body,ast.Expr) and isinstance(body.value,ast.Constant) and isinstance(body.value.value,str) else body.lineno-1
  lines[insert-start:insert-start]=[' '*body.col_offset+'from '+handler_module(owners[name])+' import '+name+'\n' for name in sorted(cross)]
 body=''.join(lines).replace('@private_api.','@router.')
 if where=='transport':
  body=re.sub(r'^@app\.[^\n]+\n','',body,flags=re.M)
  first=node.body[0];offset=first.lineno-1-node.lineno+1
  # Transport imports the shared context at call time to avoid context/transport cycles.
  bodylines=body.splitlines(True);at=next(i for i,line in enumerate(bodylines) if line.startswith('    '))
  bodylines[at:at]=['    from stockrl.api_context import '+', '.join(sorted((used&context_names)-{'__future__'}))+'\n']
  body=''.join(bodylines)
 return body,used&context_names,top
for where in sets:
 chunks=[];names=set();top=set()
 for name,n in defs.items():
  if owners[name]!=where:continue
  body,used,globalcross=transform_node(n,where);chunks.append(body);names.update(used);top.update(globalcross)
 if where=='transport':
  result['backend/stockrl/api_transport.py']+='\n\n'+'\n\n'.join(chunks)+'\n';continue
 names.discard('private_api');names.update(('APIRouter','FiniteJSONResponse'))
 header='"""'+groups[where.split('/')[0]][where.split('/')[1]]+' — existing API handlers."""\nfrom __future__ import annotations\n'
 header+='from stockrl.api_context import '+', '.join(sorted(names))+'\n'
 for name in sorted(top):header+='from '+handler_module(owners[name])+' import '+name+'\n'
 header+='\nrouter=APIRouter(default_response_class=FiniteJSONResponse)\n\n'
 result['backend/stockrl/'+where+'/handlers.py']=header+'\n\n'.join(chunks)+'\n'
result['backend/stockrl/web_api.py']='''"""Platform entry: import the menu coordinator and expose one API."""
from .api_context import app,private_api,FRONTEND_DIST,StaticFiles,Route,UnifiedAPI,GZipMiddleware,system
from .api_transport import local_writes,react_index
from .menu_registry import register_api

register_api(private_api)
app.router.routes.append(Route('/api',UnifiedAPI(),methods=['GET','POST']))
app.mount('/assets',StaticFiles(directory=str(FRONTEND_DIST/'assets'),check_dir=False),name='react-assets')
app.get('/',include_in_schema=False)(react_index)
app.middleware('http')(local_writes)
app.add_middleware(GZipMiddleware)
system.command_router=private_api
'''

# Each coordinator imports only its small-menu packages, including their routers.
for group,children in groups.items():
 path=f'backend/stockrl/{group}/{group}_menu_manager.py'
 source=result[path]
 if group=='rea':source='"""REA menu coordinator."""\nfrom .analysis.menu import MENU\nfrom .project_browser.menu import MENU as PROJECTS\nGROUP={\'id\':\'rea\',\'title\':\'REA 역공학\',\'menus\':(MENU,PROJECTS)}\n'
 router_children=[c for c in children if f'backend/stockrl/{group}/{c}/handlers.py' in result]
 source+='\n'+''.join(f'from .{c}.handlers import router as {c}_router\n' for c in router_children)
 source+='ROUTERS=('+','.join(c+'_router' for c in router_children)+',)\n'
 result[path]=source
registry=result['backend/stockrl/menu_registry.py']
for group,label in [('trading','TRADING'),('finrl','FINRL'),('extensions','EXTENSIONS'),('management','MANAGEMENT'),('rea','REA')]:
 registry=registry.replace(f'import GROUP as {label}',f'import GROUP as {label}, ROUTERS as {label}_ROUTERS')
registry+='\n\ndef register_api(api):\n    """Collect small-menu routers through the five large-menu coordinators."""\n    for routers in (TRADING_ROUTERS,FINRL_ROUTERS,REA_ROUTERS,EXTENSIONS_ROUTERS,MANAGEMENT_ROUTERS):\n        for router in routers:api.include_router(router)\n    bind(api.routes)\n'
result['backend/stockrl/menu_registry.py']=registry

# REA separates extraction from saved-project browsing; IDs remain stable.
rea=result['backend/stockrl/rea/analysis/extract.py'];rt=ast.parse(rea)
browse={'_project','catalog','_inside','tree','read_file','open_folder'}
bodies={n.name:ast.get_source_segment(rea,n) for n in rt.body if isinstance(n,ast.FunctionDef)}
browser='''"""Browse physical REA output projects; never execute extracted programs."""
from pathlib import Path
import json,os,re
from stockrl import ROOT
OUTPUT=ROOT/'backend/rea_projects'

'''
for n in rt.body:
 if isinstance(n,ast.FunctionDef) and n.name in browse:browser+=bodies[n.name]+'\n\n'
browser=re.sub(r"def _project\(identifier\):.*?(?=\ndef catalog\()",'''def _project(identifier):
    if not re.fullmatch(r'[a-f0-9]{32}',identifier or ''):raise ValueError('저장 프로젝트를 선택하세요.')
    for entry in catalog()['items']:
        if entry['id']==identifier:
            folder=_inside(OUTPUT,Path(entry['folder']).name)
            if folder.is_dir():return folder
    raise ValueError('저장 프로젝트가 없습니다.')

''',browser,flags=re.S)
lines=rea.splitlines(True)
for n in sorted([n for n in rt.body if isinstance(n,ast.FunctionDef) and n.name in browse],key=lambda n:-n.lineno):del lines[n.lineno-1:n.end_lineno]
rea=''.join(lines).replace("OUTPUT=ROOT/'backend/rea_projects'","from stockrl.rea.project_browser.projects import OUTPUT,_inside")
rea=rea.replace("identifier=uuid.uuid4().hex;folder=OUTPUT/identifier", "identifier=uuid.uuid4().hex\n    display=urlparse(target).hostname if kind=='web' else Path(target).name\n    display=re.sub(r'[<>:\"/\\\\|?*\\x00-\\x1f]','_',display or '분석대상').strip(' .')[:90] or '분석대상'\n    if display.upper().split('.')[0] in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:display='대상_'+display\n    folder=OUTPUT/(display+'__'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))")
rea=rea.replace("BASE/'artifacts.mjs'","BASE/'analysis/artifacts.mjs'")
result['backend/stockrl/rea/analysis/extract.py']=rea
result['backend/stockrl/rea/project_browser/projects.py']=browser
result['backend/stockrl/rea/analysis/operations.py']=result['backend/stockrl/rea/analysis/operations.py'].replace('BASE=Path(__file__).parent','BASE=Path(__file__).parent.parent').replace("BASE/'bridge.mjs'","BASE/'analysis/bridge.mjs'")
# Imports of the old all-in-one project module must target the function's owner.
for name in list(result):
 if name.endswith('.py'):
  text=result[name]
  text=re.sub(r'from stockrl\.rea\.analysis\.extract import (catalog|tree|read_file|open_folder|_inside)\b',r'from stockrl.rea.project_browser.projects import \1',text)
  result[name]=text
oldmenu=result['backend/stockrl/rea/analysis/menu.py'].splitlines()
result['backend/stockrl/rea/analysis/menu.py']='\n'.join(l for l in oldmenu if not l.startswith('PROJECTS='))+'\n'
result['backend/stockrl/rea/project_browser/menu.py']='"""REA saved-project menu."""\n'+next(l.replace('PROJECTS=','MENU=',1) for l in oldmenu if l.startswith('PROJECTS='))+'\n'

# Split the two REA screens and retain only truly shared framework UI in shared/.
fp='frontend/src/pages/rea/analysis/REAWorkspace.tsx';text=result[fp];head,analysis,browsertext=text.split('export function REAWorkspace()',1)[0],text.split('export function REAWorkspace()',1)[1].split('export function REAProjects()',1)[0],text.split('export function REAProjects()',1)[1]
result[fp]=head.replace('useEffect,useState','useState').replace('interface Entry {name:string;path:string;folder:boolean;bytes?:number}\n','')+'export function REAWorkspace()'+analysis
result['frontend/src/pages/rea/project_browser/REAProjects.tsx']=head+'export function REAProjects()'+browsertext
shared='frontend/src/pages/shared/frameworks/FrameworkWorkspace.tsx'
result[shared]=re.sub(r'export function (FinrlToolsWorkspace|ProjectModulesWorkspace)\(\).*?\n','',result[shared])
for group,small,component,scope in [('finrl','tools','FinrlToolsWorkspace','FinRL'),('extensions','project_modules','ProjectModulesWorkspace','stockrl')]:
 result[f'frontend/src/pages/{group}/{small}/{component}.tsx']=f"import {{FrameworkWorkspace}} from '../../shared/frameworks/FrameworkWorkspace';\nexport function {component}(){{return <FrameworkWorkspace framework=\"{scope}\"/>}}\n"
 p=f'frontend/src/pages/{group}/{group}_menu_manager.ts'
 result[p]=result[p].replace("../shared/frameworks/FrameworkWorkspace",f'./{small}/{component}')
result['frontend/src/pages/rea/rea_menu_manager.ts']=result['frontend/src/pages/rea/rea_menu_manager.ts'].replace("import('./analysis/REAWorkspace').then(m=>({default:m.REAProjects}))","import('./project_browser/REAProjects').then(m=>({default:m.REAProjects}))")
# Correct menu metadata paths and the now separated REA browser.
for name,text in list(result.items()):
 if '/menu.py' in name:
  text=text.replace('pages/rea/REAWorkspace.tsx','pages/rea/analysis/REAWorkspace.tsx')
  if name.endswith('/project_browser/menu.py'):text=text.replace('pages/rea/analysis/REAWorkspace.tsx','pages/rea/project_browser/REAProjects.tsx').replace('stockrl.rea.analysis.menu','stockrl.rea.project_browser.menu')
  if name.endswith('/finrl/tools/menu.py'):text=text.replace('pages/shared/frameworks/FrameworkWorkspace.tsx','pages/finrl/tools/FinrlToolsWorkspace.tsx')
  if name.endswith('/extensions/project_modules/menu.py'):text=text.replace('pages/shared/frameworks/FrameworkWorkspace.tsx','pages/extensions/project_modules/ProjectModulesWorkspace.tsx')
  result[name]=text
result['frontend/src/shell/Shell.tsx']=result['frontend/src/shell/Shell.tsx'].replace('FinRL <span className="hidden text-[11px] font-normal text-slate-400 sm:inline">SB3 SAC</span>','프로젝트 플랫폼')
result['frontend/index.html']=(ROOT/'frontend/index.html').read_text(encoding='utf8').replace('<title>FinRL', '<title>프로젝트 플랫폼')

# Short navigation documents explain scope and distinguish registration from execution.
for group,children in groups.items():
 for base in ('backend/stockrl','frontend/src/pages'):
  rows=[]
  for small,title in children.items():
   folder=f'{base}/{group}/{small}';files=sorted(Path(p).name for p in result if str(Path(p).parent).replace('\\','/')==folder and not p.endswith('README.md'))
   roles='menu.py: 메뉴 등록; handlers.py: 기존 API 처리. ' if base.startswith('backend') else '화면 컴포넌트와 소속 기능. '
   result[folder+'/README.md']=f'# {title}\n\n- 역할: {roles}\n- 핵심 파일: '+', '.join(files)+f'\n- 상위 연결: ../{group}_menu_manager.'+('py' if base.startswith('backend') else 'ts')+' → 전체 menu_registry → 단일 /api.\n- 필수 의존성: 소스의 명시적 import와 공통 상태·API 전송 모듈.\n- 상태: 등록 경로 이식 완료. 이번 구조 변경 후 함수 실행·브라우저 검사 미실행. 기존 기록만 실행 확인으로 표시합니다.\n'
   rows.append(f'- [{title}]({small}/README.md): {small}/')
  result[f'{base}/{group}/README.md']='# '+{'trading':'거래 운영','finrl':'FinRL · 메인','extensions':'프로젝트 확장','management':'연결 · 관리','rea':'REA 역공학'}[group]+f'\n\n취합: `{group}_menu_manager.'+('py' if base.startswith('backend') else 'ts')+'`. 이 파일만 상위 menu_registry가 import합니다.\n\n'+'\n'.join(rows)+'\n'
result['frontend/src/pages/README.md']='# 플랫폼 대메뉴\n\n'+''.join(f'- [{group}]({group}/README.md)\n' for group in groups)+'\nshared/는 여러 메뉴에서 재사용하는 화면 부품입니다. 메뉴 취합 파일은 각 대메뉴 폴더에 있고, 전체 총괄은 shell/menu_groups/menu_registry.ts입니다.\n'
result['frontend/src/shell/menu_groups/README.md']='# 전체 메뉴 총괄\n\nmenu_registry.ts는 pages/의 대메뉴 취합 파일 5개만 import합니다. menu_types.ts는 공통 메뉴 계약입니다. 개별 화면은 대메뉴 아래 작은 메뉴 폴더에서 구현합니다.\n'
result['backend/stockrl/README.md']='# 프로젝트 플랫폼 백엔드\n\nweb_api.py → menu_registry.py → 대메뉴 취합 파일 → 작은 메뉴의 menu.py·handlers.py 순서로 연결합니다. 각 폴더 README를 먼저 읽습니다.\n\n'+''.join(f'- [{group}]({group}/README.md)\n' for group in groups)+'\n- api_context.py: 공유 HTTP 객체·기존 상태 관리자 참조.\n- api_transport.py: 단일 /api 전송·로컬 요청 처리·React 제공.\n- platform/: 여러 메뉴가 함께 사용하는 상태·모델·장치·공식 모듈 실행 기반.\n- 루트 expert_*, moe_*, multiscale.py: 학습·운영·MoE에서 공유하는 모델 계약입니다. 저장 정책의 클래스 import 경로를 유지합니다.\n- finrl/framework.py와 finrl_trading/: 여러 메뉴에서 사용하는 공식 라이브러리 연결입니다.\n- job_worker.py: 메뉴 구현을 실행하는 공통 작업 프로세스.\n\n단일 /api를 유지합니다. 메뉴 등록·import·실행 확인은 서로 다릅니다. 모델·데이터·계좌·인증·설정은 재배치하지 않습니다.\n'
result['backend/stockrl/rea/analysis/README.md']+='\noperations.py는 설치된 원본 REA CLI/MCP·Ghidra와 연결하며 extract.py는 원문 추출·분석 저장만 수행합니다. bridge.mjs·artifacts.mjs도 이 폴더에 있습니다. 코딩 에이전트·재구현·추출 프로그램 실행은 자동 호출하지 않습니다.\n'
result['backend/stockrl/rea/project_browser/README.md']+='\nprojects.py는 backend/rea_projects/의 물리적 저장 결과를 탐색합니다. 폴더명은 분석 대상 이름과 생성 시각입니다. 내부 프로젝트 ID와 원본/추론 구분을 유지하며 original/의 내용은 이름 변경 과정에서 수정하지 않습니다.\n'
result['backend/stockrl/rea/README.md']+='\n설치 의존성: 이 대메뉴 폴더의 package.json·node_modules. 저장 결과: ../../rea_projects/ (Git 제외). 분석 엔진은 analysis/, 저장 결과 탐색은 project_browser/에 있습니다.\n'
# A fresh package marker is needed only for newly introduced Python folders.
for group,children in groups.items():
 for small in children:result.setdefault(f'backend/stockrl/{group}/{small}/__init__.py',f'"""{children[small]}."""\n')

# Prepare moves; PowerShell performs all actual filesystem relocation within the workspace.
plan=[]
for old,new in moves.items():
 assert (ROOT/old).is_file(),old
 assert not (ROOT/new).exists(),new
 plan.append({'source':old,'destination':new})
for file in (ROOT/'backend/rea_projects').glob('*/project.json'):
 meta=json.loads(file.read_text(encoding='utf8'));old=file.parent
 if not re.fullmatch(r'[a-f0-9]{32}',old.name):continue
 label=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(meta.get('name') or '분석대상')).strip(' .')[:90] or '분석대상'
 if label.upper().split('.')[0] in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:label='대상_'+label
 stamp=re.sub(r'[^0-9]','',str(meta.get('created_at') or ''))[:20] or datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
 new=old.with_name(label+'__'+stamp)
 if new.exists():new=old.with_name(label+'__'+stamp+'_'+meta['id'][:8])
 assert not new.exists(),new
 plan.append({'source':old.relative_to(ROOT).as_posix(),'destination':new.relative_to(ROOT).as_posix()})
 meta['folder']=str(new);result[new.relative_to(ROOT).as_posix()+'/project.json']=json.dumps(meta,ensure_ascii=False,indent=2)+'\n'
 # Saved analysis evidence contains paths to the copied source; update those paths only.
 for evidence in (old/'analysis').rglob('*.json'):
  source=evidence.read_text(encoding='utf8');changed=source.replace(json.dumps(str(old))[1:-1],json.dumps(str(new))[1:-1]).replace(old.as_posix(),new.as_posix())
  if source!=changed:result[(new/evidence.relative_to(old)).relative_to(ROOT).as_posix()]=changed
temp=Path(os.environ['TEMP'])
(temp/'project_menu_move_plan.json').write_text(json.dumps(plan,ensure_ascii=False),encoding='utf8')
(temp/'project_menu_file_updates.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf8')
print(json.dumps({'move_count':len(plan),'small_menus':sum(map(len,groups.values())),'api_entry_lines':len(result['backend/stockrl/web_api.py'].splitlines()),'rea_renames':sum(p['source'].startswith('backend/rea_projects/') for p in plan),'updates':len(result)},ensure_ascii=False))
