from pathlib import Path
import ast,json,os,re,subprocess
import psutil
R=Path(r'C:\Users\hushm\Desktop\금융매매모델');os.chdir(R)
p=psutil.Process();p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[:2])
tracked=[v for v in subprocess.check_output([r'C:\Program Files\Git\cmd\git.exe','ls-files','-z']).decode().split('\0') if v]
pyfiles=[v for v in tracked if v.endswith('.py') and v.startswith(('backend/','scripts/','tests/'))]
def module(name):return name.removeprefix('backend/').removesuffix('.py').replace('/','.').removesuffix('.__init__')
mods={module(v):v for v in pyfiles if v.startswith('backend/')};edges={};errors=[]
for name in pyfiles:
 source=(R/name).read_text(encoding='utf-8-sig')
 try:tree=ast.parse(source)
 except SyntaxError as e:errors.append({'path':name,'reason':str(e)});continue
 own=module(name);pkg=own.split('.') if name.endswith('/__init__.py') else own.split('.')[:-1];deps=set()
 for n in ast.walk(tree):
  if isinstance(n,ast.Import):deps.update(a.name for a in n.names)
  elif isinstance(n,ast.ImportFrom):
   parent=pkg[:-(n.level-1)] if n.level>1 else pkg
   base='.'.join([*parent,*([n.module] if n.module else [])]) if n.level else (n.module or '')
   deps.add(base);deps.update('.'.join(v for v in (base,a.name) if v) for a in n.names)
  elif isinstance(n,ast.Constant) and isinstance(n.value,str):
   if n.value in mods and n.value!=own:deps.add(n.value)
   # Process entry strings and uvicorn module:app references also count.
   if n.value.split(':',1)[0] in mods:deps.add(n.value.split(':',1)[0])
 deps={d for d in deps if d in mods};deps.update('.'.join(own.split('.')[:i]) for i in range(1,len(own.split('.'))) if '.'.join(own.split('.')[:i]) in mods)
 edges[own]=deps
roots={'web_api','stockrl.__main__','stockrl.job_worker','stockrl.finrl.policy_learning.official_cli','stockrl.platform.kiwoom_worker'}
roots.update(module(v) for v in pyfiles if v.startswith(('scripts/','tests/')))
def reach(graph,initial):
 seen=set(initial);queue=list(seen)
 while queue:
  for item in graph.get(queue.pop(),()):
   if item not in seen:seen.add(item);queue.append(item)
 return seen
used=reach(edges,roots);orphan_py=[v for m,v in mods.items() if m not in used and not v.endswith('/__init__.py')]
front=[v for v in tracked if v.startswith('frontend/') and v.endswith(('.ts','.tsx','.css','.html'))];known=set(front);fedges={};unresolved=[]
for name in front:
 source=(R/name).read_text(encoding='utf-8-sig');deps=set()
 for value in re.findall(r"['\"]([^'\"\n]+)['\"]",source):
  if not value.startswith('.'):continue
  base=Path(os.path.normpath(str(Path(name).parent/value))).as_posix()
  target=next((v for v in (base,base+'.ts',base+'.tsx',base+'.css',base+'/index.ts',base+'/index.tsx') if v in known),None)
  if target:deps.add(target)
 fedges[name]=deps
froots={'frontend/src/main.tsx','frontend/vite.config.ts','frontend/playwright.config.ts','frontend/index.html'}|{v for v in front if v.startswith('frontend/tests/')}
fused=reach(fedges,froots);orphan_front=[v for v in front if v.startswith('frontend/src/') and v not in fused]
artifacts=[]
# Project caches only: never traverse environments, official vendor, saved code or Trash.
for base in ('backend','scripts','tests','frontend/src'):
 for directory,dirs,files in os.walk(R/base):
  dirs[:]=[d for d in dirs if d not in ('node_modules','saved_projects','.git')]
  if Path(directory).name=='__pycache__':
   dirs[:]=[]
   for file in files:
    path=Path(directory)/file
    if not file.endswith('.pyc'):continue
    source=path.parent.parent/(file.split('.',1)[0]+'.py')
    artifacts.append({'path':path.relative_to(R).as_posix(),'reason':'regenerated Python bytecode' if source.is_file() else 'bytecode left behind after source move','kind':'cache'})
dist=R/'frontend/dist';assets=dist/'assets';asset_files={v.name:v for v in assets.iterdir() if v.is_file()} if assets.is_dir() else {}
pattern=r'[A-Za-z0-9_][A-Za-z0-9_.-]*\.(?:js|css|svg|png|jpe?g|webp|woff2?|ttf|ico)'
def refs(text):return {v for v in re.findall(pattern,text) if v in asset_files}
asset_graph={}
for name,path in asset_files.items():asset_graph[name]=refs(path.read_text(encoding='utf8',errors='replace')) if path.suffix in ('.js','.css') else set()
entry=refs((dist/'index.html').read_text(encoding='utf8')) if (dist/'index.html').is_file() else set()
active=reach(asset_graph,entry)
if entry and any(v.endswith('.js') for v in entry):
 artifacts.extend({'path':p.relative_to(R).as_posix(),'reason':'not referenced by current dist/index.html and its transitive assets','kind':'obsolete_build'} for name,p in asset_files.items() if name not in active)
for relative in ('frontend/test-results','frontend/playwright-report','frontend/coverage','frontend/.cache','frontend/node_modules/.vite'):
 path=R/relative
 if path.is_dir() and not path.is_symlink():artifacts.append({'path':relative,'reason':'generated test/report/build cache; not application source','kind':'generated_folder'})
summary={'python_sources_investigated':len(pyfiles),'frontend_sources_investigated':len(front),'python_unreferenced_candidates':orphan_py,'frontend_unreferenced_candidates':orphan_front,'source_read_errors':errors,'current_build_assets':len(active),'obsolete_build_assets':sum(v['kind']=='obsolete_build' for v in artifacts),'project_cache_files':sum(v['kind']=='cache' for v in artifacts),'generated_folders':[v['path'] for v in artifacts if v['kind']=='generated_folder'],'preserved':['README documents','installed Python/Node dependencies','official vendor source','configs/data/runtime/model assets','saved REA original and inferred files','AGENTS.md existing local changes']}
temp=Path(os.environ['TEMP']);(temp/'platform_cleanup_audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');(temp/'platform_cleanup_artifacts.json').write_text(json.dumps(artifacts,ensure_ascii=False),encoding='utf8');print(json.dumps(summary,ensure_ascii=False))
