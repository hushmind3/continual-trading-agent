"""Host lifecycle contract; no trading or agent implementation lives here."""
import os
from pathlib import Path
import subprocess
import threading
import time
import sys
import hashlib
import psutil
from platform_modules import ROOT, registrations
from platform_state_io import read_json, atomic_json

SERVER_RUNTIME=ROOT/'runtime/platform'

def apply_running(value=None):
    value=value or read_json(SERVER_RUNTIME/'apply.json')
    if value.get('status') not in ('pending','running'):return False
    try:
        process=psutil.Process(value['pid'])
        return abs(process.create_time()-value['process_created'])<.01 and any('start_server.py' in arg for arg in process.cmdline())
    except (psutil.Error,KeyError):return False

def apply_state():
    value=read_json(SERVER_RUNTIME/'apply.json',{'status':'pending','stages':[]})
    if value.get('status') in ('pending','running') and value.get('pid') and not apply_running(value):
        value={**value,'status':'failed','error':'변경 적용 프로세스가 종료됐습니다.'}
    return value

class HostSystem:
    command_router=None
    _restarting=False
    job_lock=threading.RLock()
    snapshot_cache={}
    @property
    def restarting(self):return self._restarting or os.environ.get('PLATFORM_READ_ONLY')=='1'
    @restarting.setter
    def restarting(self,value):self._restarting=bool(value)
    def notify(self,method):
        for metadata,entry in registrations():
            if callback:=getattr(entry,method,None):
                try:callback()
                except (OSError,RuntimeError) as exc:
                    __import__('logging').getLogger(__name__).warning('%s %s: %s',metadata['id'],method,exc)
    def cancel(self):self.notify('cancel_operations')
    def invalidate_states(self):self.notify('invalidate_states')

system=HostSystem()

def register_controls(router):
    """Global apply guards belong to the host, even when a business module is absent."""
    from fastapi import HTTPException
    from platform_modules import busy_reasons,lifecycle
    paths={'/api/system/blockers','/api/system/prepare-restart','/api/health','/api/state'}
    router.routes[:]=[route for route in router.routes if getattr(route,'path',None) not in paths]
    @router.get('/api/system/blockers')
    def blockers():return {'items':busy_reasons()}
    @router.post('/api/system/prepare-restart')
    def prepare_restart():
        if reasons:=busy_reasons():raise HTTPException(409,' · '.join(reasons))
        try:lifecycle('reserve_restart')
        except Exception as exc:raise HTTPException(409,str(exc)) from exc
        system.restarting=True
        lifecycle('close')
        return {'prepared':True,'items':[]}
    @router.get('/api/health')
    def health():return {'ok':True,'service':'project-platform','project':str(ROOT),'status':'ok',
                        'pid':os.getpid(),'python':sys.executable,'python_prefix':sys.prefix,
                        'deployment_id':os.environ.get('STOCKRL_APPLY_ID')}
    @router.get('/api/state')
    def state(views:str='[]',refresh_views:bool=False):
        import json
        try:wanted=json.loads(views)
        except (ValueError,TypeError):raise HTTPException(400,'조회할 화면 목록이 올바르지 않습니다.') from None
        if not isinstance(wanted,list) or any(not isinstance(value,str) for value in wanted):raise HTTPException(400,'화면 목록을 전달하세요.')
        result={'architecture':'finrl-unified-v3','updated_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                'views':{},'experts':{'items':[]},'job':{'running':False}}
        errors={item['id']:entry.load_error for item,entry in registrations() if getattr(entry,'load_error',None)}
        for metadata,entry in registrations():
            if callback:=getattr(entry,'snapshot',None):
                try:
                    snapshot=callback([value for value in wanted if value!='menu_catalog'],refresh_views)
                    system.snapshot_cache[metadata['id']]=snapshot
                except (OSError,RuntimeError) as exc:
                    errors[metadata['id']]=str(exc);snapshot=system.snapshot_cache.get(metadata['id'],{})
                result.update(snapshot)
        result['views']={**result.get('views',{})}
        result['module_errors']={**result.get('module_errors',{}),**errors}
        if 'menu_catalog' in wanted:
            from menu_registry import catalog
            result['views']['menu_catalog']={'data':catalog(router.routes),'error':None}
        index=ROOT/'frontend/dist/index.html'
        if index.is_file():result['frontend_revision']=hashlib.sha256(index.read_bytes()).hexdigest()
        return result
