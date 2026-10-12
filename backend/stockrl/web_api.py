"""Local HTTP adapter for official_cli, DataStore files and frozen Expert registry."""
from __future__ import annotations

import ast
import csv
import json
import math
import os
import re
import sqlite3
import sys
import time
import uuid
import zipfile
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from starlette.routing import Route
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field

from . import ROOT
from .finrl.framework import CASH_ENVIRONMENT,policy_files,policy_checkpoint,sac_example,finrl_file,champion_structure_environment
from .finrl_trading import finrlx
from .state_io import atomic_json, read_json, update_json
from .platform.resources import ResourceMonitor
from .platform.system_operations import system,apply_state,apply_running,start_apply,busy,check_system
from .platform.operations_runtime import runtime
from .platform.library_operations import library as library_manager
from .expert_registry_native import ExpertRegistry
from finrl.agents.stablebaselines3.models import MODELS
from stable_baselines3.common.off_policy_algorithm import OffPolicyAlgorithm

RUNTIME = ROOT / "runtime/official"
DB = ROOT / "data/finrl_trading.db"
MODEL_DIR = Path.home() / "Desktop/모델"
ENVIRONMENT = CASH_ENVIRONMENT


def finite_json(value):
    if isinstance(value,float) and not math.isfinite(value):return None
    if isinstance(value,dict):return {key:finite_json(item) for key,item in value.items()}
    if isinstance(value,(list,tuple)):return [finite_json(item) for item in value]
    return value


class FiniteJSONResponse(JSONResponse):
    def render(self,content):
        return super().render(finite_json(content))


app = FastAPI(title="FinRL local workspace", version="2",default_response_class=FiniteJSONResponse)
private_api=APIRouter(default_response_class=FiniteJSONResponse)
class UnifiedAPI:
    async def __call__(self,scope,receive,send):
        route,forwarded,body=scope['state']['api_dispatch']
        received=False
        async def payload():
            nonlocal received
            if received:return await receive()
            received=True
            return {'type':'http.request','body':body,'more_body':False}
        await route.handle(forwarded,payload,send)
app.router.routes.append(Route('/api',UnifiedAPI(),methods=['GET','POST']))
FRONTEND_DIST = ROOT / "frontend/dist"
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets"), check_dir=False), name="react-assets")
resource_monitor = ResourceMonitor(ROOT)
database_cache = {"stamp": None, "value": None}


@app.middleware("http")
async def local_writes(request: Request, call_next):
    path=request.url.path;method=request.method
    if path=='/api':
        from urllib.parse import urlencode
        try:
            if method=='GET':
                operation=request.query_params.get('operation','');parameters=json.loads(request.query_params.get('payload','{}'))
            else:
                envelope=await request.json();operation=envelope.get('operation','');parameters=envelope.get('payload',{})
            if not isinstance(operation,str) or not operation or not isinstance(parameters,dict):raise ValueError('operation과 payload 객체를 전달하세요.')
            path='/api/'+operation;matched=None
            for internal_method in (('GET',) if method=='GET' else ('POST','GET')):
                forwarded={**request.scope,'path':path,'raw_path':path.encode('utf-8'),'method':internal_method,
                    'query_string':urlencode(parameters,doseq=True).encode() if internal_method=='GET' else b''}
                from .menu_registry import dispatch
                matched=dispatch(forwarded,parameters)
                if matched:break
            if not matched:return JSONResponse({'detail':'등록되지 않은 백엔드 명령입니다.'},status_code=404)
            method=matched[1]['method'];body=json.dumps(parameters,ensure_ascii=False).encode('utf-8') if method=='POST' else b''
            matched[1]['headers']=[(key,value) for key,value in request.scope['headers'] if key.lower() not in (b'content-length',b'content-type')]+[(b'content-type',b'application/json'),(b'content-length',str(len(body)).encode())]
            request.state.api_dispatch=(*matched,body)
        except (ValueError,TypeError,AttributeError) as exc:return JSONResponse({'detail':str(exc)},status_code=400)
    elif path.startswith('/api/'):
        return JSONResponse({'detail':'단일 /api 통로를 사용하세요.'},status_code=404)
    origin = request.headers.get("origin")
    if method != "GET" and origin and origin not in {
        "http://127.0.0.1:5173", "http://localhost:5173",
        "http://127.0.0.1:8766", "http://localhost:8766"
    }:
        return JSONResponse({"detail": "로컬 화면에서 요청하세요."}, status_code=403)
    if method!='GET':
        allowed_stop=path in ('/api/stop','/api/system/stop','/api/system/prepare-restart','/api/library/stop') or path.startswith('/api/controls/') and parameters.get('enabled') is False
        if ((apply_running() and apply_state().get('target')!='frontend') or system.restarting) and not allowed_stop and path!='/api/system/apply':
            return JSONResponse({'detail':'변경 적용/서버 갱신 중입니다. 기존 작업은 보존합니다.'},status_code=409)
        conflict=path in ('/api/train','/api/backtest','/api/stop','/api/collect','/api/settings','/api/checkpoints/restore','/api/system/stop') or path.startswith(('/api/controls/','/api/experts/','/api/provider/')) and path!='/api/provider/test' or path.startswith('/api/framework/') or path.startswith('/api/library/') and path not in ('/api/library/search','/api/library/inspect')
        if conflict:
            system.cancel()
    response=await call_next(request)
    if method!='GET':system.invalidate_states()
    return response


class RunRequest(BaseModel):
    currency: Literal["USD", "KRW"] = "USD"
    symbols: list[str] = Field(default_factory=list, max_length=1000)
    resume: bool = False
    champion_path: str | None = None
    checkpoint_path: str | None = None
    algorithm: str = 'sac'
    total_timesteps: int | None = Field(default=None,ge=1)


