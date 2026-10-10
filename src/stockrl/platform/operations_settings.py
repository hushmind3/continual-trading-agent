"""Operational fields reused from f153957; SAC settings stay in framework.py."""
from pathlib import Path
from types import SimpleNamespace
from ..framework import ROOT
from ..state_io import read_json,atomic_json

CONFIG_PATH=ROOT/'configs/local/operations.json'

def settings():
    values=read_json(CONFIG_PATH)
    model_dir=Path.home()/'Desktop'/'모델'
    # Original paper-account/collector defaults. No learning settings are copied.
    risk=SimpleNamespace(**{'fee':0.001,'slippage':0.0001,**values.get('risk',{})})
    data=SimpleNamespace(**{'poll_seconds':15,'timeout_seconds':10,**values.get('data',{})})
    resources=SimpleNamespace(expert_devices=values.get('expert_devices',{}),
        ram_reserve_gib=0,vram_reserve_gib=0,disk_reserve_gib=0)
    root=ROOT/'runtime/operations'
    root.mkdir(parents=True,exist_ok=True)
    return SimpleNamespace(registry_file=ROOT/'configs/experts.json',model_dir=model_dir,
        expert_checkpoint=str(model_dir/'champion.pt'),state_dir=root,
        resolve=lambda path:Path(path) if Path(path).is_absolute() else ROOT/path,
        resources=resources,risk=risk,data=data,symbols=values.get('symbols',[]))

def update(values):
    current=read_json(CONFIG_PATH)
    for name in ('risk','data','symbols','expert_devices'):
        if name in values:current[name]=values[name]
    atomic_json(current,CONFIG_PATH)
    return current
