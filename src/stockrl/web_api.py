"""Local HTTP adapter for official_cli, DataStore files and frozen Expert registry."""
from __future__ import annotations

import ast
import csv
import json
import math
import os
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import psutil
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .framework import ROOT
from .state_io import atomic_json, read_json
from .platform.resources import ResourceMonitor

RUNTIME = ROOT / "runtime/official"
DB = ROOT / "data/finrl_trading.db"
MODEL_DIR = Path.home() / "Desktop/모델"
ENVIRONMENT = "finrl.meta.env_portfolio_allocation.env_portfolio.StockPortfolioEnv"
app = FastAPI(title="FinRL-X local workspace", version="2")
FRONTEND_DIST = ROOT / "frontend/dist"
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets"), check_dir=False), name="react-assets")
launch_lock = threading.Lock()
resource_monitor = ResourceMonitor(ROOT)
database_cache = {"stamp": None, "value": None}
children = {}


@app.middleware("http")
async def local_writes(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method != "GET" and origin and origin not in {
        "http://127.0.0.1:5173", "http://localhost:5173",
        "http://127.0.0.1:8766", "http://localhost:8766"
    }:
        return JSONResponse({"detail": "로컬 화면에서 요청하세요."}, status_code=403)
    if request.method!='GET':
        from .platform.system_operations import system,apply_running
        allowed_stop=request.url.path in ('/api/stop','/api/system/stop','/api/system/prepare-restart')
        if (apply_running() or system.restarting) and not allowed_stop and request.url.path!='/api/system/apply':
            return JSONResponse({'detail':'변경 적용/서버 갱신 중입니다. 기존 작업은 보존합니다.'},status_code=409)
        path=request.url.path
        conflict=path in ('/api/train','/api/backtest','/api/stop','/api/collect','/api/settings','/api/checkpoints/restore','/api/system/stop') or path.startswith(('/api/controls/','/api/experts/','/api/provider/')) and path!='/api/provider/test' or path.startswith('/api/library/') and path not in ('/api/library/search','/api/library/inspect')
        if conflict:
            system.cancel()
    return await call_next(request)


class RunRequest(BaseModel):
    currency: Literal["USD", "KRW"] = "USD"
    symbols: list[str] = Field(default_factory=list, max_length=1000)
    resume: bool = False
    champion_path: str | None = None


class ChampionRequest(BaseModel):
    currency:Literal["USD","KRW"]="USD"
    symbols:list[str]=Field(min_length=1,max_length=1000)
    experts:list[str]=Field(default_factory=list,max_length=128)
    source_path:str|None=None


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


def file_info(path):
    return {"exists": path.is_file(), "bytes": path.stat().st_size if path.is_file() else 0,
            "modified": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if path.is_file() else None}


@lru_cache(maxsize=1)
def source_settings():
    """Read constants from the exact checked-out call sites without loading learners."""
    from .framework import sac_example
    _, params, steps = sac_example()
    framework = ast.parse((ROOT / "src/stockrl/framework.py").read_text(encoding="utf8"))
    env_args = {}
    for node in ast.walk(framework):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "StockPortfolioEnv":
            for kw in node.keywords:
                try:
                    env_args[kw.arg] = ast.literal_eval(kw.value)
                except (ValueError, TypeError):
                    pass
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
                    "feature_extractor": policy.features_extractor_class.__name__}
    versions = {name: importlib.metadata.version(name) for name in ("stable-baselines3","finrl","torch","gymnasium")}
    return {"parameters": params, "steps_per_run": steps, "environment": ENVIRONMENT,
            "environment_args": env_args, "covariance_lookback": 252, "rolling_days": [1095, 365],
            "sb3_defaults": defaults, "policy": architecture, "versions": versions,
            "parameter_source": "FinRL-X/src/strategies/rl_model.py::train_sac",
            "environment_source": "src/stockrl/framework.py::training_environment",
            "save_policy": "실행 정상 종료 시 SAC와 Replay 저장",
            "observation": "원본 환경 관측 + 시장 예측 4값 + 매매 판단 4값",
            "notes": ["원본 StockPortfolioEnv.step은 transaction_cost_pct를 차감하지 않습니다.",
                      "BacktestEngine은 투자 비중을 합계 100%로 정규화하고 거래 비용을 적용합니다.",
                      "실시간 수신·실제 주문은 현재 실행 경로에 연결되어 있지 않습니다."]}


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
    from .framework import policy_files
    selected=Path(selected) if selected is not None else policy_files()
    path = selected / "sac.zip"
    replay = selected / "replay.pkl"
    identity = read_json(selected / "dataset.json")
    result = {"file": file_info(path), "replay": file_info(replay), "identity": identity,
              "compatible": False, "reasons": [], "num_timesteps": None, "updates": None}
    if not path.is_file():
        result["reasons"].append("저장된 정책이 없습니다.")
        return result
    try:
        with zipfile.ZipFile(path) as archive:
            state = json.loads(archive.read("data"))
        result.update(num_timesteps=state.get("num_timesteps"), updates=state.get("_n_updates"),
                      observation_shape=state.get("observation_space", {}).get("_shape"),
                      action_shape=state.get("action_space", {}).get("_shape"),
                      parameters={k: state.get(k) for k in settings["parameters"]},
                      policy_kwargs=state.get("policy_kwargs"))
        expected = {"currency": identity.get("currency"), "symbols": identity.get("symbols"),
                    "sac_example": settings["parameters"], "environment": settings["environment"],
                    "rolling_days": settings["rolling_days"]}
        if not identity.get("symbols") or not identity.get("currency"):
            result["reasons"].append("저장 모델의 통화·종목 정보가 없습니다.")
        is_champion=bool(identity.get("feature_extractor"))
        if (not is_champion and identity != expected) or (is_champion and any(identity.get(k)!=v for k,v in expected.items())):
            result["reasons"].append("현재 SAC 설정·StockPortfolioEnv 식별 정보와 일치하지 않는 이전 저장본입니다.")
        for key in ("batch_size", "buffer_size", "learning_rate", "learning_starts"):
            if state.get(key) != settings["parameters"][key]:
                result["reasons"].append(f"{key}: 저장값 {state.get(key)} / 현재값 {settings['parameters'][key]}")
        if identity.get('symbols') and is_champion:
            expected_shape=[identity.get('base_observation_dim',0)+64*len(identity.get('champion_experts',[]))+identity.get('account_feature_size',16)]
            if result['observation_shape']!=expected_shape or result['action_shape']!=[len(identity['symbols'])]:
                result['reasons'].append(f"통합 SAC Champion 관측/행동 크기 불일치: {result['observation_shape']}/{result['action_shape']} vs {expected_shape}/[{len(identity['symbols'])}]")
        elif identity.get('symbols'):
            from finrl import config
            count=len(identity['symbols']);expected_shape=[(count+len(config.INDICATORS))*count+8]
            if result['observation_shape']!=expected_shape or result['action_shape']!=[count]:
                result['reasons'].append(f"원본 환경+Expert 관측/행동 크기 불일치: {result['observation_shape']}/{result['action_shape']} vs {expected_shape}/[{count}]")
        result['policy_compatible']=not result['reasons']
        if not replay.is_file():
            result["reasons"].append("이어 학습에 필요한 Replay 파일이 없습니다.")
        result["compatible"] = not result["reasons"]
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        result["reasons"].append("정책 파일 읽기 실패: " + str(exc))
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
    from .framework import policy_files
    path = policy_files() / "replay.pkl"
    if not path.exists():
        return {"status":"missing"}
    try:
        return replay_metadata(str(path),path.stat().st_mtime_ns,path.stat().st_size)
    except Exception as exc:
        return {"status":"unreadable","error":str(exc)}