class ChampionRequest(BaseModel):
    algorithm:str='sac'
    currency:Literal["USD","KRW"]|None=None
    symbols:list[str]=Field(default_factory=list,max_length=1000)
    experts:list[str]=Field(default_factory=list,max_length=128)


class Selection(BaseModel):
    active: list[str]


class Registration(BaseModel):
    path: str = Field(min_length=1)
    slot: str = Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")


class CollectionRequest(BaseModel):
    symbols:list[str]=Field(min_length=1,max_length=100)
    start_date:str=Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date:str=Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


def now():
    return datetime.now(timezone.utc).isoformat()


def algorithms():
    return {'default':'sac','items':[{'name':name,'parameters':sac_example(name)[1],
        'steps_per_run':sac_example(name)[2],'uses_replay':issubclass(model,OffPolicyAlgorithm)} for name,model in MODELS.items()]}


def file_info(path):
    return {"exists": path.is_file(), "bytes": path.stat().st_size if path.is_file() else 0,
            "modified": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if path.is_file() else None}


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



def database():
    if not DB.is_file():
        return {"error": "가격 DB가 없습니다.", "rows": 0, "tickers": 0, "instruments": []}
    wal=DB.with_name(DB.name+'-wal')
    stamp = (DB.stat().st_mtime_ns, DB.stat().st_size,wal.stat().st_mtime_ns if wal.exists() else 0,
             (ROOT / "configs/instruments.json").stat().st_mtime_ns)
    if database_cache["stamp"] == stamp:
        return database_cache["value"]
    try:
        with sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True, timeout=5) as connection:
            connection.row_factory = sqlite3.Row
            totals = dict(connection.execute("SELECT COUNT(*) rows, COUNT(DISTINCT ticker) tickers, MIN(date) start, MAX(date) end FROM price_data").fetchone())
            stats = {r["symbol"]: dict(r) for r in connection.execute("""
                SELECT ticker symbol, COUNT(*) rows, COUNT(DISTINCT date) observations,
                       COUNT(DISTINCT substr(date,1,10)) trading_days, MIN(date) start, MAX(date) end
                FROM price_data GROUP BY ticker
            """)}
            latest = {r["ticker"]: dict(r) for r in connection.execute("""
                SELECT p.ticker,p.close,p.volume FROM price_data p
                JOIN (SELECT ticker,MAX(date) latest FROM price_data GROUP BY ticker) q
                ON p.ticker=q.ticker AND p.date=q.latest
            """)}
        config = read_json(ROOT / "configs/instruments.json").get("instruments", [])
        catalog = {i["symbol"]: i for i in config}
        instruments = []
        for symbol in sorted(set(catalog) | set(stats)):
            meta = catalog.get(symbol, {})
            market = meta.get("market", "KRX" if symbol.endswith(".KS") else "KOSDAQ" if symbol.endswith(".KQ") else "미분류")
            currency = "KRW" if market in ("KRX", "KOSDAQ") else "USD"
            eligible = meta.get("asset_class") in ("equity", "etf") and market in ("KRX", "KOSDAQ", "US", "NASDAQ", "NYSE", "NYSEARCA", "AMEX")
            item = {"symbol": symbol, "name": meta.get("name", symbol), "market": market, "currency": currency,
                    "eligible": eligible, "stored": symbol in stats, "rows": 0, "observations": 0, "trading_days": 0,
                    "start": None, "end": None, "last_close": latest.get(symbol, {}).get("close")}
            item.update(stats.get(symbol, {}))
            instruments.append(item)
        totals["instruments"] = instruments
        totals["path"] = str(DB)
        totals["error"] = None
        database_cache.update(stamp=stamp, value=totals)
        return totals
    except (sqlite3.Error, OSError, ValueError) as exc:
        return {"error": str(exc), "rows": 0, "tickers": 0, "instruments": []}


def model_state(settings,selected=None):
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


def capabilities():
    return {
        "learning":{"status":"supported","reason":"FinRL DRLAgent · SB3 알고리즘 선택·학습·중단·동일 정책 이어 학습 · 기본 SAC","source":"stockrl.finrl.framework.train"},
        "expert_selection":{"status":"supported","reason":"Frozen Expert 등록·선택·같은 모델 정밀도 교체·해제","source":"stockrl.expert_registry_native.ExpertRegistry"},
        "collection":{"status":"supported","reason":"FinRL-X FMP 가격 수집 모듈. API 인증이 있어야 원격 수집 가능합니다.","source":"FinRL-X/src/data/data_fetcher.py::fetch_price_data"},
        "paper_accounts":{"status":"supported","reason":"원본 PaperAccount의 KRW/USD 독립 잔고·보유·체결·손익 기능이 연결되어 있습니다.","source":"stockrl.paper_account.PaperAccount"},
        "live_feed":{"status":"supported","reason":"복구한 LiveMarketCollector와 Kiwoom BrokerStreams의 완료 시세를 DataStore·가상계좌에 전달합니다.","source":"stockrl.live_feed"},
        "kiwoom":{"status":"supported","reason":"기존 보안 저장소·인증·실시간 수신 모듈 연결. 실제 수신에는 유효한 인증이 필요합니다. 실제 주문은 전송하지 않습니다.","source":"stockrl.provider_credentials / platform.kiwoom_data"},
        "alpaca":{"status":"not_connected","reason":"공식 서브모듈에는 Alpaca 모듈이 있지만 현재 SAC 작업에 연결되지 않았습니다.","source":"FinRL-X/src/trading/alpaca_manager.py"},
        "conversion":{"status":"supported","reason":"기존 정밀도 변환과 품질 비교·후보 선택 함수를 연결합니다. 변환은 새 파일로 저장됩니다.","source":"stockrl.platform.expert_conversion / expert_optimizer"},
        "discovery":{"status":"supported","reason":"기존 HF/GitHub 검색·가중치 호환 확인·다운로드·자동 등록 함수가 연결되어 있습니다.","source":"stockrl.platform.expert_discovery / expert_acquisition"},
        "checkpoint_restore":{"status":"supported","reason":"기존 SB3 파일을 변경하지 않고 선택하여 복원·이어 학습에 사용합니다. 이전 자체 정책 형식은 호환되지 않습니다.","source":"stockrl.finrl.framework.policy_files"},
        "settings_edit":{"status":"supported","reason":"시세·가상계좌·Expert 장치의 기존 운영 설정을 편집합니다. SAC 학습값은 변경하지 않습니다.","source":"stockrl.platform.operations_settings"},
    }


