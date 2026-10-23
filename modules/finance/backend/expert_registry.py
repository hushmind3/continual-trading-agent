"""Timestamp and JSON compatibility for frozen native runner definitions."""
from datetime import datetime,timezone
from .state_io import atomic_json as _write
from .state_io import read_json
from pathlib import Path
import copy
import json
from contextlib import contextmanager
from contextvars import ContextVar

_catalog_reads=ContextVar('expert_catalog_reads',default=None)

@contextmanager
def catalog_read_scope():
    """Share one validated registry snapshot within a single read-only response."""
    token=_catalog_reads.set({})
    try:yield
    finally:_catalog_reads.reset(token)

def read_catalog(path=None):
    if path is None:path=Path.home()/'Desktop'/'모델'/'experts'/'expert_registry.json'
    cache=_catalog_reads.get();key=str(Path(path).absolute())
    if cache is None:return _load_catalog(path)
    if key not in cache:cache[key]=_load_catalog(path)
    return cache[key]

def utc_now():return datetime.now(timezone.utc).isoformat()
def atomic_json(path,value):_write(value,path)


def _load_catalog(path):
    path=Path(path)
    try:index=json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:index={}
    except (OSError,ValueError) as exc:raise ValueError('Expert registry JSON cannot be read: '+str(path)) from exc
    if not isinstance(index,dict):raise ValueError('Expert registry JSON must be an object: '+str(path))
    if index.get('format')!='expert_model_index_v1':return index or {'experts':{},'active':[]}
    root=path.resolve().parent
    result={key:copy.deepcopy(value) for key,value in index.items() if key not in ('format','models')}
    result['experts']={}
    for relative in index.get('models',[]):
        manifest=(root/relative).resolve()
        if not manifest.is_relative_to(root):raise ValueError('Model manifest outside Expert folder')
        try:model=json.loads(manifest.read_text(encoding='utf-8'))
        except (OSError,ValueError) as exc:raise ValueError('Model registration JSON cannot be read: '+str(manifest)) from exc
        if not isinstance(model,dict) or not isinstance(model.get('experts',{}),dict):raise ValueError('Invalid model registration JSON: '+str(manifest))
        for key,item in model.get('experts',{}).items():
            item=copy.deepcopy(item);package=(manifest.parent/item['package']['file']).resolve()
            if not package.is_relative_to(root):raise ValueError('Model package outside Expert folder')
            item['package']['file']=package.relative_to(root).as_posix();result['experts'][key]=item
        for field in ('optimizations','quantizations'):
            result.setdefault(field,{}).update(model.get(field,{}))
    result['active']=[key for key in result.get('active',[]) if key in result['experts']]
    return result


def write_catalog(value,path,*,removed_ids=()):
    path=Path(path);root=path.resolve().parent;models={};owners={}
    previous=read_catalog(path)
    missing=set(previous.get('experts',{}))-set(value.get('experts',{}))-set(removed_ids)
    if missing:raise ValueError('Expert registration would be lost without a delete request: '+', '.join(sorted(missing)))
    for key,original in value.get('experts',{}).items():
        item=copy.deepcopy(original);package=(root/item['package']['file']).resolve()
        if not package.is_relative_to(root):raise ValueError('Model package outside Expert folder')
        manifest=package.parent/'expert.json';relative=manifest.relative_to(root).as_posix()
        if manifest.exists() and read_json(manifest).get('format')!='expert_model_metadata_v1':raise ValueError('Existing model JSON collision')
        model=models.setdefault(relative,{'format':'expert_model_metadata_v1','experts':{}})
        item['package']['file']=package.name;model['experts'][key]=item;owners[key]=model
    index={key:copy.deepcopy(item) for key,item in value.items() if key!='experts'}
    for field in ('optimizations','quantizations'):
        retained={}
        for key,item in index.pop(field,{}).items():
            if key in owners:owners[key].setdefault(field,{})[key]=item
            else:retained[key]=item
        if retained:index[field]=retained
    index.update(format='expert_model_index_v1',models=sorted(models))
    for relative in set(read_json(path).get('models',[]))-set(models):
        manifest=(root/relative).resolve()
        if not manifest.is_relative_to(root):raise ValueError('Model manifest outside Expert folder')
        if read_json(manifest).get('format')=='expert_model_metadata_v1':_write({'format':'expert_model_metadata_v1','experts':{}},manifest)
    for relative,model in models.items():_write(model,root/relative)
    _write(index,path)