def checkpoints(settings):
    paths = ([RUNTIME/"sac.zip"] if (RUNTIME/"sac.zip").is_file() else []) + sorted((RUNTIME/"archives").glob("*/sac.zip")) + sorted((RUNTIME/"policies").glob("*/sac.zip")) + sorted((RUNTIME/"champions").glob("*/sac.zip"))
    items=[]
    for path in paths:
        try:
            with zipfile.ZipFile(path) as archive:
                data=json.loads(archive.read("data"))
            identity=read_json(path.parent/"dataset.json")
            compatible=identity.get("environment")==settings["environment"] and identity.get("sac_example")==settings["parameters"]
            items.append({"name":path.parent.name if path.parent!=RUNTIME else "현재 정책",
                          "path":path.relative_to(RUNTIME).as_posix(),"file":file_info(path),
                          "num_timesteps":data.get("num_timesteps"),"updates":data.get("_n_updates"),
                          "identity":identity,"compatible":compatible})
        except (OSError,ValueError,KeyError,zipfile.BadZipFile):
            continue
    return items


def capabilities():
    return {
        "learning":{"status":"supported","reason":"원본 train_sac · SB3 SAC 시작·중단·동일 정책 이어 학습","source":"stockrl.framework.train"},
        "expert_selection":{"status":"supported","reason":"Frozen Expert 등록·선택·같은 모델 정밀도 교체·해제","source":"stockrl.expert_registry_native.ExpertRegistry"},
        "collection":{"status":"supported","reason":"FinRL-X FMP 가격 수집 모듈. API 인증이 있어야 원격 수집 가능합니다.","source":"FinRL-X/src/data/data_fetcher.py::fetch_price_data"},
        "paper_accounts":{"status":"supported","reason":"원본 PaperAccount의 KRW/USD 독립 잔고·보유·체결·손익 기능이 연결되어 있습니다.","source":"stockrl.paper_account.PaperAccount"},
        "live_feed":{"status":"supported","reason":"복구한 LiveMarketCollector와 Kiwoom BrokerStreams의 완료 시세를 DataStore·가상계좌에 전달합니다.","source":"stockrl.live_feed"},
        "kiwoom":{"status":"supported","reason":"기존 보안 저장소·인증·실시간 수신 모듈 연결. 실제 수신에는 유효한 인증이 필요합니다. 실제 주문은 전송하지 않습니다.","source":"stockrl.provider_credentials / platform.kiwoom_data"},
        "alpaca":{"status":"not_connected","reason":"공식 서브모듈에는 Alpaca 모듈이 있지만 현재 SAC 작업에 연결되지 않았습니다.","source":"FinRL-X/src/trading/alpaca_manager.py"},
        "conversion":{"status":"supported","reason":"기존 정밀도 변환과 품질 비교·후보 선택 함수를 연결합니다. 변환은 새 파일로 저장됩니다.","source":"stockrl.platform.expert_conversion / expert_optimizer"},
        "discovery":{"status":"supported","reason":"기존 HF/GitHub 검색·가중치 호환 확인·다운로드·자동 등록 함수가 연결되어 있습니다.","source":"stockrl.platform.expert_discovery / expert_acquisition"},
        "checkpoint_restore":{"status":"supported","reason":"기존 SB3 파일을 변경하지 않고 선택하여 복원·이어 학습에 사용합니다. 이전 자체 정책 형식은 호환되지 않습니다.","source":"stockrl.framework.policy_files"},
        "settings_edit":{"status":"supported","reason":"시세·가상계좌·Expert 장치의 기존 운영 설정을 편집합니다. SAC 학습값은 변경하지 않습니다.","source":"stockrl.platform.operations_settings"},
    }


