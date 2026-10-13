"""정책 학습 — existing API handlers."""
from __future__ import annotations
from api_context import APIRouter
from api_context import BaseModel
from api_context import CASH_ENVIRONMENT
from api_context import ENVIRONMENT
from api_context import Field
from api_context import FileResponse
from api_context import FiniteJSONResponse
from api_context import HTTPException
from api_context import Literal
from api_context import MODELS
from api_context import MODEL_DIR
from api_context import OffPolicyAlgorithm
from api_context import Path
from api_context import ROOT
from api_context import RUNTIME
from api_context import atomic_json
from api_context import finrl_file
from api_context import json
from api_context import lru_cache
from api_context import policy_checkpoint
from api_context import policy_files
from api_context import read_json
from api_context import runtime
from api_context import sac_example
from api_context import system
from api_context import update_json
from api_context import uuid
from api_context import zipfile

router=APIRouter(default_response_class=FiniteJSONResponse)

class RunRequest(BaseModel):
    currency: Literal["USD", "KRW"] = "USD"
    symbols: list[str] = Field(default_factory=list, max_length=1000)
    resume: bool = False
    champion_path: str | None = None
    algorithm: str = 'sac'
    total_timesteps: int | None = Field(default=None,ge=1)


def algorithms():
    return {'default':'sac','items':[{'name':name,'parameters':sac_example(name)[1],
        'steps_per_run':sac_example(name)[2],'uses_replay':issubclass(model,OffPolicyAlgorithm)} for name,model in MODELS.items()]}


@lru_cache(maxsize=1)
def source_settings():
    """Read constants from the exact checked-out call sites without loading learners."""
    _, params, steps = sac_example()
    import inspect
    import importlib.metadata
    import numpy as np
    from gymnasium import spaces
    from stable_baselines3 import SAC
    from stable_baselines3.sac.policies import SACPolicy
    defaults = {}
    for name, parameter in inspect.signature(SAC.__init__).parameters.items():
        if parameter.default is not inspect.Parameter.empty and isinstance(parameter.default, (str,int,float,bool,type(None))):
            defaults[name] = parameter.default
    # An official default policy used only to report architecture, never to train.
    policy = SACPolicy(spaces.Box(-np.inf,np.inf,(1,),dtype=np.float32),
                       spaces.Box(-1,1,(1,),dtype=np.float32), lambda _: defaults["learning_rate"])
    architecture = {"actor_arch": policy.actor.net_arch, "critic_arch": policy.critic_kwargs["net_arch"],
                    "n_critics": policy.critic.n_critics, "activation": policy.activation_fn.__name__,
                    "optimizer": policy.actor.optimizer.__class__.__name__,
                    "feature_extractor": "stockrl.platform.sac_champion.ChampionExtractor"}
    versions = {name: importlib.metadata.version(name) for name in ("stable-baselines3","finrl","torch","gymnasium")}
    env_class=finrl_file('meta/env_portfolio_optimization/env_portfolio_optimization.py').PortfolioOptimizationEnv
    env_args={key:value.default for key,value in inspect.signature(env_class).parameters.items()
        if value.default is not inspect.Parameter.empty and isinstance(value.default,(str,int,float,bool,list,type(None)))}
    return {"parameters":params,"steps_per_run":steps,"environment":ENVIRONMENT,"environment_args":env_args,
        "covariance_lookback":0,"rolling_days":[1095,365],"sb3_defaults":defaults,"policy":architecture,"versions":versions,
        "parameter_source":"finrl.agents.stablebaselines3.models::MODEL_KWARGS['sac']",
        "environment_source":"finrl/meta/env_portfolio_optimization/env_portfolio_optimization.py::PortfolioOptimizationEnv",
        "save_policy":"정상 종료 시 동일 SAC 정책·Replay·Champion 새 버전 저장",
        "observation":"공식 가격 관측 + Expert별 실제 출력 64D + 계좌 16D → ChampionExtractor",
        "notes":["공식 PortfolioOptimizationEnv의 정규화·보상·수수료 기본값을 사용합니다.",
            "SAC 행동은 현금(첫 항목)과 종목별 비중입니다. 가상원장 전달 시 현금을 마지막 항목으로 옮깁니다.",
            "Frozen Expert와 결합부·Actor·Twin Critic은 단일 SAC 정책에 연결됩니다."]}


