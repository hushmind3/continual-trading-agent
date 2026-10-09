"""FinRL-X data universe includes the exact observations required by enabled assets."""
from ..state_io import read_json,atomic_json


def prepare(settings):
    original=read_json(settings.resolve(settings.instruments))
    document={**original,"instruments":[dict(i) for i in original.get("instruments",[])]}
    present={i["symbol"] for i in document["instruments"]}
    from .integrated_asset import read_header
    model=settings.resolve(settings.expert_checkpoint)
    header=read_header(model) if model.is_file() else {}
    entries=[{**entry,"id":key,"universe":entry.get("stock_policy",{}).get("universe")} for key,entry in header.get("expert_mapping",{}).items()]
    selected=set(settings.enabled_experts)
    requirements={}
    for entry in entries:
        key=entry["id"]
        if selected and key not in selected:
            continue
        for symbol in entry.get("symbols") or entry.get("universe") or []:
            requirements.setdefault(symbol,[]).append(key)
    library=read_json(settings.state_dir/'expert-library.json')
    for key,entry in library.get('experts',{}).items():
        if key not in selected or not entry.get('input',{}).get('supported'):continue
        for symbol in entry['input'].get('universe') or []:requirements.setdefault(symbol,[]).append(key)
    references=[e["id"] for e in entries if e.get("backend") in ("chronos","timesfm") and (not selected or e["id"] in selected)]
    if references:requirements.setdefault("SPY",[]).extend(references)
    for symbol,required_by in sorted(requirements.items()):
        if symbol not in present:
            document["instruments"].append(dict(symbol=symbol,name=symbol,market="US",asset_class="equity",
                                                provider_symbol=symbol,interval="1m",required_by=required_by))
            present.add(symbol)
    destination=settings.state_dir/"feed-universe.json"
    if read_json(destination)!=document:atomic_json(document,destination)
    return destination
