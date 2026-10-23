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
