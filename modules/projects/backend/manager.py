"""Project submenu registration and common execution lifecycle."""
from .handlers import router
from . import installer, runtime
from .store import LOCK
MENU = {'id': 'projects/manage', 'title': '프로젝트 관리', 'operations': ['projects/']}
register_host = runtime.register_host
busy_reason = installer.busy_reason
close = runtime.close


def reserve_restart():
    with LOCK, runtime.LOCK:
        installer.RESTARTING = True; runtime.RESTARTING = True
        if reason := busy_reason():
            cancel_restart(); raise RuntimeError(reason)


def cancel_restart():
    installer.RESTARTING = False; runtime.RESTARTING = False


router.add_event_handler('shutdown', close)