def expert_state():
    from .platform.operations_runtime import runtime
    registry = read_json(ROOT / "configs/experts.json", {"active": [], "experts": {}})
    status = read_json(ROOT / "runtime/experts/status.json")
    rows = []
    for key, item in registry.get("experts", {}).items():
        reference = item.get("package", {})
        path = (MODEL_DIR / reference.get("file", "")).resolve()
        available = path.is_relative_to(MODEL_DIR.resolve()) and path.is_file()
        if available and reference.get("bytes") is not None:
            available = path.stat().st_size == reference["bytes"]
        rows.append({**item, "id": key, "active": key in registry.get("active", []),
                     "package_available": available, "package_path": str(path),
                     "inference": status.get("experts", {}).get(key),
                     "resources": status.get("resources", {}).get(key, {}),
                     "current_resources": runtime.pool.metrics.get(key,{}) if runtime.pool else {},
                     "loaded": bool(runtime.pool and key in runtime.pool.loaded)})
    return {"active": registry.get("active", []), "items": rows, "as_of": status.get("as_of"),
            "reported": file_info(ROOT / "runtime/experts/status.json").get("modified")}


def process_for(job):
    try:
        process = psutil.Process(int(job["pid"]))
        if job.get("process_created") and abs(process.create_time() - job["process_created"]) > 0.1:
            return None
        if process.is_running() and any(x in " ".join(process.cmdline()) for x in ("stockrl.job_worker", "stockrl.official_cli")):
            return process
    except (psutil.Error, KeyError, ValueError):
        pass
    return None


def job_state():
    job = read_json(RUNTIME / "job.json")
    if not job:
        try:
            pid = int((RUNTIME / "training.pid").read_text())
            process = process_for({"pid": pid})
            if process:
                job = {"pid": pid, "status": "running", "command": "legacy", "log": "training.log"}
        except (OSError, ValueError):
            pass
    process = process_for(job) if job else None
    if job.get("status") in ("starting", "running") and not process:
        job["status"] = "unknown"
        job["detail"] = "프로세스가 종료됐지만 완료 기록이 없습니다. 로그를 확인하세요."
    result = {**job, "running": process is not None, "log_text": ""}
    name = job.get("log", "training.log")
    path = RUNTIME / name
    if path.is_file() and path.resolve().is_relative_to(RUNTIME.resolve()):
        with path.open("rb") as stream:
            stream.seek(max(0, path.stat().st_size - 32000))
            result["log_text"] = stream.read().decode("utf8", errors="replace")
    import re
    measured={}
    for key,value in re.findall(r"\|\s*([a-z_]+)\s*\|\s*([-+\deE.]+)\s*\|",result["log_text"]):
        try: measured[key]=float(value)
        except ValueError: pass
    result["measurements"]=measured
    return result


