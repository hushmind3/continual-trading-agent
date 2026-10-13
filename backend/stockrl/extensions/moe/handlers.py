"""MoE — existing API handlers."""
from __future__ import annotations
from stockrl.api_context import APIRouter, BaseModel, ExpertRegistry, Field, FiniteJSONResponse, HTTPException, Literal, MODEL_DIR, ROOT, RUNTIME, champion_structure_environment, library_manager, lru_cache, os, re, read_json, runtime, system

router=APIRouter(default_response_class=FiniteJSONResponse)

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


@lru_cache(maxsize=256)
def expert_descriptor(key,file,checksum,size,modified):
    from stockrl.platform.expert_packages import load_package
    from stockrl.platform.expert_contracts import descriptor
    reference={"file":file,"sha256":checksum,"bytes":size}
    return descriptor(key,load_package(MODEL_DIR/"expert_registry.json",reference),reference)


def expert_state():
    from stockrl.management.diagnostics.handlers import file_info
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
                    from stockrl.platform.gguf_format import stored_precision
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


def champions():
    from stockrl.platform.sac_champion import list_champions
    return {"items":list_champions()}


@router.post("/api/champions/create")
def champion_create(request:ChampionRequest):
    from stockrl.management.diagnostics.handlers import database
    if system.job_state()["running"]:raise HTTPException(409,"현재 학습·수집이 끝난 뒤 생성하세요.")
    from stockrl.trading.control.operations_settings import settings
    recent=read_json(RUNTIME/"job.json")
    if recent.get('command')!='train':recent={}
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
    from stockrl.platform.sac_champion import create
    from stockrl.finrl.framework import champion_structure_environment
    env=None
    try:
        env=champion_structure_environment(request.currency,request.symbols,ExpertRegistry(),request.experts)
        result=create(request.currency,request.symbols,request.experts,env,algorithm=request.algorithm)
        return result
    except HTTPException:raise
    except (ValueError,RuntimeError,OSError,KeyError,MemoryError,FileExistsError) as exc:raise HTTPException(400,str(exc)) from exc
    finally:
        if env is not None:env.close()


@router.post("/api/experts/select")
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


@router.post("/api/experts/register")
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


@router.post("/api/library/{kind}")
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


def stop_library():
    library_manager.cancelled.set();runtime.cancel_inference.set()
    return {'message':'모델 작업 중지를 요청했습니다. 진행 중 연산은 종료 상태를 확인하세요.'}


@router.post('/api/model/open-directory')
def open_model_directory():
    if not MODEL_DIR.is_dir():raise HTTPException(404,'실제 모델 폴더가 없습니다.')
    if os.name!='nt':raise HTTPException(400,'현재 폴더 열기는 Windows에서 제공합니다.')
    os.startfile(MODEL_DIR)
    return {'path':str(MODEL_DIR)}