@lru_cache(maxsize=256)
def expert_descriptor(key,file,checksum,size,modified):
    from .platform.expert_packages import load_package
    from .platform.expert_contracts import descriptor
    reference={"file":file,"sha256":checksum,"bytes":size}
    return descriptor(key,load_package(MODEL_DIR/"expert_registry.json",reference),reference)


def expert_state():
    registry = read_json(ROOT / "configs/experts.json", {"active": [], "experts": {}})
    status = read_json(ROOT / "runtime/experts/status.json")
    rows = []
    for key, item in registry.get("experts", {}).items():
        reference = item.get("package", {})
        path = (MODEL_DIR / reference.get("file", "")).resolve()
        available = path.is_relative_to(MODEL_DIR.resolve()) and path.is_file()
        if available and reference.get("bytes") is not None:
            available = path.stat().st_size == reference["bytes"]
        detail=dict(item)
        if available:
            try:
                actual=expert_descriptor(key,reference["file"],reference["sha256"],reference["bytes"],path.stat().st_mtime_ns)
                detail={**item,**actual,"name":item.get("name",actual["name"]),
                    "check":item.get("check",actual["check"]),"conversion":item.get("conversion",actual.get("conversion"))}
                if actual.get("executor")=="llama_cpp":
                    from .platform.gguf_format import stored_precision
                    package=read_json(path);weight=(MODEL_DIR/package["weight_asset"]["file"]).resolve()
                    if not weight.is_relative_to(MODEL_DIR.resolve()):raise ValueError("GGUF 경로가 모델 폴더 밖입니다.")
                    info=weight.stat()
                    detail["representation"]=stored_precision(str(weight),info.st_mtime_ns,info.st_size)
                    detail["quantized"]=bool(re.search(r'(?:I?Q)\d+',detail["representation"]))
            except (ValueError,OSError,KeyError,RuntimeError) as exc:
                detail["metadata_error"]=str(exc)
        rows.append({**detail, "id": key, "active": key in registry.get("active", []),
                     "package_available": available, "package_path": str(path),
                     "inference": status.get("experts", {}).get(key),
                     "resources": status.get("resources", {}).get(key, {}),
                     "current_resources": system.expert_pool.metrics.get(key,{}) if system.expert_pool else {},
                     "loaded": bool(system.expert_pool and key in system.expert_pool.loaded)})
    return {"active": registry.get("active", []), "items": rows, "as_of": status.get("as_of"),
            "reported": file_info(ROOT / "runtime/experts/status.json").get("modified")}






def evaluation_root(currency=None):
    if not currency:return RUNTIME
    root=RUNTIME/'backtests'/currency
    if (root/'backtest.csv').is_file():return root
    return RUNTIME if read_json(RUNTIME/'backtest_metrics.json').get('currency')==currency else root


def evaluation(currency:Literal['KRW','USD']|None=None):
    root=evaluation_root(currency);path = root / "backtest.csv"
    points = []
    if path.is_file():
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream)
            next(reader, None)
            for row in reader:
                try:
                    value = float(row[-1])
                    if math.isfinite(value):
                        points.append({"date": row[0], "value": value})
                except (ValueError, IndexError):
                    continue
    return {"points": points, "file": file_info(path),
            "report": read_json(root / "backtest_metrics.json")}


@private_api.get("/api/health")
def health():
    return {"ok": True, "service": "finrlx-react-sac", "project": str(ROOT.resolve()), "pid": os.getpid(),"deployment_id":os.environ.get('STOCKRL_APPLY_ID')}


@app.get("/", include_in_schema=False)
def react_index():
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(503, "React 빌드가 없습니다. 서버켜기.cmd를 실행하세요.")
    return FileResponse(index, headers={"Cache-Control": "no-cache"})


def modules():
    from .platform.framework_operations import catalog
    return catalog()


def menu_catalog():
    from .menu_registry import catalog
    return catalog(private_api.routes)


def result_table(kind: Literal["weights", "trades"], limit: int = Query(1000, ge=1, le=5000),currency:Literal['KRW','USD']|None=None):
    path = evaluation_root(currency) / ("backtest_" + kind + ".csv")
    if not path.is_file():
        return {"columns": [], "rows": [], "total": 0}
    import pandas as pd
    frame = pd.read_csv(path)
    frame.columns = [str(c).replace("Unnamed: 0", "index") for c in frame.columns]
    finite = frame.replace([float("inf"), -float("inf")], None).astype(object).where(frame.notna(), None)
    return {"columns": list(frame.columns), "rows": finite.tail(limit).to_dict("records"), "total": len(frame)}


def currency_models(settings):
    return {currency:model_state(settings,policy_files(currency)) for currency in ('KRW','USD')}


def state_stamp(*patterns):
    values=[]
    for pattern in patterns:
        path=Path(pattern)
        paths=sorted(path.parent.glob(path.name)) if '*' in path.name else [path]
        for item in paths:
            if item.is_file() or item.is_dir():
                stamp=item.stat();values.append((str(item),stamp.st_mtime_ns,stamp.st_size))
    return tuple(values)


