"""Host HTTP context; no finance, REA or agent business libraries."""
import json
from fastapi import APIRouter,FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.routing import Route
from starlette.middleware.gzip import GZipMiddleware
from platform_modules import ROOT
from api_transport import FiniteJSONResponse,UnifiedAPI
from platform_context import system,apply_running,apply_state
app=FastAPI(title='Local project platform',version='2',default_response_class=FiniteJSONResponse)
private_api=APIRouter(default_response_class=FiniteJSONResponse)
FRONTEND_DIST=ROOT/'frontend/dist'
