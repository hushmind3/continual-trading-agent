"""Operational fields reused from f153957; SAC settings stay in framework.py."""
from stockrl import CONFIG_DIR
import math
from pathlib import Path
from types import SimpleNamespace
from stockrl import ROOT
from stockrl.state_io import read_json
from stockrl.state_io import atomic_json

CONFIG_PATH=CONFIG_DIR / 'local/operations.json'

def settings():
    values=read_json(CONFIG_PATH)
    model_dir=Path.home()/'Desktop'/'모델'/'experts'
    # Original paper-account/collector defaults. No learning settings are copied.
    risk=SimpleNamespace(**{'fee':0.001,'slippage':0.0001,**values.get('risk',{})})
    data=SimpleNamespace(**{'poll_seconds':15,'timeout_seconds':10,**values.get('data',{})})
    resources=SimpleNamespace(expert_devices=values.get('expert_devices',{}),
        ram_reserve_gib=0,vram_reserve_gib=0,disk_reserve_gib=0)
    root=ROOT/'runtime/finance/operation_control'
    root.mkdir(parents=True,exist_ok=True)
    return SimpleNamespace(registry_file=model_dir/'expert_registry.json',model_dir=model_dir,
        expert_checkpoint=str(model_dir/'champion.pt'),state_dir=root,account_dir=ROOT/'runtime/finance/virtual_account_orders',library_dir=ROOT/'runtime/finance/moe',
        resolve=lambda path:Path(path) if Path(path).is_absolute() else ROOT/path,
        resources=resources,risk=risk,data=data,symbols=values.get('symbols',[]))

def update(values):
    current=read_json(CONFIG_PATH)
    for name in ('risk','data','symbols','expert_devices'):
        if name not in values:continue
        if name in ('risk','data','expert_devices'):
            if not isinstance(values[name],dict):raise ValueError(name+': 객체가 필요합니다.')
            current[name]={**current.get(name,{}),**values[name]}
        else:current[name]=values[name]
    for group,fields in (('risk',('fee','slippage')),('data',('poll_seconds','timeout_seconds'))):
        for name in fields:
            if name not in current.get(group,{}):continue
            value=current[group][name]
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 or (group=='data' and value==0):
                raise ValueError(group+'.'+name+': 유한한 '+('양수' if group=='data' else '0 이상의 값')+'가 필요합니다.')
    symbols=current.get('symbols',[])
    if not isinstance(symbols,list) or any(not isinstance(symbol,str) or not symbol.strip() for symbol in symbols):
        raise ValueError('symbols: 비어 있지 않은 종목 문자열 목록이 필요합니다.')
    devices=current.get('expert_devices',{})
    if not isinstance(devices,dict) or any(not isinstance(device,str) or not device.strip() for device in devices.values()):
        raise ValueError('expert_devices: 모델별 장치 문자열이 필요합니다.')
    atomic_json(current,CONFIG_PATH)
    return current
