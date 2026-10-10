"""Versioned SB3 SAC policies assembled with frozen, per-Expert MoE inputs."""
from __future__ import annotations

import hashlib
import copy
import json
import shutil
from pathlib import Path

import numpy as np
import torch
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor

from ..framework import ROOT, sac_example
from ..state_io import atomic_json, read_json
from .expert_packages import load_package
from .expert_contracts import input_contract

MODEL_DIR = Path.home() / "Desktop" / "모델"
EXPERT_FEATURES = 64


def _key(value):
    return hashlib.sha1(value.encode("utf8")).hexdigest()[:16]


class GroupedQueryAttention(torch.nn.Module):
    """GQA shapes follow the inspected PRO tensors: 16 query / 4 KV / 64D."""

    def __init__(self, hidden_size, query_heads, key_value_heads, head_dim):
        super().__init__()
        from torch import nn
        self.query_heads=int(query_heads);self.key_value_heads=int(key_value_heads);self.head_dim=int(head_dim)
        if self.query_heads%self.key_value_heads:
            raise ValueError("GQA query head 수는 KV head 수의 배수여야 합니다.")
        self.q_proj=nn.Linear(hidden_size,self.query_heads*self.head_dim,bias=False)
        self.k_proj=nn.Linear(hidden_size,self.key_value_heads*self.head_dim,bias=False)
        self.v_proj=nn.Linear(hidden_size,self.key_value_heads*self.head_dim,bias=False)
        self.o_proj=nn.Linear(self.query_heads*self.head_dim,hidden_size,bias=False)

    def forward(self,query,tokens):
        batch,query_count,_=query.shape;token_count=tokens.shape[1]
        q=self.q_proj(query).view(batch,query_count,self.query_heads,self.head_dim).transpose(1,2)
        k=self.k_proj(tokens).view(batch,token_count,self.key_value_heads,self.head_dim).transpose(1,2)
        v=self.v_proj(tokens).view(batch,token_count,self.key_value_heads,self.head_dim).transpose(1,2)
        repeat=self.query_heads//self.key_value_heads
        k=k.repeat_interleave(repeat,dim=1);v=v.repeat_interleave(repeat,dim=1)
        weights=torch.softmax(torch.matmul(q,k.transpose(-2,-1))*(self.head_dim**-0.5),dim=-1)
        attended=torch.matmul(weights,v).transpose(1,2).contiguous().view(batch,query_count,self.query_heads*self.head_dim)
        return self.o_proj(attended)


class RMSNorm(torch.nn.Module):
    def __init__(self,width,eps=1e-6):
        super().__init__();self.weight=torch.nn.Parameter(torch.ones(width));self.eps=float(eps)

    def forward(self,value):
        scale=torch.rsqrt(value.float().pow(2).mean(dim=-1,keepdim=True)+self.eps).to(value.dtype)
        return value*scale*self.weight


