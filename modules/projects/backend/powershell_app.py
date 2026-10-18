"""Discover and run original Windows installers without evaluating source at discovery."""
import json
import os
from pathlib import Path
import subprocess
import threading
from . import runtime,store

CANCELS={}


def executable():
    path=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    if not path.is_file():raise ValueError('이 설치 프로그램은 Windows PowerShell이 필요합니다.')
    return str(path)


def inspect(source,spec):
    script=store.owned(source,spec['script'])
    if not script.is_file() or script.suffix.lower()!='.ps1':raise ValueError('원본 Windows 설치 스크립트가 없습니다.')
    result=subprocess.run([executable(),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(Path(__file__).with_name('powershell_metadata.ps1')),str(script)],capture_output=True,text=True,encoding='utf8',timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('원본 설치 스크립트 확인 실패: '+result.stderr[-2000:])
    return json.loads(result.stdout.lstrip('\ufeff'))


def detect(source):
    candidates=[source/'install.ps1',*sorted((source/'windows').glob('install*.ps1')),*sorted((source/'scripts').glob('install*.ps1'))]
    scripts=[path for path in candidates if path.is_file()]
    if len(scripts)!=1:return None
    spec={'kind':'powershell','directory':'.','script':scripts[0].relative_to(source).as_posix()}
    inspect(source,spec)
    return spec


def state(record):
    if record.get('adapter',{}).get('kind')!='powershell':raise ValueError('Windows 설치 프로그램이 아닙니다.')
    source=Path(record['active_source'])
    file=source.parent/'setup-state.json';log=source.parent/'setup.log'
    value=json.loads(file.read_text(encoding='utf8')) if file.is_file() else {'state':'idle'}
    if value.get('state')=='running':
        import psutil
        try:alive=abs(psutil.Process(value['owner_pid']).create_time()-value['owner_created'])<.01
        except (KeyError,psutil.Error):alive=False
        if not alive:value.update(state='interrupted',error='서버 종료로 설치 확인이 끊겼습니다. 원본 설치 결과를 확인한 뒤 다시 실행하세요.')
    if log.is_file():
        with log.open('rb') as stream:
            stream.seek(0,2);stream.seek(max(0,stream.tell()-20000));value['log']=stream.read().decode('utf8',errors='replace')
    return value


def describe(record):
    if record.get('adapter',{}).get('kind')!='powershell':raise ValueError('Windows 설치 프로그램이 아닙니다.')
    return {**inspect(Path(record['active_source']),record['adapter']),'result':state(record)}


def start(record,values):
    if not isinstance(values,dict):raise ValueError('설치 옵션을 확인하세요.')
    metadata=describe(record);parameters=metadata['parameters']
    if set(values)-{item['name'] for item in parameters}:raise ValueError('원본에 없는 설치 옵션입니다.')
    source=Path(record['active_source']);command=[executable(),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(store.owned(source,record['adapter']['script']))]
    for parameter in parameters:
        name=parameter['name'];value=values.get(name,parameter.get('default'))
        if parameter['kind']=='switch':
            if value not in (None,False,True):raise ValueError(name+' 옵션은 켜기/끄기입니다.')
            if value:command+=['-'+name]
            continue
        if parameter['required'] and (value is None or not str(value).strip()):raise ValueError(name+' 값을 입력하세요.')
        if value is None or value=='':continue
        if not isinstance(value,(str,int,float)) or len(str(value))>4096:raise ValueError(name+' 값이 올바르지 않습니다.')
        if parameter['choices'] and str(value) not in parameter['choices']:raise ValueError(name+' 선택 값을 확인하세요.')
        command+=['-'+name,str(value)]
    import psutil
    status=source.parent/'setup-state.json';log=source.parent/'setup.log'
    from platform_state_io import atomic_json
    with runtime.LOCK:
        from . import installer
        if installer.JOBS or installer.RESTARTING or runtime.RESTARTING or runtime.ACTIVE:raise ValueError('진행 중인 작업이 끝난 뒤 설치하세요.')
        runtime.ACTIVE+=1
        cancelled=threading.Event();CANCELS[record['id']]=cancelled
        result={'state':'running','owner_pid':os.getpid(),'owner_created':psutil.Process().create_time()}
        try:atomic_json(result,status)
        except Exception:
            runtime.ACTIVE-=1;CANCELS.pop(record['id'],None);raise
    def run():
        try:
            from .installer import run_command
            log.write_text('',encoding='utf8')
            cache=source.parent/'setup-cache';cache.mkdir(exist_ok=True)
            run_command(command,source,log,cancelled,timeout=1800,environment={**record.get('environment',{}),'TEMP':str(cache),'TMP':str(cache)})
            result.update(state='complete',error='')
        except Exception as exc:result.update(state='failed',error=str(exc)[-2500:])
        finally:
            try:atomic_json(result,status)
            finally:
                with runtime.LOCK:runtime.ACTIVE-=1;CANCELS.pop(record['id'],None)
    threading.Thread(target=run,daemon=True).start()
    return result


def stop(key):
    with runtime.LOCK:
        if key not in CANCELS:raise ValueError("실행 중인 설치가 없습니다.")
        CANCELS[key].set()
    return {"requested":True}


def choose_folder():
    code="[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);Add-Type -AssemblyName System.Windows.Forms;$dialog=New-Object Windows.Forms.FolderBrowserDialog;$dialog.Description='설치 대상 폴더를 선택하세요.';$dialog.ShowNewFolderButton=$false;try{if($dialog.ShowDialog() -eq [Windows.Forms.DialogResult]::OK){[Console]::Write($dialog.SelectedPath)}}finally{$dialog.Dispose()}"
    import base64
    result=subprocess.run([executable(),'-NoProfile','-STA','-EncodedCommand',base64.b64encode(code.encode('utf-16le')).decode()],capture_output=True,text=True,encoding='utf8',timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('Windows 폴더 선택 창을 열지 못했습니다.')
    return {'path':result.stdout.strip()}