def model_state(settings,selected=None):
    from stockrl.management.diagnostics_logs_code_apply.handlers import file_info
    from stockrl.management.diagnostics_logs_code_apply.handlers import state
    selected=Path(selected) if selected is not None else policy_files()
    path = policy_checkpoint(selected)
    replay = selected / "replay.pkl"
    identity = read_json(selected / "dataset.json")
    algorithm=identity.setdefault('algorithm','sac');parameters=sac_example(algorithm)[1]
    result = {"file": file_info(path), "replay": file_info(replay), "identity": identity,
              "compatible": False, "policy_compatible":False,"structure_reasons":[],"resume_reasons":[],
              "reasons": [], "num_timesteps": None, "updates": None}
    if not path.is_file():
        result["reasons"].append("저장된 정책이 없습니다.")
        result["structure_reasons"].append("저장된 정책이 없습니다.")
        return result
    try:
        with zipfile.ZipFile(path) as archive:
            state = json.loads(archive.read("data"))
        result.update(num_timesteps=state.get("num_timesteps"), updates=state.get("_n_updates"),
                      observation_shape=state.get("observation_space", {}).get("_shape"),
                      action_shape=state.get("action_space", {}).get("_shape"),
                      parameters={k: state.get(k) for k in parameters},
                      policy_kwargs=state.get("policy_kwargs"))
        structure_reasons=result['structure_reasons'];resume_reasons=result['resume_reasons']
        if not identity.get("symbols") or not identity.get("currency"):
            structure_reasons.append("저장 모델의 통화·종목 정보가 없습니다.")
        is_champion=bool(identity.get("feature_extractor"))
        action_count=len(identity.get('symbols',[]))+1
        if identity.get('environment')!=CASH_ENVIRONMENT:
            structure_reasons.append(f"환경 비호환: 저장 {identity.get('environment')} / 현재 {CASH_ENVIRONMENT}")
        if identity.get('rolling_days')!=settings['rolling_days']:
            structure_reasons.append(f"rolling 구간 비호환: 저장 {identity.get('rolling_days')} / 현재 {settings['rolling_days']}")
        if is_champion and identity.get('feature_extractor')!='stockrl.platform.sac_champion.ChampionExtractor':
            structure_reasons.append("Champion 관측 특성 추출기가 현재 SAC 구조와 다릅니다.")
        for key,value in parameters.items():
            if isinstance(value,(str,int,float,bool)) and key!='action_noise' and state.get(key) != value:
                resume_reasons.append(f"{key}: 저장값 {state.get(key)} / 현재값 {value}")
        if identity.get('symbols') and (is_champion or identity.get('observation_contract')=='expert-observation-v1'):
            env_args=settings['environment_args']
            base_dim=len(env_args['features'])*len(identity['symbols'])*env_args['time_window']
            expected_shape=[base_dim+64*len(identity.get('champion_experts',[]))+16]
            if result['observation_shape']!=expected_shape or result['action_shape']!=[action_count]:
                structure_reasons.append(f"통합 SAC Champion 관측/행동 크기 불일치: 저장 {result['observation_shape']}/{result['action_shape']} / 현재 {expected_shape}/[{action_count}] (현금 포함)")
        else:structure_reasons.append('현재 Expert 관측 계약의 식별 정보가 없습니다. 신규 정책으로 생성하세요.')
        result['policy_compatible']=not structure_reasons
        if issubclass(MODELS[algorithm],OffPolicyAlgorithm) and not replay.is_file():
            resume_reasons.append("이어 학습에 필요한 Replay 파일이 없습니다.")
        result['structure_reasons']=structure_reasons
        result['resume_reasons']=resume_reasons
        result['reasons']=structure_reasons+resume_reasons
        result["compatible"] = not result["reasons"]
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        result["reasons"].append("정책 파일 읽기 실패: " + str(exc))
        result["structure_reasons"].append("정책 파일 읽기 실패: " + str(exc))
    return result


@lru_cache(maxsize=8)
def replay_metadata(path_string, modified, size):
    # This is the project's existing SB3 artifact, not a package supplied through HTTP.
    from stable_baselines3.common.save_util import load_from_pkl
    buffer = load_from_pkl(Path(path_string), verbose=0)
    return {"status": "saved", "size": int(buffer.size()), "capacity": int(buffer.buffer_size),
            "position": int(buffer.pos), "full": bool(buffer.full), "n_envs": int(buffer.n_envs),
            "array_bytes": sum(getattr(value,"nbytes",0) for value in vars(buffer).values())}


def saved_replay():
    identity=read_json(policy_files()/'dataset.json')
    if not issubclass(MODELS[identity.get('algorithm','sac')],OffPolicyAlgorithm):return {'status':'not_used'}
    path = policy_files() / "replay.pkl"
    if not path.exists():
        return {"status":"missing"}
    try:
        return replay_metadata(str(path),path.stat().st_mtime_ns,path.stat().st_size)
    except Exception as exc:
        return {"status":"unreadable","error":str(exc)}