def state_view(path):
    from urllib.parse import urlsplit,parse_qs
    parsed=urlsplit(path);query=parse_qs(parsed.query);key=parsed.path
    if parsed.scheme or parsed.netloc:raise ValueError('통합 상태 항목을 선택하세요.')
    currency=query.get('currency',[None])[0]
    if currency not in (None,'USD','KRW'):raise ValueError('USD/KRW 상태를 선택하세요.')
    config=ROOT/'configs';official=ROOT/'runtime/official'
    providers={
        'menu_catalog':(menu_catalog,lambda:()),
        'algorithms':(algorithms,lambda:()),
        'finrl':(finrl_workspace,lambda:state_stamp(official/'job.json',*(official/'framework-jobs').glob('*/result.json'))),
        'framework':(framework_catalog,None),
        'framework/providers':(framework_providers,None),
        'connections':(connections,None),
        'provider':(provider,None),
        'settings':(operational_settings,lambda:state_stamp(config/'local/operations.json')),
        'models':(model_files,lambda:state_stamp(config/'experts.json',*MODEL_DIR.rglob('*'))),
        'champions':(champions,lambda:state_stamp(*MODEL_DIR.glob('*_champion_*.pt'))),
        'logs':(logs,lambda:state_stamp(*(official/name for name in ('api.stderr.log','api.stdout.log','server.stderr.log','training.log')))),
    }
    if key=='evaluation':
        folder=evaluation_root(currency);providers[key]=(lambda:evaluation(currency),state_stamp(folder/'backtest.csv',folder/'backtest_metrics.json'))
    elif key in ('result/weights','result/trades'):
        kind=key.rsplit('/',1)[1];folder=evaluation_root(currency)
        providers[key]=(lambda:result_table(kind,1000,currency),state_stamp(folder/('backtest_'+kind+'.csv')))
    elif key=='prices':
        symbol=query.get('symbol',[''])[0];limit=int(query.get('limit',['300'])[0])
        if not symbol or not 1<=limit<=2000:raise ValueError('종목과 기존 가격 조회 범위를 확인하세요.')
        providers[key]=(lambda:price_history(symbol,limit),state_stamp(DB,DB.with_name(DB.name+'-wal')))
    if key not in providers:raise ValueError('등록되지 않은 통합 상태 항목입니다: '+key)
    loader,signature=providers[key];name='view:'+path
    data=system.state_value(name,loader,signature)
    return {'data':data,'error':system.state_errors.get(name,''),'updated_at':system.state_updates.get(name)}


@private_api.get('/api/state')
def state(views:str='[]',refresh_views:bool=False):
    try:
        requested=json.loads(views)
        if not isinstance(requested,list) or not all(isinstance(path,str) for path in requested):raise ValueError('상태 항목 목록이 필요합니다.')
    except (ValueError,TypeError) as exc:raise HTTPException(400,str(exc)) from exc
    if refresh_views:system.invalidate_states()
    system.prune_missing_file_states('champion:')
    imports=system.connect_modules()
    settings=system.state_value('settings',source_settings,())
    db=system.state_value('data',database,lambda:state_stamp(DB,DB.with_name(DB.name+'-wal'),ROOT/'configs/instruments.json'))
    job=system.state_value('job',system.job_state)
    def saved_model():
        folder=policy_files()
        if settings is None:raise RuntimeError('공식 설정 조회 실패: '+system.state_errors.get('settings',''))
        value=model_state(settings,folder);value['replay_state']=saved_replay();return value
    def model_signature():
        folder=policy_files()
        return state_stamp(RUNTIME/'active-checkpoint.json',ROOT/'runtime/operations/policies.json',policy_checkpoint(folder),folder/'dataset.json',folder/'replay.pkl')
    model=system.state_value('model',saved_model,model_signature)
    def connected_experts():
        experts=expert_state()
        return {**experts,'observation_connection':{'size':64*len((model or {}).get('identity',{}).get('champion_experts',experts['active']))+16,'configured':model is not None,'recorded':bool(experts.get('as_of')),
            'last_success':{role:sum(1 for row in experts['items'] if row['active'] and row.get('inference') and row['inference'].get('status')=='ready' and row.get('role')==role) for role in ('market','action')}}}
    experts=system.state_value('experts',connected_experts)
    def currency_signature():
        currencies=[policy_files(currency) for currency in ('KRW','USD')]
        return state_stamp(ROOT/'runtime/operations/policies.json',RUNTIME/'active-checkpoint.json',*(file for root in currencies for file in (policy_checkpoint(root),root/'dataset.json',root/'replay.pkl')))
    models=system.state_value('models_by_currency',lambda:currency_models(settings),currency_signature)
    evaluations=system.state_value('evaluation',evaluation,lambda:state_stamp(evaluation_root()/'backtest.csv',evaluation_root()/'backtest_metrics.json'))
    def checkpoint_signature():
        files=[*RUNTIME.glob('*.zip'),*(RUNTIME/'policies').glob('*/*.zip'),*(RUNTIME/'champions').glob('*/*.zip'),*(RUNTIME/'archives').glob('*/*.zip')]
        return state_stamp(*files,*(file.parent/'dataset.json' for file in files))
    revisions=system.state_value('checkpoints',lambda:checkpoints(settings),checkpoint_signature)
    operations_state=system.state_value('operations',runtime.snapshot)
    library=system.state_value('library',library_manager.snapshot)
    automation=system.state_value('automation',lambda:{'apply':apply_state(),'system':system.snapshot()})
    selected={}
    for path in dict.fromkeys(requested):
        try:selected[path]=state_view(path)
        except Exception as exc:selected[path]={'data':None,'error':str(exc),'updated_at':None}
    workers={'learner':{'pid':(job or {}).get('pid'),'alive':(job or {}).get('running',False)}}
    resources=system.state_value('resources',lambda:resource_monitor.snapshot(workers))
    return {'architecture':'finrl-unified-v3','updated_at':now(),'settings':settings,'model':model,'data':db,'experts':experts,'job':job,
        'evaluation':evaluations,'models_by_currency':models,'checkpoints':revisions,'capabilities':system.state_value('capabilities',capabilities,()),
        'operations':operations_state,'library':library,'automation':automation,'resources':resources,'views':selected,
        'state_revision':system.state_revision,'module_errors':dict(system.state_errors),'module_updated_at':dict(system.state_updates),'resident_models':system.resident_models(),'imports':imports,
        'commands':system.commands(),'frontend_revision':system.state_value('frontend_revision',lambda:read_json(RUNTIME/'applied-sources.json').get('dist_sha256'),lambda:state_stamp(RUNTIME/'applied-sources.json'))}


