"""진단 · 로그 · 코드 적용 — existing API handlers."""
from __future__ import annotations
from api_context import private_api
from api_context import APIRouter
from api_context import DB
from api_context import FiniteJSONResponse
from api_context import HTTPException
from api_context import MODEL_DIR
from api_context import Path
from api_context import ROOT
from api_context import RUNTIME
from api_context import app
from api_context import apply_state
from api_context import busy
from api_context import check_system
from api_context import database_cache
from api_context import datetime
from api_context import json
from api_context import library_manager
from api_context import os
from api_context import policy_checkpoint
from api_context import policy_files
from api_context import read_json
from api_context import resource_monitor
from api_context import runtime
from api_context import sqlite3
from api_context import start_apply
from api_context import system
from api_context import timezone

router=APIRouter(default_response_class=FiniteJSONResponse)

def now():
    return datetime.now(timezone.utc).isoformat()


def file_info(path):
    return {"exists": path.is_file(), "bytes": path.stat().st_size if path.is_file() else 0,
            "modified": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if path.is_file() else None}


def database():
    if not DB.is_file():
        from stockrl.finrl.price_data.storage import PriceStore
        PriceStore(DB.parent)
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


def capabilities():
    return {
        "learning":{"status":"supported","reason":"FinRL DRLAgent · SB3 알고리즘 선택·학습·중단·동일 정책 이어 학습 · 기본 SAC","source":"stockrl.finrl.framework.train"},
        "expert_selection":{"status":"supported","reason":"Frozen Expert 등록·선택·같은 모델 정밀도 교체·해제","source":"stockrl.expert_registry_native.ExpertRegistry"},
        "paper_accounts":{"status":"supported","reason":"원본 PaperAccount의 KRW/USD 독립 잔고·보유·체결·손익 기능이 연결되어 있습니다.","source":"stockrl.trading.virtual_account_orders.paper_account.PaperAccount"},
        "live_feed":{"status":"supported","reason":"복구한 LiveMarketCollector와 Kiwoom BrokerStreams의 완료 시세를 DataStore·가상계좌에 전달합니다.","source":"stockrl.live_feed"},
        "kiwoom":{"status":"supported","reason":"기존 보안 저장소·인증·실시간 수신 모듈 연결. 실제 수신에는 유효한 인증이 필요합니다. 실제 주문은 전송하지 않습니다.","source":"stockrl.management.connection_settings.provider_credentials / platform.kiwoom_data"},
        "alpaca":{"status":"not_connected","reason":"Alpaca 연결·매매 도구는 플랫폼에서 제거했습니다.","source":None},
        "conversion":{"status":"supported","reason":"기존 정밀도 변환과 품질 비교·후보 선택 함수를 연결합니다. 변환은 새 파일로 저장됩니다.","source":"stockrl.platform.expert_conversion / expert_optimizer"},
        "discovery":{"status":"supported","reason":"기존 HF/GitHub 검색·가중치 호환 확인·다운로드·자동 등록 함수가 연결되어 있습니다.","source":"stockrl.platform.expert_discovery / expert_acquisition"},
        "checkpoint_restore":{"status":"supported","reason":"기존 SB3 파일을 변경하지 않고 선택하여 복원·이어 학습에 사용합니다. 이전 자체 정책 형식은 호환되지 않습니다.","source":"stockrl.finrl.framework.policy_files"},
        "settings_edit":{"status":"supported","reason":"시세·가상계좌·Expert 장치의 기존 운영 설정을 편집합니다. SAC 학습값은 변경하지 않습니다.","source":"stockrl.trading.operation_control.operations_settings"},
    }


@router.get("/api/health")
def health():
    return {"ok": True, "service": "project-platform", "project": str(ROOT.resolve()), "pid": os.getpid(),"deployment_id":os.environ.get('STOCKRL_APPLY_ID')}


def modules():
    from stockrl.platform.framework_operations import catalog
    return catalog()


