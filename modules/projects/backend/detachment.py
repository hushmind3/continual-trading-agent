"""Prepare a runnable local folder, then move the actual program and owned data."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import zipfile
from . import installer,runtime,store


def builtin_record(key):
    from .builtin_packages import SUPPORTED
    from menu_registry import MODULE_ENTRIES
    if key not in SUPPORTED:raise ValueError('등록된 프로젝트가 없습니다.')
    item=next((item for item,entry in MODULE_ENTRIES if item['id']==key),None)
    if not item:raise ValueError('연결된 기본 모듈이 없습니다.')
    return {'id':key,'module_id':key,'builtin':True,'title':{'finance':'금융','rea':'REA 역공학','hermes':'헤르메스'}[key],'group_title':item['group']['title'],
            'repository':'플랫폼 기본 앱','url':'','stage':'ready','active_source':str(item['folder']),
            'adapter':{'kind':'builtin'},'data':item.get('data',[]),'environment':{}}


def long_path(path):
    value=str(Path(path).resolve())
    return '\\\\?\\'+value if os.name=='nt' and not value.startswith('\\\\?\\') else value


def copy_environment(source,target):
    def copy(file,destination):
        path=Path(file)
        if 'site-packages' in path.parts and path.suffix not in ('.pth','.pyc') and not path.name.startswith('_module_source'):
            try:os.link(file,destination);return destination
            except OSError:pass
        return shutil.copy2(file,destination)
    shutil.copytree(long_path(source),long_path(target),copy_function=copy,
        ignore=lambda folder,names:[name for name in names if name in {'__pycache__','.cache'} or (Path(folder)/name).is_symlink()])


def remove_temporary(path):
    if not path.resolve().is_relative_to(store.STATE.resolve()):raise ValueError('임시 폴더 경계 오류')
    if path.exists():shutil.rmtree(long_path(path))


def rewrite_settings(root,old,new):
    candidates=list((root/'modules').glob('*/configs/**/*.json'))
    candidates+=list((root/'runtime').glob('*/*/platform-settings.json'))
    def rewrite(value):
        if isinstance(value,list):return [rewrite(item) for item in value]
        if isinstance(value,dict):return {key:rewrite(item) for key,item in value.items()}
        if isinstance(value,str):
            for origin,replacement in ((str(old),str(new)),(old.as_posix(),new.as_posix())):
                if value==origin or value.startswith(origin+'\\') or value.startswith(origin+'/'):return replacement+value[len(origin):]
        return value
    for path in candidates:
        value=json.loads(path.read_text(encoding='utf8'));next_value=rewrite(value)
        if next_value!=value:path.write_text(json.dumps(next_value,ensure_ascii=False,indent=2),encoding='utf8')


def prepare(record,target,progress):
    """Reuse existing exporters internally. No browser download or user setup."""
    from . import packages
    result=packages.export(record['id'],_preparing=True)
    archive=store.project_folder(record)/'exports'/result['filename']
    try:
        with zipfile.ZipFile(archive) as bundle:bundle.extractall(target)
    finally:archive.unlink(missing_ok=True)
    try:archive.parent.rmdir()
    except OSError:pass
    progress('실행 환경을 앱 폴더 안에 준비하고 있습니다.')
    if record.get('builtin') or record['adapter']['kind'] in ('fastapi','python-cli'):
        environment=target/('.venv/platform' if record.get('builtin') else '.runtime/venv')
        copy_environment(store.ROOT/'.venv/platform',environment)
    (target/'.runtime').mkdir(exist_ok=True)
    (target/'실행.cmd').write_text('@echo off\ncd /d "%~dp0"\npy -X utf8 run.py run\npause\n',encoding='utf8')
    launcher=target/'실행.command'
    launcher.write_text('#!/bin/zsh\nset -e\ncd "${0:A:h}"\nexport PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"\npython3 run.py run\n',encoding='utf8')
    launcher.chmod(0o755)
    if record.get('builtin'):
        node=target/'node_modules'
        shutil.copytree(long_path(store.ROOT/'node_modules'),long_path(node),copy_function=os.link,
            ignore=lambda folder,names:[name for name in names if name=='.cache' or (Path(folder)/name).is_symlink()])
        progress('독립 화면을 준비하고 있습니다.')
        log=target/'preparation.log'
        with log.open('w',encoding='utf8') as output:
            result=subprocess.run(['node',str(node/'vite/bin/vite.js'),'build'],cwd=target/'frontend',
                stdout=output,stderr=subprocess.STDOUT,timeout=120)
        if result.returncode:raise ValueError('독립 화면 준비 실패: '+log.read_text(encoding='utf8',errors='replace')[-1800:])
        if record['id']=='hermes':
            engine=store.ROOT/'runtime/shared/engines/llama.cpp'
            if engine.is_dir():shutil.copytree(engine,target/'runtime/shared/engines/llama.cpp')
        remove_temporary(target/'modules'/record['id'])
    else:remove_temporary(target/'source')
    return target


def start(key):
    from . import lifecycle
    with store.LOCK,runtime.LOCK:
        try:record=store.read(key)
        except ValueError:record=builtin_record(key)
        if record.get('stage')=='removed':return installer.public(record)
        if not record.get('active_source'):raise ValueError('설치된 프로그램이 없습니다. 제거로 정리하세요.')
        lifecycle.idle(record)
        before=dict(record);record.update(stage='detaching',error='',detail='분리할 프로그램과 실행 환경을 준비합니다.')
        store.save(record);installer.JOBS[key]=threading.Event()
    def run():
        target=store.owned(store.project_folder(record),'standalone')
        moves=[];created=not target.exists()
        def progress(message):
            record['detail']=message;store.save(record)
        try:
            if created:
                # Keep the job guard active while preparing the independent host.
                prepare(record,target,progress)
            with store.LOCK,runtime.LOCK:
                folder=lifecycle.module_folder(record)
                if not folder or not folder.is_dir():raise ValueError('연결된 프로그램 폴더가 없습니다.')
                from .agent_tasks import link
                link(record,remove=True)
                destination=target/'modules'/key if record.get('builtin') else target/'connector'
                destination.parent.mkdir(parents=True,exist_ok=True)
                folder.rename(destination);moves.append((folder,destination))
                if record.get('builtin'):
                    for relative in record.get('data',[]):
                        source=store.owned(store.ROOT,relative);dest=store.owned(target,relative)
                        if not source.exists():continue
                        if dest.exists():raise ValueError('분리 대상 데이터와 같은 이름의 파일이 있습니다: '+relative)
                        dest.parent.mkdir(parents=True,exist_ok=True);source.rename(dest);moves.append((source,dest))
                        if dest.is_file() and dest.suffix in ('.db','.sqlite','.sqlite3'):
                            for suffix in ('-wal','-shm'):
                                sidecar=Path(str(source)+suffix)
                                if sidecar.exists():
                                    moved=Path(str(dest)+suffix);sidecar.rename(moved);moves.append((sidecar,moved))
                    rewrite_settings(target,store.ROOT,target)
                else:
                    source=Path(record['active_source']);dest=target/'source'
                    if source.resolve()!=dest.resolve():source.rename(dest);moves.append((source,dest))
                    record['active_source']=str(dest)
                    (target/'.runtime/environment.json').write_text(json.dumps(record.get('environment',{})),encoding='utf8')
                record.update(stage='removed',standalone_path=str(target),detached_module=str(destination),
                    detached_moves=[{'original':str(a),'detached':str(b)} for a,b in moves],
                    detail='분리 완료 · 이 폴더의 실행.cmd(Windows)·실행.command(Mac)로 실행하거나 다시 연결할 수 있습니다.')
                store.save(record)
        except Exception as exc:
            with store.LOCK:
                rollback=[]
                if record.get('builtin') and moves:
                    try:rewrite_settings(target,target,store.ROOT)
                    except Exception as error:rollback.append(str(error))
                for origin,destination in reversed(moves):
                    if destination.exists():
                        try:
                            if origin.exists():raise ValueError('복원 위치 충돌: '+str(origin))
                            origin.parent.mkdir(parents=True,exist_ok=True);destination.rename(origin)
                        except Exception as error:rollback.append(str(error))
                if created and not rollback:remove_temporary(target)
                before.update(error='분리 준비 실패: '+str(exc)+(' · 파일 보존: '+'; '.join(rollback) if rollback else ''))
                if rollback:before['standalone_path']=str(target)
                store.save(before)
                from menu_registry import MODULE_ENTRIES
                entry=next((entry for item,entry in MODULE_ENTRIES if item['id']==record.get('module_id')),None)
                if entry and (cancel:=getattr(entry,'cancel_restart',None)):cancel()
        finally:
            with store.LOCK:installer.JOBS.pop(key,None)
    initial=installer.public(dict(record))
    threading.Thread(target=run,daemon=True).start()
    return initial


def reconnect_builtin(record):
    target=store.owned(store.project_folder(record),'standalone')
    import psutil
    for process in psutil.process_iter(['pid','cwd']):
        if process.info['pid']==os.getpid():continue
        try:
            if process.info['cwd'] and Path(process.info['cwd']).resolve().is_relative_to(target):raise ValueError('분리된 앱을 종료한 뒤 다시 연결하세요.')
        except (psutil.Error,OSError):continue
    moves=[(Path(item['original']),Path(item['detached'])) for item in record['detached_moves']]
    for original,detached in moves:
        if not original.resolve().is_relative_to(store.ROOT.resolve()) or not detached.resolve().is_relative_to(target):raise ValueError('재연결 경로 경계 오류')
        if original.exists():raise ValueError('원래 위치에 같은 이름의 파일이 생겼습니다. 분리본은 보관했습니다: '+str(original))
    rewrite_settings(target,target,store.ROOT)
    completed=[]
    try:
        for original,detached in moves:
            original.parent.mkdir(parents=True,exist_ok=True);detached.rename(original);completed.append((original,detached))
        record.update(stage='awaiting_activation',active_source=str(store.ROOT/'modules'/record['id']),standalone_path='',detached_module='',error='',detail='프로그램과 데이터를 원래 위치로 다시 연결합니다.')
        store.save(record)
    except Exception:
        for original,detached in reversed(completed):original.rename(detached)
        rewrite_settings(target,store.ROOT,target)
        raise
    # A user may have edited the independent shell too; quarantine the remaining
    # template instead of discarding those files during reconnection.
    relative=target.resolve().relative_to(store.ROOT.resolve())
    backup=store.ROOT/'휴지통'/relative
    if backup.exists():backup=backup.with_name(backup.name+'-'+str(time.time_ns()))
    backup.parent.mkdir(parents=True,exist_ok=True);target.rename(backup)
    from menu_registry import MODULE_ENTRIES
    entry=next((entry for item,entry in MODULE_ENTRIES if item['id']==record['module_id']),None)
    if entry and (cancel:=getattr(entry,'cancel_restart',None)):cancel()
    return installer.public(record)