def checkpoints(settings):
    from stockrl.management.diagnostics_logs_code_apply.handlers import file_info
    paths = list(RUNTIME.glob('*.zip')) + sorted((RUNTIME/"archives").glob("*/*.zip")) + sorted((RUNTIME/"policies").glob("*/*.zip")) + sorted((RUNTIME/"champions").glob("*/*.zip"))
    items=[]
    for path in paths:
        if path.stem not in MODELS:continue
        try:
            with zipfile.ZipFile(path) as archive:
                data=json.loads(archive.read("data"))
            identity=read_json(path.parent/"dataset.json")
            identity.setdefault('algorithm',path.stem)
            compatible=identity.get("environment")==settings["environment"] and identity.get('algorithm','sac')==path.stem and identity.get("sac_example")==sac_example(path.stem)[1]
            items.append({"name":path.parent.name if path.parent!=RUNTIME else "현재 정책",
                          "path":path.relative_to(RUNTIME).as_posix(),"file":file_info(path),
                          "num_timesteps":data.get("num_timesteps"),"updates":data.get("_n_updates"),
                          "identity":identity,"compatible":compatible})
        except (OSError,ValueError,KeyError,zipfile.BadZipFile):
            continue
    return items


def currency_models(settings):
    return {currency:model_state(settings,policy_files(currency)) for currency in ('KRW','USD')}


@router.get("/api/download/{name}")
def download(name: Literal["sac.zip", "dataset.json"],currency:Literal['KRW','USD']|None=None):
    path = policy_files(currency) / name
    if not path.is_file():
        raise HTTPException(404, "결과 파일이 없습니다.")
    return FileResponse(path, filename=name)


def preflight(req, command):
    from stockrl.management.diagnostics_logs_code_apply.handlers import database
    from stockrl.extensions.moe.handlers import expert_state
    db = database()
    errors = []
    if db.get("error"):
        errors.append(db["error"])
    eligible = {row["symbol"]: row for row in db["instruments"]
                if row["currency"] == req.currency and row["eligible"]}
    symbols = sorted(set(req.symbols or [s for s, item in eligible.items() if item["stored"]]))
    if not symbols:
        errors.append("선택 시장에 저장된 종목이 없습니다.")
    for symbol in symbols:
        item = eligible.get(symbol)
        if item is None:
            errors.append(symbol + ": 선택 시장의 등록 주식·ETF가 아닙니다.")
        elif not item["stored"]:
            errors.append(symbol + ": 저장 가격이 없습니다.")
        elif item["observations"] < 2:
            errors.append(symbol + ": 공식 환경 실행에는 최소 2개 가격 관측이 필요합니다.")
    settings = source_settings()
    model={'identity':{}}
    if req.resume:
        try:
            selected=policy_files(req.currency)
            model=model_state(settings,selected)
        except (ValueError,OSError) as exc:
            errors.append(str(exc));model=model_state(settings)
    try:_,_,steps=sac_example(req.algorithm)
    except ValueError as exc:errors.append(str(exc));steps=settings['steps_per_run']
    if req.resume and model['identity'].get('algorithm','sac')!=req.algorithm:errors.append('이어 학습 알고리즘이 저장 정책과 다릅니다.')
    if req.champion_path:
        from stockrl.platform.sac_champion import champion_info
        from stockrl.platform.sac_champion import MODEL_DIR
        source=Path(req.champion_path).expanduser().resolve()
        try:
            if not source.is_relative_to(MODEL_DIR.resolve()) or source.suffix!='.pt':
                raise ValueError('모델 폴더의 MoE Champion을 선택하세요.')
            champion=champion_info(source);identity=champion['identity']
            if identity['algorithm']!=req.algorithm:raise ValueError('선택한 알고리즘과 Champion의 알고리즘이 다릅니다.')
            if identity.get('environment')!=CASH_ENVIRONMENT:
                raise ValueError('현재 PortfolioOptimizationEnv와 다른 Champion입니다. MoE에서 현재 환경으로 생성하세요.')
            checkpoint=Path(champion['checkpoint'])
            if not checkpoint.is_absolute():checkpoint=RUNTIME/checkpoint
            if not checkpoint.is_file():raise ValueError('Champion의 SB3 학습 체크포인트가 없습니다.')
            if identity.get('currency')!=req.currency or identity.get('symbols')!=symbols:
                raise ValueError('선택한 Champion의 통화·종목 구성이 다릅니다.')
        except (ValueError,OSError,KeyError,RuntimeError) as exc:
            errors.append('MoE Champion: '+str(exc))
    if req.resume and not req.champion_path:
        compatible=model["compatible"]
        if not compatible:
            errors.extend(model["reasons"])
        if model["identity"].get("currency") != req.currency or model["identity"].get("symbols") != symbols:
            errors.append("저장 정책의 통화·종목 구성과 다릅니다.")
    if not req.champion_path:
        experts = expert_state()
        for row in experts["items"]:
            if row["active"] and not row["package_available"]:
                errors.append(row["id"] + ": 활성 Expert 패키지가 없거나 크기가 다릅니다.")
    periods=None
    if symbols and not errors:
        from stockrl.finrl_trading.price_data.operations import prices
        from stockrl.finrl.framework import validate_price_panel
        from pandas import Timedelta,to_datetime
        frame=prices(req.currency,symbols)
        if frame.empty:errors.append('학습·추론 모듈이 사용하는 실제 저장 가격이 없습니다.')
        else:
            dates=to_datetime(frame.date,utc=True);trade=dates.max()+Timedelta(days=1)
            train_mask=(dates>=trade-Timedelta(days=1095))&(dates<trade-Timedelta(days=365))
            train_count=int(dates[train_mask].nunique())
            if train_count<2:errors.append('공식 rolling 학습 구간에 데이터가 부족합니다.')
            try:validate_price_panel(frame[train_mask],symbols)
            except ValueError as exc:errors.append('학습: '+str(exc))
            periods={'training_observations':train_count,'trade_date':str(trade),
                'train_start':str(trade-Timedelta(days=1095)),'train_end_exclusive':str(trade-Timedelta(days=365))}
    return {"ok": not errors, "errors": errors, "symbols": symbols, "currency": req.currency, "periods": periods,
            "mode": "이어 학습" if req.resume else "새 학습",
            "steps_per_run": req.total_timesteps or steps}


