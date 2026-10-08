"""Read the selected MoE's existing trainable state without loading frozen bodies."""
import hashlib
import torch
from .expert_packages import HEADER_FORMAT


def load_moe_head(path):
    saved=torch.load(path,map_location="cpu",weights_only=True,mmap=True)
    if saved.get("format") not in ("registered_vertical_trading_moe_v1",HEADER_FORMAT):
        raise ValueError("선택한 파일은 기존 Champion MoE 형식이 아닙니다.")
    config={k:saved["config"][k] for k in ("feature_sizes","stock_policy_ids","assembly_routing","router_family") if k in saved["config"]}
    state={k:v.clone() for k,v in saved["state_dict"].items() if k.startswith(("controller.","adapters."))}
    state={k.replace("calibration.weight","scale").replace("calibration.bias","bias"):
           (v.diagonal() if k.endswith("calibration.weight") else v) for k,v in state.items()}
    digest=hashlib.sha256()
    for key,value in state.items():
        digest.update(key.encode()); digest.update(value.contiguous().view(torch.uint8).numpy().tobytes())
    spec={"config":config,"expert_ids":sorted(saved["expert_mapping"]),
          "source_updates":int(saved.get("optimizer_updates",0)),"source_head_sha256":digest.hexdigest(),
          "source_model":str(path),"source_model_bytes":path.stat().st_size}
    if saved.get('format')==HEADER_FORMAT:
        spec.update(source_format=HEADER_FORMAT,expert_packages=saved['expert_packages'],
                    active_experts=saved.get('active_experts',sorted(saved['expert_mapping'])))
    return spec,state


def validate_source(saved_spec, selected_spec):
    keys=("expert_ids","config","source_head_sha256","expert_packages") if selected_spec.get('source_format')==HEADER_FORMAT else ("expert_ids", "config", "source_head_sha256", "source_model_bytes")
    for key in keys:
        if saved_spec.get(key) != selected_spec.get(key):
            raise ValueError("저장된 정책과 선택한 원본 MoE가 다릅니다. 해당 모델의 운영 상태 위치를 사용하세요.")