def evaluation():
    path = RUNTIME / "backtest.csv"
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
            "report": read_json(RUNTIME / "backtest_metrics.json")}


@app.get("/api/health")
def health():
    return {"ok": True, "service": "finrlx-react-sac", "project": str(ROOT.resolve()), "pid": os.getpid(),"deployment_id":os.environ.get('STOCKRL_APPLY_ID')}


@app.get("/", include_in_schema=False)
def react_index():
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(503, "React 빌드가 없습니다. 서버켜기.cmd를 실행하세요.")
    return FileResponse(index, headers={"Cache-Control": "no-cache"})


@app.get("/api/modules")
def modules():
    paths = [*sorted((ROOT / "src/stockrl").rglob("*.py")),
             *sorted((ROOT / "FinRL-X/src").rglob("*.py"))]
    items = []
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        except (UnicodeError, SyntaxError) as exc:
            items.append({"path": path.relative_to(ROOT).as_posix(),
                          "description": "소스 형식 확인 필요: " + str(exc), "functions": []})
            continue
        functions = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                functions.append(node.name)
                functions.extend(node.name + "." + child.name for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)))
        items.append({"path": path.relative_to(ROOT).as_posix(),
                      "description": ast.get_docstring(tree), "functions": functions})
    return {"items": items}


@app.get("/api/result/{kind}")
def result_table(kind: Literal["weights", "trades"], limit: int = Query(1000, ge=1, le=5000)):
    path = RUNTIME / ("backtest_" + kind + ".csv")
    if not path.is_file():
        return {"columns": [], "rows": [], "total": 0}
    import pandas as pd
    frame = pd.read_csv(path)
    frame.columns = [str(c).replace("Unnamed: 0", "index") for c in frame.columns]
    finite = frame.replace([float("inf"), -float("inf")], None).astype(object).where(frame.notna(), None)
    return {"columns": list(frame.columns), "rows": finite.tail(limit).to_dict("records"), "total": len(frame)}


@app.get("/api/state")
def state():
    settings = source_settings()
    db = database()
    job = job_state()
    workers = {"learner": {"pid": job.get("pid"), "alive": job["running"]}}
    model=model_state(settings)
    model["replay_state"]=saved_replay()
    experts=expert_state()
    experts["observation_connection"]={"size":8,"configured":True,"recorded":bool(experts.get("as_of")),
        "last_success":{role:sum(1 for row in experts["items"] if row["active"] and row.get("inference") and row["inference"].get("status")=="ready" and row.get("role")==role) for role in ("market","action")}}
    from .platform.operations_runtime import runtime
    from .platform.library_operations import library
    from .platform.system_operations import system,apply_state
    return {"architecture":"finrlx-official-sac-v2","updated_at": now(), "settings": settings, "model": model,
            "data": db, "experts": experts, "job": job, "evaluation": evaluation(),
            "checkpoints":checkpoints(settings),"capabilities":capabilities(),
            "operations":runtime.snapshot(),"library":library.snapshot(),"automation":{"apply":apply_state(),"system":system.snapshot()},
            "resources": resource_monitor.snapshot(workers)}


@app.get("/api/connections")
def connections():
    from .framework import finrlx
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


@app.get("/api/logs")
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


@app.get("/api/prices")
def price_history(symbol: str, limit: int = Query(300, ge=1, le=2000)):
    if not DB.exists():
        raise HTTPException(404, "가격 DB가 없습니다.")
    with sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT date,open,high,low,close,volume FROM price_data WHERE ticker=? ORDER BY date DESC LIMIT ?", (symbol, limit)).fetchall()
    return {"symbol": symbol, "rows": [dict(row) for row in reversed(rows)]}