@router.post("/api/preflight/train")
def check(req: RunRequest):
    return preflight(req, "train")


def launch(command, req,preserve_output=False):
    from stockrl.management.diagnostics_logs_code_apply.handlers import now
    with system.job_lock:
        if system.job_state()["running"]:
            raise HTTPException(409, "학습 작업이 실행 중입니다.")
        checked = preflight(req, command)
        if not checked["ok"]:
            raise HTTPException(400, "\n".join(checked["errors"]))
        RUNTIME.mkdir(parents=True, exist_ok=True)
        job_id = uuid.uuid4().hex
        job = {"id": job_id, "status": "starting", "command": command, "currency": req.currency,
               "symbols": checked["symbols"], "resume": req.resume, "started_at": now(),
               "log": f"jobs/{job_id}.log", "finished_at": None, "exit_code": None}
        job.update(algorithm=req.algorithm,total_timesteps=req.total_timesteps)
        if req.champion_path:
            from stockrl.platform.sac_champion import _next_version
            _,target=_next_version(req.algorithm)
            job.update(champion_path=str(Path(req.champion_path).expanduser().resolve()),
                champion_output=str(target),output='champions/'+target.stem)
        elif command=='train' or preserve_output:job['output']='policies/'+job_id
        system.start_job(job)
        return {"message": "학습을 시작했습니다.", "job": job}


@router.post("/api/train")
def train(req: RunRequest):
    return launch("train", req)


@router.get("/api/checkpoint")
def checkpoint_download(path:str):
    target=(RUNTIME/path).resolve()
    if not target.is_relative_to(RUNTIME.resolve()) or target.suffix!='.zip' or target.stem not in MODELS or not target.exists():
        raise HTTPException(404,"정책 파일이 없습니다.")
    return FileResponse(target,filename=target.parent.name+'-'+target.name)


@router.post("/api/checkpoints/restore")
def restore_checkpoint(request:dict):
    with system.job_lock:
        if system.job_state()["running"]:raise HTTPException(409,"현재 학습 작업 종료 후 복원하세요.")
        path=(RUNTIME/request.get("path","")).resolve()
        if not path.is_relative_to(RUNTIME.resolve()) or path.suffix!='.zip' or path.stem not in MODELS or not path.is_file():
            raise HTTPException(400,"저장된 FinRL 정책 버전을 선택하세요.")
        identity=read_json(path.parent/"dataset.json")
        settings=source_settings()
        if identity.get("environment")!=settings["environment"] or identity.get('algorithm','sac')!=path.stem or identity.get("sac_example")!=sac_example(path.stem)[1]:
            raise HTTPException(400,"현재 FinRL 환경·알고리즘·설정과 호환되지 않는 정책입니다.")
        with runtime.lock:
            try:loaded=runtime.check_policy(path.parent,load=True)
            except (ValueError,RuntimeError,OSError,KeyError,MemoryError) as exc:raise HTTPException(400,str(exc)) from exc
            atomic_json({"path":path.relative_to(RUNTIME).as_posix()},RUNTIME/"active-checkpoint.json")
            selection_path=ROOT/'runtime/operations/policies.json'
            update_json(selection_path,lambda selected:{**selected,identity['currency']:path.relative_to(RUNTIME).as_posix()})
            system.release_models(keep=system.selected_models())
        return {"message":"해당 FinRL 정책을 선택하고 중앙 정책을 실제 로드했습니다. 학습·시세·매매는 시작하지 않았습니다.","policy":loaded}