def connections():
    try:
        manager=finrlx("data.data_fetcher").get_data_manager()
        sources=[name for name,source in manager.data_sources if source.is_available()]
        info={"status":"configured" if sources else "requires_configuration",
              "source":getattr(manager,"current_source_name",None),"available_sources":sources,
              "reason":None if sources else "FMP 인증이 없어 원격 가격 수집을 실행할 수 없습니다."}
    except Exception as exc:
        info={"status":"unavailable","source":None,"available_sources":[],"reason":str(exc)}
    return {"api":{"status":"connected"},"data":info,"brokers":[
        {"name":name,"status":capabilities()[key]["status"],"reason":capabilities()[key]["reason"]}
        for name,key in (("키움","kiwoom"),("Alpaca","alpaca"))]}


def logs():
    names=("api.stderr.log","api.stdout.log","server.stderr.log","training.log")
    result=[]
    for name in names:
        path=RUNTIME/name
        if path.exists():
            with path.open("rb") as stream:
                stream.seek(max(0,path.stat().st_size-12000))
                result.append({"name":name,"file":file_info(path),"text":stream.read().decode("utf8",errors="replace")})
    return {"items":result}


def price_history(symbol: str, limit: int = Query(300, ge=1, le=2000)):
    if not DB.exists():
        raise HTTPException(404, "가격 DB가 없습니다.")
    with sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT date,open,high,low,close,volume FROM price_data WHERE ticker=? ORDER BY date DESC LIMIT ?", (symbol, limit)).fetchall()
    return {"symbol": symbol, "rows": [dict(row) for row in reversed(rows)]}


@private_api.get("/api/download/{name}")
def download(name: Literal["backtest.csv", "backtest_metrics.json", "backtest_weights.csv", "backtest_trades.csv", "sac.zip", "dataset.json"],currency:Literal['KRW','USD']|None=None):
    path = (policy_files(currency) if name in ('sac.zip','dataset.json') else evaluation_root(currency)) / name
    if not path.is_file():
        raise HTTPException(404, "결과 파일이 없습니다.")
    return FileResponse(path, filename=name)


def preflight(req, command):
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
    if command=='backtest' and not req.champion_path or req.resume:
        try:
            selected=policy_files(req.currency,req.checkpoint_path if command=='backtest' else None)
            model=model_state(settings,selected)
        except (ValueError,OSError) as exc:
            errors.append(str(exc));model=model_state(settings)
    if req.checkpoint_path and command!='backtest':errors.append('정책 경로 선택은 운영 승인 전 평가에만 사용합니다.')
    if req.checkpoint_path and req.champion_path:errors.append('평가할 정책 또는 Champion 중 하나를 선택하세요.')
    try:_,_,steps=sac_example(req.algorithm)
    except ValueError as exc:errors.append(str(exc));steps=settings['steps_per_run']
    if req.resume and model['identity'].get('algorithm','sac')!=req.algorithm:errors.append('이어 학습 알고리즘이 저장 정책과 다릅니다.')
    if command=='backtest' and not req.champion_path and model['identity'].get('algorithm','sac')!=req.algorithm:errors.append('평가 알고리즘이 저장 정책과 다릅니다.')
    if req.champion_path:
        from .platform.sac_champion import champion_info,MODEL_DIR
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
    if (command == "backtest" or req.resume) and not req.champion_path:
        compatible=model["compatible"] if req.resume else model["policy_compatible"]
        if not compatible:
            errors.extend(model["reasons"] if req.resume else model["structure_reasons"])
        if model["identity"].get("currency") != req.currency or model["identity"].get("symbols") != symbols:
            errors.append("저장 정책의 통화·종목 구성과 다릅니다.")
    if not req.champion_path:
        experts = expert_state()
        for row in experts["items"]:
            if row["active"] and not row["package_available"]:
                errors.append(row["id"] + ": 활성 Expert 패키지가 없거나 크기가 다릅니다.")
    periods=None
    if symbols and not errors:
        from .finrl_trading.data import prices
        from .finrl.framework import validate_price_panel
        from pandas import Timedelta,to_datetime
        frame=prices(req.currency,symbols)
        if frame.empty:errors.append('학습·추론 모듈이 사용하는 실제 저장 가격이 없습니다.')
        else:
            dates=to_datetime(frame.date,utc=True);trade=dates.max()+Timedelta(days=1)
            train_mask=(dates>=trade-Timedelta(days=1095))&(dates<trade-Timedelta(days=365))
            test_mask=(dates>=trade-Timedelta(days=365))&(dates<trade)
            train_count=int(dates[train_mask].nunique());test_count=int(dates[test_mask].nunique())
            if train_count<2 and command=='train':errors.append('공식 rolling 학습 구간에 데이터가 부족합니다.')
            if test_count<2:errors.append('rolling 평가 구간에 데이터가 부족합니다.')
            for label,mask in ([('학습',train_mask)] if command=='train' else [])+[('평가',test_mask)]:
                try:validate_price_panel(frame[mask],symbols)
                except ValueError as exc:errors.append(label+': '+str(exc))
            periods={'training_observations':train_count,'test_observations':test_count,'trade_date':str(trade),
                'train_start':str(trade-Timedelta(days=1095)),'train_end_exclusive':str(trade-Timedelta(days=365))}
    return {"ok": not errors, "errors": errors, "symbols": symbols, "currency": req.currency, "periods": periods,
            "mode": "이어 학습" if req.resume else "새 학습" if command == "train" else "백테스트",
            "steps_per_run": req.total_timesteps or steps}