@app.get("/api/download/{name}")
def download(name: Literal["backtest.csv", "backtest_metrics.json", "backtest_weights.csv", "backtest_trades.csv", "sac.zip", "dataset.json"]):
    from .framework import policy_files
    path = (policy_files() if name in ('sac.zip','dataset.json') else RUNTIME) / name
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
        elif item["observations"] <= 252:
            errors.append(symbol + ": 공분산을 만들 관측이 252개보다 많아야 합니다.")
    settings = source_settings()
    model = model_state(settings)
    if req.champion_path:
        from .platform.sac_champion import load_spec,MODEL_DIR
        source=Path(req.champion_path).expanduser().resolve()
        try:
            if not source.is_relative_to(MODEL_DIR.resolve()) or not source.name.startswith('sac_champion_'):
                raise ValueError('모델 폴더의 SAC Champion을 선택하세요.')
            champion=load_spec(source);identity=champion['identity']
            checkpoint=Path(champion['checkpoint'])
            if not checkpoint.is_absolute():checkpoint=RUNTIME/checkpoint
            if not checkpoint.is_file():raise ValueError('Champion의 SB3 학습 체크포인트가 없습니다.')
            if identity.get('currency')!=req.currency or identity.get('symbols')!=symbols:
                raise ValueError('선택한 Champion의 통화·종목 구성이 다릅니다.')
        except (ValueError,OSError,KeyError,RuntimeError) as exc:
            errors.append('SAC Champion: '+str(exc))
    if (command == "backtest" or req.resume) and not req.champion_path:
        if not model["compatible"]:
            errors.extend(model["reasons"])
        if model["identity"].get("currency") != req.currency or model["identity"].get("symbols") != symbols:
            errors.append("저장 정책의 통화·종목 구성과 다릅니다.")
    if not req.champion_path:
        experts = expert_state()
        for row in experts["items"]:
            if row["active"] and not row["package_available"]:
                errors.append(row["id"] + ": 활성 Expert 패키지가 없거나 크기가 다릅니다.")
    if symbols and not errors:
        with sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True) as connection:
            placeholders = ",".join("?" for _ in symbols)
            dates = [r[0] for r in connection.execute(f"SELECT DISTINCT date FROM price_data WHERE ticker IN ({placeholders}) ORDER BY date", symbols)]
        from pandas import Timedelta, to_datetime
        dates = to_datetime(dates, utc=True)
        trade = dates.max() + Timedelta(days=1)
        after_covariance = dates[252:]
        train_count = int(((after_covariance >= trade - Timedelta(days=1095)) & (after_covariance < trade - Timedelta(days=365))).sum())
        test_count = int(((after_covariance >= trade - Timedelta(days=365)) & (after_covariance < trade)).sum())
        if train_count < 2 and command == "train":
            errors.append("252개 공분산 관측 제외 후 rolling 학습 구간에 데이터가 부족합니다.")
        if test_count < 2:
            errors.append("rolling 평가 구간에 데이터가 부족합니다.")
        periods = {"training_observations": train_count, "test_observations": test_count,
                   "trade_date": str(trade), "train_start": str(trade-Timedelta(days=1095)),
                   "train_end_exclusive": str(trade-Timedelta(days=365))}
    else:
        periods = None
    return {"ok": not errors, "errors": errors, "symbols": symbols, "currency": req.currency, "periods": periods,
            "mode": "이어 학습" if req.resume else "새 학습" if command == "train" else "백테스트",
            "steps_per_run": settings["steps_per_run"]}


@app.post("/api/preflight/{command}")
def check(command: Literal["train", "backtest"], req: RunRequest):
    return preflight(req, command)


