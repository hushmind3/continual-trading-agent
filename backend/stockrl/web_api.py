"""Platform entry: import the menu coordinator and expose one API."""
from .api_context import app,private_api,FRONTEND_DIST,StaticFiles,Route,UnifiedAPI,GZipMiddleware,system
from .api_transport import local_writes,react_index
from .menu_registry import register_api

register_api(private_api)
app.router.routes.append(Route('/api',UnifiedAPI(),methods=['GET','POST']))
app.mount('/assets',StaticFiles(directory=str(FRONTEND_DIST/'assets'),check_dir=False),name='react-assets')
app.get('/',include_in_schema=False)(react_index)
app.middleware('http')(local_writes)
app.add_middleware(GZipMiddleware)
system.command_router=private_api