@private_api.post("/api/preflight/{command}")
def check(command: Literal["train", "backtest"], req: RunRequest):
    return preflight(req, command)


def launch(command, req,preserve_output=False):
    with system.job_lock:
        if system.job_state()["running"]:
            raise HTTPException(409, "학습 또는 평가가 실행 중입니다.")
        checked = preflight(req, command)
        if not checked["ok"]:
            raise HTTPException(400, "\n".join(checked["errors"]))
        RUNTIME.mkdir(parents=True, exist_ok=True)
        job_id = uuid.uuid4().hex
        job = {"id": job_id, "status": "starting", "command": command, "currency": req.currency,
               "symbols": checked["symbols"], "resume": req.resume, "started_at": now(),
               "log": f"jobs/{job_id}.log", "finished_at": None, "exit_code": None}
        job.update(algorithm=req.algorithm,total_timesteps=req.total_timesteps)
        if command=='backtest':
            job['output']='backtests/'+req.currency
            if req.checkpoint_path:job['checkpoint_path']=req.checkpoint_path
            if req.champion_path:job['champion_path']=str(Path(req.champion_path).expanduser().resolve())
        elif req.champion_path:
            from .platform.sac_champion import _next_version
            _,target=_next_version(req.algorithm)
            job.update(champion_path=str(Path(req.champion_path).expanduser().resolve()),
                champion_output=str(target),output='champions/'+target.stem)
        elif command=='train' or preserve_output:job['output']='policies/'+job_id
        system.start_job(job)
        return {"message": "학습을 시작했습니다." if command == "train" else "백테스트를 시작했습니다.", "job": job}




def framework_catalog():
    from .platform.framework_operations import catalog
    return catalog()


def finrl_workspace():
    from .finrl.operations import stock_state
    try:return stock_state()
    except (ValueError,OSError,RuntimeError) as exc:raise HTTPException(503,str(exc)) from exc


def framework_providers():
    from .finrl_trading.operations import provider_status
    return provider_status()


@private_api.post('/api/framework/providers/{provider}')
def framework_provider_save(provider:str,values:dict):
    from .finrl_trading.operations import save_provider
    try:return save_provider(provider,values)
    except (ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc))


@private_api.post('/api/framework/{action}')
def framework_task(action:str,parameters:dict):
    from .platform.framework_operations import ACTIONS,validate_native_call
    if action not in ACTIONS:raise HTTPException(404,'등록된 공식 실행 기능이 아닙니다.')
    if action=='native_call':
        try:validate_native_call(parameters)
        except (ValueError,TypeError,KeyError) as exc:raise HTTPException(400,str(exc)) from exc
    with system.job_lock:
        if system.job_state()['running']:raise HTTPException(409,'현재 공식 작업 종료 후 실행하세요.')
        job_id=uuid.uuid4().hex
        job=system.start_job({'id':job_id,'command':'framework','action':action,'parameters':parameters,
            'currency':parameters.get('currency','USD'),'symbols':parameters.get('symbols',[]),'resume':False,
            'status':'starting','started_at':now(),'log':f'jobs/{job_id}.log','output':'framework-jobs/'+job_id})
    return {'message':ACTIONS[action][0]+' 실행을 시작했습니다.','job':job}


@private_api.get('/api/framework/result/{job_id}')
def framework_result(job_id:str,kind:Literal['json','csv']='json'):
    if not re.fullmatch('[0-9a-f]{32}',job_id):raise HTTPException(400,'작업 ID가 유효하지 않습니다.')
    path=RUNTIME/'framework-jobs'/job_id/('result.'+kind)
    if not path.is_file():raise HTTPException(404,'해당 작업의 결과 파일이 없습니다.')
    return FileResponse(path,filename=path.name)


@private_api.get('/api/framework/artifact/{job_id}/{filename:path}')
def framework_artifact(job_id:str,filename:str):
    if not re.fullmatch('[0-9a-f]{32}',job_id):raise HTTPException(400,'결과 경로가 유효하지 않습니다.')
    folder=(RUNTIME/'framework-jobs'/job_id).resolve();path=(folder/filename).resolve()
    recorded=read_json(folder/'result.json').get('files',[])
    if not path.is_relative_to(folder) or (filename not in recorded and not re.fullmatch(r'figure_[0-9]+\.png',filename)):raise HTTPException(400,'기록된 결과 파일만 열 수 있습니다.')
    if not path.is_file():raise HTTPException(404,'실제 생성된 그림 파일이 없습니다.')
    return FileResponse(path)


@private_api.post("/api/train")
def train(req: RunRequest):
    return launch("train", req)


@private_api.post("/api/backtest")
def backtest(req: RunRequest):
    return launch("backtest", req)