def launch(command, req,preserve_output=False):
    with launch_lock:
        if job_state()["running"]:
            raise HTTPException(409, "학습 또는 평가가 실행 중입니다.")
        checked = preflight(req, command)
        if not checked["ok"]:
            raise HTTPException(400, "\n".join(checked["errors"]))
        RUNTIME.mkdir(parents=True, exist_ok=True)
        job_id = uuid.uuid4().hex
        job = {"id": job_id, "status": "starting", "command": command, "currency": req.currency,
               "symbols": checked["symbols"], "resume": req.resume, "started_at": now(),
               "log": f"jobs/{job_id}.log", "finished_at": None, "exit_code": None}
        if req.champion_path:
            from .platform.sac_champion import _next_version
            _,target=_next_version()
            job.update(champion_path=str(Path(req.champion_path).expanduser().resolve()),
                champion_output=str(target),output='champions/'+target.stem)
        elif preserve_output:job['output']='policies/'+job_id
        (RUNTIME / "jobs").mkdir(exist_ok=True)
        env = os.environ.copy()
        env.update(PYTHONPATH=str(ROOT / "src"), PYTHONUTF8="1")
        with (RUNTIME / job["log"]).open("w", encoding="utf8") as output:
            process = subprocess.Popen([sys.executable, "-m", "stockrl.job_worker", job_id],
                cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        job.update(pid=process.pid, process_created=psutil.Process(process.pid).create_time())
        children[job_id] = process
        atomic_json(job, RUNTIME / "job.json")
        (RUNTIME / "training.pid").write_text(str(process.pid))
        return {"message": "학습을 시작했습니다." if command == "train" else "백테스트를 시작했습니다.", "job": job}


@app.post("/api/train")
def train(req: RunRequest):
    return launch("train", req)


@app.post("/api/backtest")
def backtest(req: RunRequest):
    return launch("backtest", req)


@app.post("/api/collect")
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
    with launch_lock:
        if job_state()["running"]:
            raise HTTPException(409,"다른 작업을 마친 뒤 수집하세요.")
        RUNTIME.mkdir(parents=True,exist_ok=True)
        job_id=uuid.uuid4().hex
        (RUNTIME/"jobs").mkdir(exist_ok=True)
        job={"id":job_id,"command":"collect","status":"starting","started_at":now(),
             "symbols":sorted(set(req.symbols)),"currency":"USD","resume":False,
             "start_date":req.start_date,"end_date":req.end_date,"log":f"jobs/{job_id}.log"}
        env=os.environ.copy()
        env.update(PYTHONPATH=str(ROOT/"src"),PYTHONUTF8="1")
        with (RUNTIME/job["log"]).open("w",encoding="utf8") as output:
            process=subprocess.Popen([sys.executable,"-m","stockrl.job_worker",job_id],
                cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        job.update(pid=process.pid,process_created=psutil.Process(process.pid).create_time())
        children[job_id]=process
        atomic_json(job,RUNTIME/"job.json")
        (RUNTIME/"training.pid").write_text(str(process.pid))
    return {"message":"FinRL-X 원본 가격 수집을 시작했습니다.","job":job}


@app.get("/api/champions")
def champions():
    from .platform.sac_champion import list_champions
    return {"items":list_champions()}


def champion_environment(request):
    from .framework import prices,training_environment
    from .expert_registry_native import ExpertRegistry
    frame=prices(request.currency,request.symbols)
    if frame.empty:raise HTTPException(400,"선택 종목의 저장 가격을 찾지 못했습니다.")
    registry=ExpertRegistry()
    try:
        env=training_environment(frame,registry,champion_ids=request.experts)
        return env
    except BaseException:
        registry.close(cleanup=True)
        raise


@app.post("/api/champions/inspect")
def champion_inspect(request:ChampionRequest):
    from .platform.sac_champion import inspect
    if len(request.symbols)!=len(set(request.symbols)) or len(request.experts)!=len(set(request.experts)):
        raise HTTPException(400,"종목과 Expert는 중복 없이 선택하세요.")
    request.symbols=sorted(request.symbols);request.experts=sorted(request.experts)
    env=None
    try:
        env=champion_environment(request)
        env.reset()
        registry=env.registry
        inference=[{"id":key,"status":value.get('status'),"reason":value.get('reason'),
            "as_of":value.get('as_of'),"output_sample":value.get('output',[])[:8],
            "resources":registry.pool.metrics.get(key,{}) if registry.pool else {}}
            for key,value in registry.last_outputs.items()]
        registry.close()
        return inspect(request.currency,request.symbols,request.experts,env,inference)
    except HTTPException:raise
    except (ValueError,RuntimeError,OSError,KeyError,MemoryError) as exc:raise HTTPException(400,str(exc)) from exc
    finally:
        if env is not None:env.close()


@app.post("/api/champions/create")
def champion_create(request:ChampionRequest):
    if job_state()["running"]:raise HTTPException(409,"현재 학습·수집·백테스트가 끝난 뒤 생성하세요.")
    if len(request.symbols)!=len(set(request.symbols)) or len(request.experts)!=len(set(request.experts)):
        raise HTTPException(400,"종목과 Expert는 중복 없이 선택하세요.")
    request.symbols=sorted(request.symbols);request.experts=sorted(request.experts)
    from .platform.sac_champion import MODEL_DIR,create,load_spec
    if request.source_path:
        source=Path(request.source_path).expanduser().resolve()
        if not source.is_relative_to(MODEL_DIR.resolve()) or not source.name.startswith("sac_champion_"):
            raise HTTPException(400,"모델 폴더의 SAC Champion만 재조립할 수 있습니다.")
        try:
            previous=load_spec(source);identity=previous["identity"]
            if identity.get("currency")!=request.currency or identity.get("symbols")!=sorted(request.symbols):
                raise ValueError("기존 Champion과 통화·종목 구성이 달라 SAC Actor·Twin Critic을 호환 승계할 수 없습니다.")
        except (ValueError,OSError,KeyError,RuntimeError) as exc:raise HTTPException(400,str(exc)) from exc
    env=None
    try:
        env=champion_environment(request)
        env.reset()
        failures=[f"{key}: {value.get('reason','입력 또는 추론에 실패했습니다.')}" for key,value in env.registry.last_outputs.items() if value.get('status')!='ready']
        if failures:raise HTTPException(400,"선택 Expert 추론 검사를 통과하지 못했습니다. "+"; ".join(failures))
        env.registry.close()
        result=create(request.currency,request.symbols,request.experts,env,request.source_path)
        return result
    except HTTPException:raise
    except (ValueError,RuntimeError,OSError,KeyError,MemoryError,FileExistsError) as exc:raise HTTPException(400,str(exc)) from exc
    finally:
        if env is not None:env.close()


@app.get("/api/checkpoint")
def checkpoint_download(path:str):
    target=(RUNTIME/path).resolve()
    if not target.is_relative_to(RUNTIME.resolve()) or target.name!="sac.zip" or not target.exists():
        raise HTTPException(404,"정책 파일이 없습니다.")
    return FileResponse(target,filename=target.parent.name+"-sac.zip")


@app.post("/api/stop")
def stop():
    with launch_lock:
        job = read_json(RUNTIME / "job.json")
        process = process_for(job)
        if not process:
            raise HTTPException(409, "실행 중인 작업이 없습니다.")
        descendants = process.children(recursive=True)
        for child in reversed(descendants):
            try:
                child.terminate()
            except psutil.Error:
                pass
        process.terminate()
        psutil.wait_procs([*descendants, process], timeout=3)
        for child in [*descendants, process]:
            try:
                if child.is_running():
                    child.kill()
            except psutil.Error:
                pass
        job.update(status="stopped", finished_at=now(), detail="사용자가 중단했습니다. 정상 종료 전 새 가중치는 저장되지 않습니다.")
        atomic_json(job, RUNTIME / "job.json")
        return {"message": job["detail"]}


@app.post("/api/experts/select")
def select(req: Selection):
    with launch_lock:
        if job_state()["running"]:
            raise HTTPException(409, "실행을 마친 뒤 Expert 구성을 변경하세요.")
        from .expert_registry_native import ExpertRegistry
        try:
            ExpertRegistry().select(sorted(set(req.active)))
        except (ValueError, OSError) as exc:
            raise HTTPException(400, str(exc)) from exc
    return {"message": "Expert 선택을 저장했습니다."}


@app.post("/api/experts/register")
def register(req: Registration):
    with launch_lock:
        if job_state()["running"]:
            raise HTTPException(409, "실행을 마친 뒤 패키지를 등록하세요.")
        registry = read_json(ROOT / "configs/experts.json")
        if req.slot in registry.get("experts", {}):
            raise HTTPException(409, "이미 사용 중인 슬롯 이름입니다. 다른 이름으로 등록하세요.")
        from .expert_registry_native import ExpertRegistry
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


@app.get("/api/operations")
def operations():
    from .platform.operations_runtime import runtime
    return runtime.snapshot()


@app.post("/api/controls/{name}")
def operation_control(name:Literal["feed","paper","engine"],request:ControlRequest):
    from .platform.operations_runtime import runtime
    try:return {"controls":runtime.command(name,request.enabled)}
    except (ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc))


@app.post("/api/orders")
def paper_order(request:OrderRequest):
    from .platform.operations_runtime import runtime
    try:return runtime.manual_order(request.symbol,request.currency,request.action,request.quantity)
    except (ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc))