def menu_catalog():
    from menu_registry import catalog
    return catalog(private_api.routes)


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
    from stockrl.finrl.policy_learning.handlers import algorithms
    from stockrl.extensions.moe.handlers import champions
    from stockrl.management.connection_settings.handlers import connections
    from stockrl.management.all_backend_features.handlers import framework_catalog
    from stockrl.management.all_backend_features.handlers import framework_providers
    from stockrl.extensions.moe.handlers import model_files
    from stockrl.management.connection_settings.handlers import operational_settings
    from stockrl.management.connection_settings.handlers import provider
    from urllib.parse import urlsplit,parse_qs
    parsed=urlsplit(path);query=parse_qs(parsed.query);key=parsed.path
    if parsed.scheme or parsed.netloc:raise ValueError('통합 상태 항목을 선택하세요.')
    currency=query.get('currency',[None])[0]
    if currency not in (None,'USD','KRW'):raise ValueError('USD/KRW 상태를 선택하세요.')
    config=ROOT/'configs';official=ROOT/'runtime/official'
    providers={
        'menu_catalog':(menu_catalog,lambda:()),
        'algorithms':(algorithms,lambda:()),
        'framework':(framework_catalog,None),
        'framework/providers':(framework_providers,None),
        'connections':(connections,None),
        'provider':(provider,None),
        'settings':(operational_settings,lambda:state_stamp(config/'local/operations.json')),
        'models':(model_files,lambda:state_stamp(config/'experts.json',*MODEL_DIR.rglob('*'))),
        'champions':(champions,lambda:state_stamp(*MODEL_DIR.glob('*_champion_*.pt'))),
        'logs':(logs,lambda:state_stamp(*(official/name for name in ('api.stderr.log','api.stdout.log','server.stderr.log','training.log')))),
    }
    if key not in providers:raise ValueError('등록되지 않은 통합 상태 항목입니다: '+key)
    loader,signature=providers[key];name='view:'+path
    data=system.state_value(name,loader,signature)
    return {'data':data,'error':system.state_errors.get(name,''),'updated_at':system.state_updates.get(name)}


from stockrl.expert_registry import catalog_read_scope

@router.get('/api/state')
@catalog_read_scope()
def state(views:str='[]',refresh_views:bool=False):
    from stockrl.finrl.policy_learning.handlers import checkpoints
    from stockrl.finrl.policy_learning.handlers import currency_models
    from stockrl.extensions.moe.handlers import expert_state
    from stockrl.finrl.policy_learning.handlers import model_state
    from stockrl.finrl.policy_learning.handlers import saved_replay
    from stockrl.finrl.policy_learning.handlers import source_settings
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
    def checkpoint_signature():
        files=[*RUNTIME.glob('*.zip'),*(RUNTIME/'policies').glob('*/*.zip'),*(RUNTIME/'champions').glob('*/*.zip'),*(RUNTIME/'archives').glob('*/*.zip')]
        champions=[]
        for file in files:
            try:champion=read_json(file.parent/'dataset.json').get('champion_file')
            except (OSError,ValueError):continue
            if champion:champions.append(Path(champion))
        return state_stamp(*files,*(file.parent/'dataset.json' for file in files),*champions)
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
        'models_by_currency':models,'checkpoints':revisions,'capabilities':system.state_value('capabilities',capabilities,()),
        'operations':operations_state,'library':library,'automation':automation,'resources':resources,'views':selected,
        'state_revision':system.state_revision,'module_errors':dict(system.state_errors),'module_updated_at':dict(system.state_updates),'resident_models':system.resident_models(),'imports':imports,
        'commands':system.commands(),'frontend_revision':system.state_value('frontend_revision',lambda:read_json(RUNTIME/'applied-sources.json').get('dist_sha256'),lambda:state_stamp(RUNTIME/'applied-sources.json'))}


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


@router.post("/api/stop")
def stop():
    try:return system.stop_job()
    except RuntimeError as exc:raise HTTPException(409,str(exc)) from exc


@router.post('/api/system/apply')
def apply_changes(request:dict):
    try:return start_apply(request.get('target','frontend'))
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc


@router.get('/api/system/blockers')
def restart_blockers():
    return {'items':busy()}


@router.post('/api/system/prepare-restart')
def prepare_restart():
    with system.job_lock:
        blockers=busy()
        if blockers:raise HTTPException(409,' · '.join(blockers))
        system.restarting=True
        runtime.close()
    return {'ready':True}


@router.get('/api/system/check')
def system_check():
    return check_system()


@app.on_event("shutdown")
def close_operations():
    runtime.close()
    system.close_models()