@private_api.post("/api/collect")
def collect(req:CollectionRequest):
    try:
        if datetime.fromisoformat(req.start_date)>datetime.fromisoformat(req.end_date):
            raise ValueError("시작일이 종료일보다 늦습니다.")
    except ValueError as exc:
        raise HTTPException(400,str(exc))
    allowed={r["symbol"] for r in database()["instruments"] if r["eligible"] and r["currency"]=="USD"}
    if not set(req.symbols)<=allowed:
        raise HTTPException(400,"현재 FMP 수집은 등록된 미국 주식·ETF만 선택할 수 있습니다.")
    info=connections()
    if info["data"]["status"]!="configured":
        raise HTTPException(409,info["data"]["reason"])
    with system.job_lock:
        if system.job_state()["running"]:
            raise HTTPException(409,"다른 작업을 마친 뒤 수집하세요.")
        RUNTIME.mkdir(parents=True,exist_ok=True)
        job_id=uuid.uuid4().hex
        (RUNTIME/"jobs").mkdir(exist_ok=True)
        job={"id":job_id,"command":"collect","status":"starting","started_at":now(),
             "symbols":sorted(set(req.symbols)),"currency":"USD","resume":False,
             "start_date":req.start_date,"end_date":req.end_date,"log":f"jobs/{job_id}.log"}
        system.start_job(job)
    return {"message":"FinRL-X 원본 가격 수집을 시작했습니다.","job":job}


def champions():
    from .platform.sac_champion import list_champions
    return {"items":list_champions()}


@private_api.post("/api/champions/create")
def champion_create(request:ChampionRequest):
    if system.job_state()["running"]:raise HTTPException(409,"현재 학습·수집·백테스트가 끝난 뒤 생성하세요.")
    from .platform.operations_settings import settings
    recent=read_json(RUNTIME/"job.json")
    if recent.get('command') not in ('train','backtest'):recent={}
    request.currency=request.currency or recent.get("currency") or "USD"
    if not request.symbols:
        configured=settings().symbols
        request.symbols=configured or (recent.get("symbols") if recent.get("currency")==request.currency else []) or []
        if not request.symbols:
            request.symbols=[row["symbol"] for row in database()["instruments"] if row["currency"]==request.currency and row["eligible"] and row["stored"]]
    if not request.symbols:raise HTTPException(400,"기존 운영·학습 종목 구성이 없습니다. 종목을 등록한 뒤 생성하세요.")
    if len(request.symbols)!=len(set(request.symbols)) or len(request.experts)!=len(set(request.experts)):
        raise HTTPException(400,"종목과 Expert는 중복 없이 선택하세요.")
    request.symbols=sorted(request.symbols);request.experts=sorted(request.experts)
    instruments=read_json(ROOT/"configs/instruments.json").get("instruments",[])
    markets={item["symbol"]:item for item in instruments}
    valid_markets=("KRX","KOSDAQ") if request.currency=="KRW" else ("US","NASDAQ","NYSE","NYSEARCA","AMEX")
    invalid=[symbol for symbol in request.symbols if symbol not in markets or markets[symbol].get("market") not in valid_markets or markets[symbol].get("asset_class") not in ("equity","etf")]
    if invalid:raise HTTPException(400,"선택 시장의 등록 주식·ETF가 아닙니다: "+", ".join(invalid))
    from .platform.sac_champion import create
    from .finrl.framework import champion_structure_environment
    env=None
    try:
        env=champion_structure_environment(request.currency,request.symbols,ExpertRegistry(),request.experts)
        result=create(request.currency,request.symbols,request.experts,env,algorithm=request.algorithm)
        return result
    except HTTPException:raise
    except (ValueError,RuntimeError,OSError,KeyError,MemoryError,FileExistsError) as exc:raise HTTPException(400,str(exc)) from exc
    finally:
        if env is not None:env.close()


@private_api.get("/api/checkpoint")
def checkpoint_download(path:str):
    target=(RUNTIME/path).resolve()
    if not target.is_relative_to(RUNTIME.resolve()) or target.suffix!='.zip' or target.stem not in MODELS or not target.exists():
        raise HTTPException(404,"정책 파일이 없습니다.")
    return FileResponse(target,filename=target.parent.name+'-'+target.name)


@private_api.post("/api/stop")
def stop():
    try:return system.stop_job()
    except RuntimeError as exc:raise HTTPException(409,str(exc)) from exc


@private_api.post("/api/experts/select")
def select(req: Selection):
    with system.job_lock:
        with system.job_lock:
            if system.job_state()["running"]:
                raise HTTPException(409, "실행을 마친 뒤 Expert 구성을 변경하세요.")
            try:
                ExpertRegistry().select(sorted(set(req.active)))
            except (ValueError, OSError) as exc:
                raise HTTPException(400, str(exc)) from exc
        return {"message": "Expert 선택을 저장했습니다."}


@private_api.post("/api/experts/register")
def register(req: Registration):
    with system.job_lock:
        with system.job_lock:
            if system.job_state()["running"]:
                raise HTTPException(409, "실행을 마친 뒤 패키지를 등록하세요.")
            registry = read_json(ROOT / "configs/experts.json")
            if req.slot in registry.get("experts", {}):
                raise HTTPException(409, "이미 사용 중인 슬롯 이름입니다. 다른 이름으로 등록하세요.")
            try:
                ExpertRegistry().register(req.path, req.slot)
            except (ValueError, RuntimeError, OSError, KeyError) as exc:
                raise HTTPException(400, str(exc)) from exc
        return {"message": "Expert 패키지를 등록했습니다."}


class ControlRequest(BaseModel):
    enabled:bool


class OrderRequest(BaseModel):
    currency:Literal["KRW","USD"]
    symbol:str
    action:Literal["BUY","SELL"]
    quantity:int=Field(gt=0)


class CredentialRequest(BaseModel):
    environment:Literal["paper","real"]="real"
    app_key:str=""
    secret:str=""
    account:str=""




@private_api.post("/api/controls/{name}")
def operation_control(name:Literal["feed","paper","engine","learning"],request:ControlRequest):
    try:return {"controls":runtime.command(name,request.enabled)}
    except (ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc))