@app.get("/api/provider")
def provider():
    from .provider_credentials import public_status
    from .platform.operations_settings import settings
    return public_status(settings().state_dir)


@app.post("/api/provider/connect")
def connect_provider(request:CredentialRequest):
    from .provider_credentials import connect_credentials
    from .platform.operations_settings import settings
    from .platform.operations_runtime import runtime
    if runtime.controls['feed']:raise HTTPException(409,'기존 시세 수신을 중지한 뒤 공급원 인증을 변경하세요.')
    try:return connect_credentials(settings().state_dir,request.environment,request.app_key,request.secret,request.account)
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(400,str(exc))


@app.post("/api/provider/test")
def check_provider(request:CredentialRequest):
    from .provider_credentials import test_connection
    from .platform.operations_settings import settings
    try:return test_connection(settings().state_dir,"kiwoom",request.environment)
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(400,str(exc))


@app.post("/api/provider/public")
def public_feed():
    from .platform.operations_runtime import runtime
    if runtime.controls['feed']:raise HTTPException(409,'시세 수신을 중지한 뒤 공급원을 변경하세요.')
    from .provider_credentials import _write_settings,read_settings
    from .platform.operations_settings import settings
    root=settings().state_dir;value=read_settings(root);value['provider']='yahoo'
    _write_settings(root,value)
    return {"message":"기존 공개 시세 공급원을 선택했습니다."}


@app.post('/api/provider/disconnect')
def disconnect_provider():
    from .platform.operations_runtime import runtime
    runtime.command('feed',False)
    return {'message':'시세 연결 중지를 요청했습니다. 저장된 인증 정보는 유지합니다.'}


@app.get("/api/settings")
def operational_settings():
    from .platform.operations_settings import settings
    current=settings()
    return {"risk":vars(current.risk),"data":vars(current.data),"symbols":current.symbols,
            "expert_devices":current.resources.expert_devices,"sac_readonly":source_settings()}


