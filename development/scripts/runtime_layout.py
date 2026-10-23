"""One-time, reversible moves from legacy runtime names to menu-owned paths.

Call migrate(root) only after stopping the API, watchdog and their workers.
Model weights are moved without deserializing them. No live operations start.
"""
from pathlib import Path
import json
import shutil

PATHS=(
    ('runtime/finance/policy_learning/framework-jobs','runtime/finance/all_backend_features/results'),
    ('runtime/official/framework-jobs','runtime/finance/all_backend_features/results'),
    ('runtime/experts/engines','runtime/shared/engines'),
    ('runtime/experts','runtime/finance/moe'),
    ('runtime/official','runtime/finance/policy_learning'),
    ('runtime/operations','runtime/finance/operation_control'),
    ('runtime/rea','runtime/rea/program_analysis'),
    ('runtime/verification','runtime/shared/verification'),
    ('backend/rea/project_explorer/saved_projects','runtime/rea/project_explorer/projects'),
)
SERVER_FILES=('apply.json','applied-sources.json','apply-build.log','apply-launch.log',
    'server-start.lock','server-watchdog.json','server-watchdog.lock','server-watchdog.log',
    'server-watchdog.stop','server.json','server.stderr.log','server.stdout.log',
    'api.stderr.log','api.stdout.log','frontend.stderr.log','frontend.stdout.log')


def rewrite(value,root):
    if isinstance(value,dict):
        result={key:rewrite(item,root) for key,item in value.items()}
        if result.get('command')=='framework' and str(result.get('output','')).startswith('framework-jobs/'):
            result['output']=str(root/'runtime/finance/all_backend_features/results'/result['output'].split('/',1)[1])
        return result
    if isinstance(value,list):return [rewrite(item,root) for item in value]
    if not isinstance(value,str):return value
    normalized=value.replace('\\','/')
    substitutions=[('runtime/official/'+name,'runtime/platform/'+name) for name in SERVER_FILES]
    substitutions += [('runtime/operations/paper-account.json','runtime/finance/virtual_account_orders/paper-account.json'),
        ('runtime/operations/library-job.json','runtime/finance/moe/library-job.json'),*PATHS]
    for old,new in substitutions:
        for prefix,replacement in ((str(root/old).replace('\\','/'),str(root/new).replace('\\','/')),(old,new)):
            if normalized==prefix or normalized.startswith(prefix+'/'):
                result=replacement+normalized[len(prefix):]
                return result.replace('/','\\') if '\\' in value else result
    return value


def metadata_files(root):
    # Bounded control files only: copied models and extracted projects can contain
    # millions of source files; walking those trees is neither needed nor safe.
    for menu in ('operation_control','virtual_account_orders','policy_learning','moe'):
        folder=root/'runtime/finance'/menu
        for pattern in ('*.json','jobs/*.json','policies/*/*.json','champions/*/*.json'):
            for file in folder.glob(pattern):
                if file.stat().st_size<=4*1024*1024:yield file
    yield from (root/'runtime/rea/project_explorer/projects').glob('*/project.json')


def migrate(root,dry_run=False):
    root=Path(root).resolve();plan=[]
    for name in SERVER_FILES:
        for suffix in ('','.lock'):
            plan.append((root/'runtime/official'/(name+suffix),root/'runtime/platform'/(name+suffix)))
    for name,menu in (('paper-account.json','virtual_account_orders'),('library-job.json','moe')):
        for suffix in ('','.lock'):
            plan.append((root/'runtime/operations'/(name+suffix),root/'runtime/finance'/menu/(name+suffix)))
    for old,new in PATHS:
        source=root/old;target=root/new
        if source.is_dir():
            reserved={item[0] for item in plan}|{root/old_root for old_root,_ in PATHS if old_root!=old}
            plan.extend((child,target/child.name) for child in source.iterdir()
                if child not in reserved and not any(item.is_relative_to(child) for item in reserved)
                and not (old=='runtime/rea' and child.name in ('program_analysis','project_explorer')))
        elif source.exists():plan.append((source,target))
    plan=[(source,target) for source,target in plan if source.exists()]
    for source,target in plan:
        if not source.resolve().is_relative_to(root) or not target.resolve().is_relative_to(root):
            raise ValueError('Runtime move escapes project')
        if source.is_symlink() or target.exists():raise ValueError('Runtime target collision: '+str(target))
    if dry_run:return {'planned':len(plan)}
    moved=[];edited=[]
    try:
        for source,target in plan:
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.move(str(source),str(target));moved.append((source,target))
        # Only generated control metadata: never extracted source, user chats or model weights.
        for file in metadata_files(root):
            try:
                original=file.read_text(encoding='utf8');value=json.loads(original)
            except (ValueError,OSError):continue
            revised=rewrite(value,root)
            if revised!=value:
                edited.append((file,original))
                temporary=file.with_suffix('.migration.tmp')
                temporary.write_text(json.dumps(revised,ensure_ascii=False,indent=2),encoding='utf8')
                temporary.replace(file)
    except Exception:
        for file,original in reversed(edited):file.write_text(original,encoding='utf8')
        for source,target in reversed(moved):
            source.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(target),str(source))
        raise
    for old,_ in PATHS:
        folder=root/old
        if folder.is_dir() and not any(folder.iterdir()):folder.rmdir()
    return {'moved':len(moved),'metadata_updated':len(edited)}