@private_api.post("/api/orders")
def paper_order(request:OrderRequest):
    try:return runtime.manual_order(request.symbol,request.currency,request.action,request.quantity)
    except (ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc))


def provider():
    from .provider_credentials import public_status
    from .platform.operations_settings import settings
    return public_status(settings().state_dir)


@private_api.post("/api/provider/connect")
def connect_provider(request:CredentialRequest):
    from .provider_credentials import connect_credentials
    from .platform.operations_settings import settings
    if runtime.controls['feed']:raise HTTPException(409,'기존 시세 수신을 중지한 뒤 공급원 인증을 변경하세요.')
    try:return connect_credentials(settings().state_dir,request.environment,request.app_key,request.secret,request.account)
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(400,str(exc))


@private_api.post("/api/provider/test")
def check_provider(request:CredentialRequest):
    from .provider_credentials import test_connection
    from .platform.operations_settings import settings
    try:return test_connection(settings().state_dir,"kiwoom",request.environment)
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(400,str(exc))


@private_api.post("/api/provider/public")
def public_feed():
    if runtime.controls['feed']:raise HTTPException(409,'시세 수신을 중지한 뒤 공급원을 변경하세요.')
    from .provider_credentials import _write_settings,read_settings
    from .platform.operations_settings import settings
    root=settings().state_dir;value=read_settings(root);value['provider']='yahoo'
    _write_settings(root,value)
    return {"message":"기존 공개 시세 공급원을 선택했습니다."}


@private_api.post('/api/provider/disconnect')
def disconnect_provider():
    runtime.command('feed',False)
    return {'message':'시세 연결 중지를 요청했습니다. 저장된 인증 정보는 유지합니다.'}


def operational_settings():
    from .platform.operations_settings import settings
    current=settings()
    return {"risk":vars(current.risk),"data":vars(current.data),"symbols":current.symbols,
            "expert_devices":current.resources.expert_devices,"sac_readonly":source_settings()}


@private_api.post("/api/settings")
def save_operational_settings(values:dict):
    from .platform.operations_settings import update
    if set(values)-{"risk","data","symbols","expert_devices"}:raise HTTPException(400,"운영 설정만 변경할 수 있습니다. SAC 설정은 원본값을 사용합니다.")
    if runtime.controls['feed']:raise HTTPException(409,"시세 수신을 멈춘 뒤 운영 설정을 변경하세요.")
    try:value=update(values)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc
    if runtime.account:
        from .platform.operations_settings import settings
        current=settings();runtime.account.fee=current.risk.fee;runtime.account.slippage=current.risk.slippage
    if system.expert_pool:
        system.expert_pool.settings.resources.expert_devices=value.get('expert_devices',{})
    return {"settings":value}




@private_api.post("/api/library/{kind}")
def library_job(kind:str,payload:dict):
    if kind=='stop':return stop_library()
    if system.job_state()["running"] and kind not in ("search","inspect"):
        raise HTTPException(409,"현재 SAC 작업 종료 후 모델 구성을 변경하세요.")
    try:return library_manager.start(kind,payload)
    except (ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc))


def model_files():
    registry=read_json(ROOT/'configs/experts.json');registered={item['package']['file']:key for key,item in registry.get('experts',{}).items()}
    for key,item in registry.get('experts',{}).items():
        if item['package']['file'].endswith('.json'):
            package=read_json(MODEL_DIR/item['package']['file'])
            if package.get('weight_asset'):registered[package['weight_asset']['file']]=key
    rows=[]
    if MODEL_DIR.exists():
        for path in MODEL_DIR.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in (".pt",".pth",".gguf",".json",".safetensors",".zip"):continue
            relative=path.relative_to(MODEL_DIR).as_posix()
            rows.append({"path":str(path),"name":relative,"format":path.suffix.lower(),
                "bytes":path.stat().st_size,"registered":registered.get(relative)})
    return {"root":str(MODEL_DIR),"files":rows}


@private_api.post("/api/checkpoints/restore")
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




@private_api.post('/api/system/apply')
def apply_changes(request:dict):
    try:return start_apply(request.get('target','frontend'))
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc


@private_api.get('/api/system/blockers')
def restart_blockers():
    return {'items':busy()}


@private_api.post('/api/system/prepare-restart')
def prepare_restart():
    with system.job_lock:
        blockers=busy()
        if blockers:raise HTTPException(409,' · '.join(blockers))
        system.restarting=True
        runtime.close()
    return {'ready':True}


@private_api.get('/api/system/check')
def system_check():
    return check_system()


@private_api.post('/api/system/start')
def start_system(values:dict):
    currencies=values.get('currencies',['USD','KRW'])
    if not currencies or not set(currencies)<= {'USD','KRW'}:raise HTTPException(400,'USD/KRW 운영 통화를 선택하세요.')
    try:return system.start(list(dict.fromkeys(currencies)))
    except ValueError as exc:raise HTTPException(409,str(exc))


@private_api.post('/api/system/stop')
def stop_system():
    return system.stop()


def stop_library():
    library_manager.cancelled.set();runtime.cancel_inference.set()
    return {'message':'모델 작업 중지를 요청했습니다. 진행 중 연산은 종료 상태를 확인하세요.'}


@private_api.post('/api/model/open-directory')
def open_model_directory():
    if not MODEL_DIR.is_dir():raise HTTPException(404,'실제 모델 폴더가 없습니다.')
    if os.name!='nt':raise HTTPException(400,'현재 폴더 열기는 Windows에서 제공합니다.')
    os.startfile(MODEL_DIR)
    return {'path':str(MODEL_DIR)}


@app.on_event("shutdown")
def close_operations():
    runtime.close()
    system.close_models()

app.add_middleware(GZipMiddleware)
system.command_router=private_api
from .menu_registry import bind as bind_menu_commands
bind_menu_commands(private_api.routes)