@app.post("/api/settings")
def save_operational_settings(values:dict):
    from .platform.operations_settings import update
    from .platform.operations_runtime import runtime
    if set(values)-{"risk","data","symbols","expert_devices"}:raise HTTPException(400,"운영 설정만 변경할 수 있습니다. SAC 설정은 원본값을 사용합니다.")
    if runtime.controls['feed']:raise HTTPException(409,"시세 수신을 멈춘 뒤 운영 설정을 변경하세요.")
    value=update(values)
    if runtime.account:
        from .platform.operations_settings import settings
        current=settings();runtime.account.fee=current.risk.fee;runtime.account.slippage=current.risk.slippage
    if runtime.pool:
        runtime.pool.settings.resources.expert_devices=value.get('expert_devices',{})
    return {"settings":value}


@app.get("/api/library")
def library_state():
    from .platform.library_operations import library
    return library.snapshot()


@app.post("/api/library/{kind}")
def library_job(kind:str,payload:dict):
    if kind=='stop':return stop_library()
    from .platform.library_operations import library
    if job_state()["running"] and kind not in ("search","inspect"):
        raise HTTPException(409,"현재 SAC 작업 종료 후 모델 구성을 변경하세요.")
    try:return library.start(kind,payload)
    except (ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc))


@app.get("/api/models")
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


@app.post("/api/checkpoints/restore")
def restore_checkpoint(request:dict):
    if job_state()["running"]:raise HTTPException(409,"현재 SAC 작업 종료 후 복원하세요.")
    path=(RUNTIME/request.get("path","")).resolve()
    if not path.is_relative_to(RUNTIME.resolve()) or path.name!="sac.zip" or not path.is_file():
        raise HTTPException(400,"저장된 SAC 버전을 선택하세요.")
    identity=read_json(path.parent/"dataset.json")
    settings=source_settings()
    if identity.get("environment")!=settings["environment"] or identity.get("sac_example")!=settings["parameters"]:
        raise HTTPException(400,"현재 공식 SAC 환경·예제와 호환되지 않는 이전 정책입니다.")
    from .platform.operations_runtime import runtime
    runtime.check_policy(path.parent)
    atomic_json({"path":path.relative_to(RUNTIME).as_posix()},RUNTIME/"active-checkpoint.json")
    selection_path=ROOT/'runtime/operations/policies.json'
    if selection_path.is_file():
        selected=read_json(selection_path);selected[identity['currency']]=path.relative_to(RUNTIME).as_posix();atomic_json(selected,selection_path)
    return {"message":"기존 가중치 파일을 변경하지 않고 해당 SAC 버전을 선택했습니다."}


@app.get('/api/system/status')
def system_status():
    from .platform.system_operations import system,apply_state
    return {'apply':apply_state(),'system':system.snapshot()}


@app.post('/api/system/apply')
def apply_changes():
    from .platform.system_operations import start_apply
    return start_apply()


@app.get('/api/system/blockers')
def restart_blockers():
    from .platform.system_operations import busy
    return {'items':busy()}


@app.post('/api/system/prepare-restart')
def prepare_restart():
    from .platform.system_operations import busy,system
    with launch_lock:
        blockers=busy()
        if blockers:raise HTTPException(409,' · '.join(blockers))
        system.restarting=True
        from .platform.operations_runtime import runtime
        runtime.close()
    return {'ready':True}


@app.get('/api/system/check')
def system_check():
    from .platform.system_operations import check_system
    return check_system()


@app.post('/api/system/start')
def start_system(values:dict):
    from .platform.system_operations import system
    currencies=values.get('currencies',['USD','KRW'])
    if not currencies or not set(currencies)<= {'USD','KRW'}:raise HTTPException(400,'USD/KRW 운영 통화를 선택하세요.')
    try:return system.start(list(dict.fromkeys(currencies)))
    except ValueError as exc:raise HTTPException(409,str(exc))


@app.post('/api/system/stop')
def stop_system():
    from .platform.system_operations import system
    return system.stop()


def stop_library():
    from .platform.library_operations import library
    from .platform.operations_runtime import runtime
    library.cancelled.set();runtime.cancel_inference.set()
    return {'message':'모델 작업 중지를 요청했습니다. 진행 중 연산은 종료 상태를 확인하세요.'}


@app.post('/api/model/open-directory')
def open_model_directory():
    if not MODEL_DIR.is_dir():raise HTTPException(404,'실제 모델 폴더가 없습니다.')
    if os.name!='nt':raise HTTPException(400,'현재 폴더 열기는 Windows에서 제공합니다.')
    os.startfile(MODEL_DIR)
    return {'path':str(MODEL_DIR)}


@app.on_event("shutdown")
def close_operations():
    from .platform.operations_runtime import runtime
    runtime.close()