class ChampionExtractor(BaseFeaturesExtractor):
    """Dynamic Expert adapters with a fixed SAC-facing latent width."""

    def __init__(self, observation_space, base_dim, expert_ids, roles, hidden_size=512,
                 market_heads=16, market_kv_heads=4, market_head_dim=64, intermediate_size=1792,
                 norm_eps=1e-6, policy_dim=64, policy_heads=4):
        self.base_dim = int(base_dim)
        self.expert_ids = list(expert_ids)
        self.roles = dict(roles)
        self.hidden_size = int(hidden_size)
        self.policy_dim = int(policy_dim)
        features_dim = self.base_dim + self.hidden_size + self.policy_dim
        super().__init__(observation_space, features_dim)
        from torch import nn
        self.market_ids = [key for key in self.expert_ids if self.roles[key] == "market"]
        self.policy_ids = [key for key in self.expert_ids if self.roles[key] == "action"]
        self.market_adapters = nn.ModuleDict({_key(key): nn.Linear(EXPERT_FEATURES, self.hidden_size) for key in self.market_ids})
        self.market_routers = nn.ModuleDict({_key(key): nn.Linear(self.hidden_size, 1) for key in self.market_ids})
        self.market_attention = GroupedQueryAttention(self.hidden_size,market_heads,market_kv_heads,market_head_dim)
        self.market_attention_norm=RMSNorm(self.hidden_size,norm_eps)
        self.market_ffn_norm=RMSNorm(self.hidden_size,norm_eps)
        self.market_ffn_in=nn.Linear(self.hidden_size,int(intermediate_size),bias=False)
        self.market_ffn_out=nn.Linear(int(intermediate_size),self.hidden_size,bias=False)
        self.policy_adapters = nn.ModuleDict({_key(key): nn.Linear(EXPERT_FEATURES, self.policy_dim) for key in self.policy_ids})
        self.policy_routers = nn.ModuleDict({_key(key): nn.Linear(self.policy_dim, 1) for key in self.policy_ids})
        self.policy_attention = nn.MultiheadAttention(self.policy_dim, policy_heads, batch_first=True)
        self.account_context = nn.Linear(16, self.policy_dim)
        self.controller_norm = nn.LayerNorm(self.policy_dim)

    def forward(self, observations):
        base = observations[:, :self.base_dim]
        count = len(self.expert_ids)
        raw = observations[:, self.base_dim:self.base_dim + count * EXPERT_FEATURES].reshape(observations.shape[0], count, EXPERT_FEATURES)
        account_start = self.base_dim + count * EXPERT_FEATURES
        account = observations[:, account_start:account_start + 16]
        zero_market = observations.new_zeros((observations.shape[0], self.hidden_size))
        zero_policy = observations.new_zeros((observations.shape[0], self.policy_dim))
        market_tokens = [self.market_adapters[_key(key)](raw[:, i]) for i, key in enumerate(self.expert_ids) if key in self.market_ids]
        policy_tokens = [self.policy_adapters[_key(key)](raw[:, i]) for i, key in enumerate(self.expert_ids) if key in self.policy_ids]
        if market_tokens:
            tokens = torch.stack(market_tokens, dim=1)
            logits = torch.cat([self.market_routers[_key(key)](token) for key, token in zip(self.market_ids, market_tokens)], dim=1)
            weights = logits.softmax(dim=1)
            tokens=self.market_attention_norm(tokens)
            query = (tokens * weights.unsqueeze(-1)).sum(dim=1, keepdim=True)
            attended=self.market_attention(query,tokens)[:,0]
            market=query[:,0]+attended
            market=market+self.market_ffn_out(torch.nn.functional.silu(self.market_ffn_in(self.market_ffn_norm(market))))
        else:
            market = zero_market
        if policy_tokens:
            tokens = torch.stack(policy_tokens, dim=1)
            logits = torch.cat([self.policy_routers[_key(key)](token) for key, token in zip(self.policy_ids, policy_tokens)], dim=1)
            weights = logits.softmax(dim=1)
            tokens = tokens * weights.unsqueeze(-1) * len(policy_tokens)
            query = tokens.mean(dim=1, keepdim=True)
            policy, _ = self.policy_attention(query, tokens, tokens)
            policy = policy[:, 0]
        else:
            policy = zero_policy
        policy = self.controller_norm(policy + self.account_context(account))
        return torch.cat((base, market, policy), dim=1)


