"""프로젝트 탐색 — existing API handlers."""
from __future__ import annotations
from fastapi import APIRouter
from api_transport import FiniteJSONResponse
from fastapi import HTTPException

router=APIRouter(default_response_class=FiniteJSONResponse)

@router.get('/api/rea/projects')
def rea_projects():
    from rea.project_explorer.projects import catalog
    return catalog()


@router.get('/api/rea/project/tree')
def rea_project_tree(id:str,path:str=''):
    from rea.project_explorer.projects import tree
    try:return tree(id,path)
    except (OSError,ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc)) from exc


@router.get('/api/rea/project/file')
def rea_project_file(id:str,path:str):
    from rea.project_explorer.projects import read_file
    try:return read_file(id,path)
    except (OSError,ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc)) from exc


@router.post('/api/rea/project/open')
def rea_project_open(request:dict):
    from rea.project_explorer.projects import open_folder
    try:return open_folder(request.get('id'))
    except (OSError,ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc)) from exc

