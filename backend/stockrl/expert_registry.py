"""Timestamp and JSON compatibility for frozen native runner definitions."""
from datetime import datetime,timezone
from .state_io import atomic_json as _write
from .state_io import read_json
from pathlib import Path
import copy

def utc_now():return datetime.now(timezone.utc).isoformat()
def atomic_json(path,value):_write(value,path)


def read_catalog(path=None):
    if path is None:path=Path.home()/'Desktop'/'모델'/'experts'/'expert_registry.json'
    path=Path(path);index=read_json(path)
    if index.get('format')!='expert_model_index_v1':return index or {'experts':{},'active':[]}
    root=path.resolve().parent
    result={key:copy.deepcopy(value) for key,value in index.items() if key not in ('format','models')}
    result['experts']={}
    for relative in index.get('models',[]):
        manifest=(root/relative).resolve()
        if not manifest.is_relative_to(root):raise ValueError('Model manifest outside Expert folder')
        model=read_json(manifest)
        for key,item in model.get('experts',{}).items():
            item=copy.deepcopy(item);package=(manifest.parent/item['package']['file']).resolve()
            if not package.is_relative_to(root):raise ValueError('Model package outside Expert folder')
            item['package']['file']=package.relative_to(root).as_posix();result['experts'][key]=item
        for field in ('optimizations','quantizations'):
            result.setdefault(field,{}).update(model.get(field,{}))
    result['active']=[key for key in result.get('active',[]) if key in result['experts']]
    return result


def write_catalog(value,path):
    path=Path(path);root=path.resolve().parent;models={};owners={}
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
