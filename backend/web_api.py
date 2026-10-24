"""Platform entry: import the menu coordinator and expose one API."""
from api_context import app
from api_context import private_api
from api_context import FRONTEND_DIST
from api_context import StaticFiles
from api_context import Route
from api_context import UnifiedAPI
from api_context import GZipMiddleware
from api_context import system
from api_transport import local_writes
from api_transport import react_index
from menu_registry import register_api
from pathlib import Path
from remote_access import RemoteAccessMiddleware, ensure_remote_access_config

register_api(private_api,app)
from platform_context import register_controls
register_controls(private_api)
from menu_registry import bind
bind(private_api.routes)
app.router.routes.append(Route('/api',UnifiedAPI(),methods=['GET','POST']))
app.router.routes.append(Route('/api/{path:path}',UnifiedAPI(),methods=['GET','POST']))
app.mount('/assets',StaticFiles(directory=str(FRONTEND_DIST/'assets'),check_dir=False),name='react-assets')
app.get('/',include_in_schema=False)(react_index)
app.middleware('http')(local_writes)
app.add_middleware(GZipMiddleware)
remote_access_file = Path(__file__).resolve().parents[1] / 'runtime/platform/remote_access.json'
ensure_remote_access_config(remote_access_file)
app.add_middleware(RemoteAccessMiddleware, config_path=str(remote_access_file))
system.command_router=private_api