def _original_report():
    path = MODEL_DIR / "champion.pt"
    report = {"path": str(path), "exists": path.is_file(), "read_only": True}
    if not path.is_file():
        return report
    source = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    state = source.get("state_dict", {})
    config = source.get("config", {}).get("central", {})
    q_shape = list(state.get("controller.market_block.attention.q_proj.weight", torch.empty(0)).shape)
    k_shape = list(state.get("controller.market_block.attention.k_proj.weight", torch.empty(0)).shape)
    static_prefixes=("controller.market_block.","controller.policy_block.","controller.market_projection.",
        "controller.market_context.","controller.output_norm.","controller.allocation.","controller.cash.","controller.target_prior_gain")
    dynamic_prefixes=("adapters.","controller.router.","controller.context_routers.","controller.projections.",
        "controller.policy_adapters.","controller.policy_router.")
    static_parameters=sum(t.numel() for name,t in state.items() if torch.is_tensor(t) and name.startswith(static_prefixes))
    dynamic_parameters=sum(t.numel() for name,t in state.items() if torch.is_tensor(t) and name.startswith(dynamic_prefixes))
    dynamic_by_expert={}
    for name,tensor in state.items():
        if not torch.is_tensor(tensor) or not name.startswith(dynamic_prefixes):continue
        parts=name.split(".");expert=parts[1] if parts[0]=="adapters" else parts[2]
        dynamic_by_expert[expert]=dynamic_by_expert.get(expert,0)+tensor.numel()
    report.update(format=source.get("format"), central=config,
        pro_state_tensor_parameters=sum(t.numel() for t in state.values() if torch.is_tensor(t)),
        pro_static_central_parameters=static_parameters,pro_expert_coupling_parameters=dynamic_parameters,
        pro_coupling_parameters_by_expert=dynamic_by_expert,
        pro_structure_static_core_dynamic_expert_couplings=True,
        expert_count=len(source.get("active_experts", [])),
        frozen_logical_parameters=source.get("integrated_summary", {}).get("frozen_parameters"),
        frozen_weight_bytes=source.get("integrated_summary", {}).get("frozen_weight_bytes"),
        attention_shapes={"q_proj.weight": q_shape, "k_proj.weight": k_shape},
        attention_config_consistent=(len(q_shape) == 2 and q_shape[0] == config.get("num_attention_heads", 0) * config.get("head_dim", 0)),
        tensor_query_heads=(q_shape[0]//config.get("head_dim",1) if len(q_shape)==2 and config.get("head_dim") else None),
        note="PRO Tensor는 새 SAC 정책에 복사하지 않습니다.")
    return report


def _next_version():
    number = 1
    while ((MODEL_DIR / f"sac_champion_{number:03d}.pt").exists() or
           (ROOT / "runtime/official/champions" / f"sac_champion_{number:03d}").exists()):
        number += 1
    return number, MODEL_DIR / f"sac_champion_{number:03d}.pt"


def _expert_payload(active):
    catalog = read_json(ROOT / "configs/experts.json", {"experts": {}, "active": []})
    expert_registry = MODEL_DIR / "expert_registry.json"
    packages, counts, roles = {}, {}, {}
    for key in active:
        if key not in catalog.get("experts", {}):
            raise ValueError(f"등록되지 않은 Expert: {key}")
        entry = catalog["experts"][key]
        package = load_package(expert_registry, entry["package"], verify=True)
        contract=input_contract(package['entry'])
        if not contract.get('supported'):
            raise ValueError(f"{key}: 현재 입력 계약을 지원하지 않습니다: {contract.get('reason')}")
        weights = package.get("state_dict", {})
        counts[key] = {"logical_parameters": int(package["entry"].get("parameters", 0)),
                       "stored_tensor_elements": sum(v.numel() for v in weights.values() if torch.is_tensor(v)),
                       "stored_tensor_bytes": sum(v.numel() * v.element_size() for v in weights.values() if torch.is_tensor(v)),
                       "package_bytes": int(entry["package"].get("bytes", 0)),
                       "dtype": package["entry"].get("dtype", "unknown")}
        roles[key] = "action" if package["entry"].get("stock_policy") else "market"
        package = dict(package)
        if package.get("weight_asset"):
            ref = package["weight_asset"]
            asset = load_package(expert_registry, entry["package"], verify=True)
            source = (expert_registry.parent / ref["file"]).resolve()
            if not source.is_relative_to(expert_registry.parent.resolve()):
                raise ValueError("Expert 추가 파일 경로가 모델 폴더 밖을 가리킵니다.")
            package["weight_asset_data"] = source.read_bytes()
        packages[key] = package
    return catalog, packages, counts, roles


def _candidate_identity(currency, symbols, active, base_dim):
    function, parameters, steps = sac_example()
    return {"currency": currency, "symbols": list(symbols), "sac_example": parameters,
        "environment": "finrl.meta.env_portfolio_allocation.env_portfolio.StockPortfolioEnv",
        "rolling_days": [1095, 365], "champion_experts": list(active),
        "expert_feature_size": EXPERT_FEATURES, "base_observation_dim": int(base_dim),
        "account_feature_size": 16,
        "sac_steps_per_run": steps, "feature_extractor": "stockrl.platform.sac_champion.ChampionExtractor"}


def _policy_kwargs(identity, roles, original):
    central = original.get("central", {})
    query_heads=original.get("tensor_query_heads") or central.get("num_attention_heads",8)
    return {"features_extractor_class": ChampionExtractor,
        "features_extractor_kwargs": {"base_dim": identity["base_observation_dim"],
            "expert_ids": identity["champion_experts"], "roles": roles,
            "hidden_size": int(central.get("hidden_size", 512)),
            "market_heads": int(query_heads),
            "market_kv_heads": int(central.get("num_key_value_heads",4)),
            "market_head_dim": int(central.get("head_dim",64)),
            "intermediate_size": int(central.get("intermediate_size",1792)),
            "norm_eps": float(central.get("rms_norm_eps",1e-6)),
            "policy_dim": 64, "policy_heads": 4}}


def _counts(model, expert_counts):
    params=list(model.policy.named_parameters())
    integration_prefixes=("actor.features_extractor.","critic.features_extractor.","critic_target.features_extractor.")
    integration=sum(parameter.numel() for name,parameter in params if name.startswith(integration_prefixes))
    entropy=int(model.log_ent_coef.numel()) if getattr(model,'log_ent_coef',None) is not None else 0
    central=sum(parameter.numel() for name,parameter in params if not name.startswith(integration_prefixes))+entropy
    return {"central_parameters": int(central),
        "integration_parameters": int(integration),
        "entropy_coefficient_parameters":entropy,
        "expert_logical_parameters": sum(v["logical_parameters"] for v in expert_counts.values()),
        "expert_stored_tensor_elements": sum(v["stored_tensor_elements"] for v in expert_counts.values()),
        "expert_stored_tensor_bytes": sum(v["stored_tensor_bytes"] for v in expert_counts.values()),
        "total_logical_parameters": int(central + integration + sum(v["logical_parameters"] for v in expert_counts.values()))}


def _copy_compatible(source, target):
    old = source if isinstance(source,dict) else source.policy.state_dict()
    new = target.policy.state_dict()
    copied, skipped = [], []
    for key, value in new.items():
        if key in old and old[key].shape == value.shape:
            value.copy_(old[key]); copied.append(key)
        else:
            skipped.append(key)
    target.policy.load_state_dict(new)
    return copied, skipped


def _transfer_optimizer(source_optimizer, target_optimizer, source_module, target_module):
    old = source_optimizer.state_dict();new = target_optimizer.state_dict()
    if len(old["param_groups"]) != len(new["param_groups"]):return 0
    old_named=dict(source_module.named_parameters());new_named=dict(target_module.named_parameters());moved=0
    for old_group,new_group in zip(old["param_groups"],new["param_groups"]):
        old_ids=old_group["params"];new_ids=new_group["params"]
        old_names=list(old_named);new_names=list(new_named)
        if len(old_ids)!=len(old_names) or len(new_ids)!=len(new_names):return moved
        for old_id,new_id,old_name,new_name in zip(old_ids,new_ids,old_names,new_names):
            if old_name!=new_name or old_name not in old_named or new_name not in new_named or old_named[old_name].shape!=new_named[new_name].shape:continue
            state=old["state"].get(old_id)
            if state is None:continue
            target_optimizer.state[new_named[new_name]]={key:value.detach().clone().to(new_named[new_name].device) if torch.is_tensor(value) else copy.deepcopy(value) for key,value in state.items()}
            moved+=1
    return moved


def _next_paths(version, stem=None):
    model_path = MODEL_DIR / f"sac_champion_{version:03d}.pt"
    run_id = model_path.stem
    directory = ROOT / "runtime/official/champions" / run_id
    if model_path.exists() or directory.exists():
        raise FileExistsError(f"Champion 버전 충돌: {run_id}")
    return model_path, directory, run_id


def create(currency, symbols, active, env, source_path=None):
    from stable_baselines3 import SAC
    from finrl.agents.stablebaselines3.models import DRLAgent
    if not symbols:
        raise ValueError("SAC Champion의 시장과 종목을 지정해야 합니다.")
    active = list(active)
    catalog, packages, expert_counts, roles = _expert_payload(active)
    number, model_path = _next_version()
    directory = ROOT / "runtime/official/champions" / model_path.stem
    if directory.exists():
        raise FileExistsError(f"체크포인트 경로 충돌: {directory}")
    base_dim = int(np.prod(env.unwrapped.observation_space.shape))
    identity = _candidate_identity(currency, symbols, active, base_dim)
    original = _original_report()
    kwargs = _policy_kwargs(identity, roles, original)
    _, params, _ = sac_example()
    agent = DRLAgent(env=env)
    model = agent.get_model("sac", model_kwargs=dict(params), policy_kwargs=kwargs)
    copied, skipped = [], list(model.policy.state_dict());optimizer_state_count=0;replay_transferred=False;source_data=None
    source_state=None;previous=None
    if source_path:
        source_path = Path(source_path)
        if source_path.is_file():
            source_data=load_spec(source_path)
            source_checkpoint=Path(source_data['checkpoint'])
            if not source_checkpoint.is_absolute():source_checkpoint=ROOT/'runtime/official'/source_checkpoint
            try:previous = SAC.load(source_checkpoint, device="cpu")
            except RuntimeError as exc:
                if "state_dict" not in str(exc):raise
                source_state=source_data.get('policy_state',{})
                copied,skipped = _copy_compatible(source_state, model)
                model.num_timesteps=int(source_data.get('training',{}).get('num_timesteps',0))
                model._n_updates=int(source_data.get('training',{}).get('updates',0))
            else:
                copied, skipped = _copy_compatible(previous, model)
                if previous.log_ent_coef is not None and model.log_ent_coef is not None and previous.log_ent_coef.shape==model.log_ent_coef.shape:
                    with torch.no_grad():model.log_ent_coef.copy_(previous.log_ent_coef.to(model.log_ent_coef.device))
                optimizer_state_count += _transfer_optimizer(previous.actor.optimizer,model.actor.optimizer,previous.actor,model.actor)
                optimizer_state_count += _transfer_optimizer(previous.critic.optimizer,model.critic.optimizer,previous.critic,model.critic)
                if previous.ent_coef_optimizer is not None and model.ent_coef_optimizer is not None:
                    old_alpha=previous.log_ent_coef;new_alpha=model.log_ent_coef
                    if old_alpha is not None and new_alpha is not None and old_alpha.shape==new_alpha.shape:
                        old=previous.ent_coef_optimizer.state_dict();new=model.ent_coef_optimizer.state_dict()
                        for old_group,new_group in zip(old['param_groups'],new['param_groups']):
                            for old_id,new_id in zip(old_group['params'],new_group['params']):
                                if old_id in old['state']:
                                    model.ent_coef_optimizer.state[new_alpha]={k:v.detach().clone().to(new_alpha.device) if torch.is_tensor(v) else copy.deepcopy(v) for k,v in old['state'][old_id].items()};optimizer_state_count+=1
                model.num_timesteps=int(previous.num_timesteps)
                model._n_updates=int(previous._n_updates)
                model._episode_num=int(getattr(previous,'_episode_num',0))
            replay_path=source_checkpoint.parent/'replay.pkl'
            same_experts=(source_data.get('expert_package_digests')=={key:catalog['experts'][key]['package']['sha256'] for key in active}
                and source_data.get('identity',{}).get('champion_experts')==active)
            source_obs=source_data.get('identity',{}).get('base_observation_dim',0)+EXPERT_FEATURES*len(active)+16
            source_actions=len(source_data.get('identity',{}).get('symbols',[]))
            spaces_match=(source_obs==int(np.prod(model.observation_space.shape)) and source_actions==int(np.prod(model.action_space.shape)))
            if same_experts and replay_path.is_file() and spaces_match:
                model.load_replay_buffer(replay_path);replay_transferred=True
    directory.mkdir(parents=True)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    identity['champion_file']=str(model_path)
    model.save(directory / "sac")
    model.save_replay_buffer(directory / "replay.pkl")
    atomic_json(identity, directory / "dataset.json")
    parameter_counts = _counts(model, expert_counts)
    output = {"format": "finrlx_compositional_sac_champion_v1", "version": number,
        "trained": bool(source_data and source_data.get("trained")), "created_at": __import__("datetime").datetime.now().astimezone().isoformat(),
        "identity": identity, "roles": roles, "expert_packages": packages,
        "expert_package_digests": {key:catalog['experts'][key]['package']['sha256'] for key in active},
        "moe_architecture": {"market_hidden_size": kwargs["features_extractor_kwargs"]["hidden_size"],
            "market_attention_heads": kwargs["features_extractor_kwargs"]["market_heads"],
            "market_key_value_heads": kwargs["features_extractor_kwargs"]["market_kv_heads"],
            "market_head_dim": kwargs["features_extractor_kwargs"]["market_head_dim"],
            "market_ffn_size": kwargs["features_extractor_kwargs"]["intermediate_size"],
            "policy_adapter_size": kwargs["features_extractor_kwargs"]["policy_dim"],
            "policy_attention_heads": kwargs["features_extractor_kwargs"]["policy_heads"],
            "expert_native_output_features": EXPERT_FEATURES, "account_context_features": 16,
            "sac_feature_size": kwargs["features_extractor_kwargs"]["base_dim"]+
                kwargs["features_extractor_kwargs"]["hidden_size"]+kwargs["features_extractor_kwargs"]["policy_dim"]},
        "expert_counts": expert_counts, "parameters": parameter_counts,
        "training": {"num_timesteps":int(model.num_timesteps),"updates":int(model._n_updates)},
        "policy_state": {key:value.detach().cpu() for key,value in model.policy.state_dict().items()}, "checkpoint": f"champions/{model_path.stem}/sac.zip",
        "transfer": {"copied_policy_tensors": copied, "initialized_policy_tensors": skipped,
                     "optimizer_state": f"호환 Actor/Critic/Entropy optimizer state {optimizer_state_count}개 승계" if optimizer_state_count else "미승계: 호환 Optimizer state가 없거나 구조가 달라졌습니다.",
                     "replay": "기존 Replay 승계" if replay_transferred else "미승계: Expert ID·가중치 checksum, 관측·행동 공간이 모두 같지 않거나 Replay 파일이 없습니다."},
        "original_pro": original}
    try:
        temporary = model_path.with_suffix(".partial")
        torch.save(output, temporary)
        temporary.replace(model_path)
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    return {"name": model_path.name, "path": str(model_path), "checkpoint": output["checkpoint"],"file_bytes":model_path.stat().st_size,
        "trained": output["trained"], "parameters": parameter_counts,"training":output["training"],
        "transfer": output["transfer"], "identity": identity}


def inspect(currency, symbols, active, env=None, inference=None):
    catalog, _, expert_counts, roles = _expert_payload(active)
    original = _original_report()
    estimated=None
    if env is not None:
        from finrl.agents.stablebaselines3.models import DRLAgent
        _, params, _ = sac_example();base_dim=int(np.prod(env.unwrapped.observation_space.shape))
        identity=_candidate_identity(currency,symbols,active,base_dim)
        model=DRLAgent(env=env).get_model('sac',model_kwargs=dict(params),policy_kwargs=_policy_kwargs(identity,roles,original))
        estimated=_counts(model,expert_counts)
    return {"original": original, "experts": [{"id": key, "name": catalog["experts"][key].get("name", key),
            "role": roles[key], **expert_counts[key]} for key in active],
        "expert_counts": expert_counts, "roles": roles,
        "candidate_filename": _next_version()[1].name,
        "source_central_parameters": original.get("central_tensor_parameters"),
        "estimated_parameters": estimated,
        "inference": inference or [],
        "symbols": list(symbols), "currency": currency,
        "resource": {"ram_available": __import__("psutil").virtual_memory().available,
            "vram_available": int(torch.cuda.mem_get_info()[0]) if torch.cuda.is_available() else 0,
            "device": "cuda" if torch.cuda.is_available() else "cpu"},
        "note": "예상 파라미터는 현재 FinRL 환경의 실제 shape와 SB3 SAC Tensor를 기준으로 계산합니다."}


def list_champions():
    result = []
    for path in sorted(MODEL_DIR.glob("sac_champion_*.pt")):
        try:
            data = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
            result.append({"name": path.name, "path": str(path), "version": data.get("version"),
                "trained": data.get("trained", False), "parameters": data.get("parameters", {}),
                "identity": data.get("identity", {}), "checkpoint": data.get("checkpoint"),"training":data.get("training",{}),
                "file_bytes": path.stat().st_size})
        except (OSError, ValueError, RuntimeError):
            continue
    return result


def load_spec(path):
    data = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    if data.get("format") != "finrlx_compositional_sac_champion_v1":
        raise ValueError("SAC Champion PT 형식이 아닙니다.")
    return data


def save_trained_champion(source_path, model, target_path, checkpoint_dir):
    data = load_spec(source_path)
    data['identity']['champion_file']=str(target_path)
    data["policy_state"] = {key:value.detach().cpu() for key,value in model.policy.state_dict().items()}
    data["trained"] = True
    data["training"] = {"num_timesteps": int(model.num_timesteps), "updates": int(model._n_updates),
        "checkpoint": str((checkpoint_dir / "sac.zip").relative_to(ROOT / "runtime/official").as_posix()),
        "replay_file": str((checkpoint_dir / "replay.pkl").relative_to(ROOT / "runtime/official").as_posix())}
    data["checkpoint"] = data["training"]["checkpoint"]
    data["version"] = int(target_path.stem.rsplit("_", 1)[1])
    data["transfer"] = {"from": Path(source_path).name, "policy_tensors_updated": True,
        "optimizer_state": "SB3 체크포인트에서 실제 복원", "replay": "SB3 Replay Buffer를 체크포인트와 함께 저장"}
    if target_path.exists():raise FileExistsError(f"Champion 파일이 이미 있습니다: {target_path.name}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = target_path.with_suffix(".partial")
    try:
        torch.save(data, temporary)
        temporary.replace(target_path)
    except BaseException:
        shutil.rmtree(target_path.parent, ignore_errors=True)
        raise
    return target_path

