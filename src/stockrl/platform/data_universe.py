"""FinRL-X data universe includes the exact observations required by enabled assets."""
from ..state_io import read_json,atomic_json
from ..paths import EXPERT_ASSETS_DIR


def prepare(settings):
    original=read_json(settings.resolve(settings.instruments))
    document={**original,"instruments":[dict(i) for i in original.get("instruments",[])]}
    present={i["symbol"] for i in document["instruments"]}
    catalog=read_json(settings.state_dir/"expert_catalog.json") or read_json(EXPERT_ASSETS_DIR/"registry.template.json")
    entries=catalog.get("experts",[])
    selected=set(settings.enabled_experts)
    requirements={}
    for entry in entries:
        key=entry["id"]
        if selected and key not in selected:
            continue
        for symbol in entry.get("symbols") or entry.get("universe") or []:
            requirements.setdefault(symbol,[]).append(key)
    requirements.setdefault("SPY",[]).extend([k for k in ("chronos","timesfm") if not selected or k in selected])
    for symbol,required_by in sorted(requirements.items()):
        if symbol not in present:
            document["instruments"].append(dict(symbol=symbol,name=symbol,market="US",asset_class="equity",
                                                provider_symbol=symbol,interval="1m",required_by=required_by))
            present.add(symbol)
    destination=settings.state_dir/"feed-universe.json"
    atomic_json(document,destination)
    return destination
