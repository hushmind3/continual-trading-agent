"""Host-facing registration; no business packages are imported in the host."""
from pathlib import Path
from module_runtime import ModuleRuntime, proxy_router
bridge=ModuleRuntime(Path(__file__).resolve().parents[1])
_description=bridge.call('describe')
GROUP=_description['group']
router=proxy_router(bridge,_description)
busy_reason=bridge.busy_reason
close=bridge.close
def actions():return bridge.call('hook',{'name':'actions'}) or []
reserve_restart=bridge.reserve_restart
cancel_restart=bridge.cancel_restart

def cancel_operations():bridge.call("hook",{"name":"cancel"})
def invalidate_states():bridge.call("hook",{"name":"invalidate_states"})

def snapshot(views,refresh):
    import base64,json
    from urllib.parse import urlencode
    response=bridge.call('request',{'path':'/api/state','method':'GET','body':'','headers':{},
        'query':urlencode({'views':json.dumps(views),'refresh_views':str(refresh).lower()})})
    if response['status']!=200:raise RuntimeError('금융 상태 조회 실패: '+str(response['status']))
    return json.loads(base64.b64decode(response['body']))
