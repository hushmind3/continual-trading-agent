"""One-time, reversible moves from legacy runtime names to menu-owned paths.

Call migrate(root) only after stopping the API, watchdog and their workers.
Model weights are moved without deserializing them. No live operations start.
"""
from pathlib import Path
import json
import shutil

PATHS=(
    ('runtime/experts/engines','runtime/shared/engines'),
    ('runtime/verification','runtime/shared/verification'),
)
SERVER_FILES=('apply.json','applied-sources.json','apply-build.log','apply-launch.log',
    'server-start.lock','server-watchdog.json','server-watchdog.lock','server-watchdog.log',
    'server-watchdog.stop','server.json','server.stderr.log','server.stdout.log',
    'api.stderr.log','api.stdout.log','frontend.stderr.log','frontend.stdout.log')


def rewrite(value,root):
    if isinstance(value,dict):
        result={key:rewrite(item,root) for key,item in value.items()}
        return result
    if isinstance(value,list):return [rewrite(item,root) for item in value]
    if not isinstance(value,str):return value
    normalized=value.replace('\\','/')
    substitutions=[('runtime/official/'+name,'runtime/platform/'+name) for name in SERVER_FILES]
    for old,new in substitutions:
        for prefix,replacement in ((str(root/old).replace('\\','/'),str(root/new).replace('\\','/')),(old,new)):
            if normalized==prefix or normalized.startswith(prefix+'/'):
                result=replacement+normalized[len(prefix):]
                return result.replace('/','\\') if '\\' in value else result
    return value


def metadata_files(root):
    return ()

def migrate(root,dry_run=False):
    root=Path(root).resolve();plan=[]
    for name in SERVER_FILES:
        for suffix in ('','.lock'):
            plan.append((root/'runtime/official'/(name+suffix),root/'runtime/platform'/(name+suffix)))
    for old,new in PATHS:
        source=root/old;target=root/new
        if source.is_dir():
            reserved={item[0] for item in plan}|{root/old_root for old_root,_ in PATHS if old_root!=old}
            plan.extend((child,target/child.name) for child in source.iterdir()
                if child not in reserved and not any(item.is_relative_to(child) for item in reserved)
                )
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
