"""Operations API and the one authoritative built React application."""
from __future__ import annotations

from contextlib import asynccontextmanager
import math
import threading
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse
from pydantic import BaseModel
from ..paths import PROJECT_ROOT,EXPERT_ASSETS_DIR
from ..state_io import atomic_json,read_json
from ..provider_credentials import public_status,connect_credentials,test_connection,clear_credentials
from .config import CONFIG_PATH,Settings
from .runtime import Runtime


class Toggle(BaseModel):
    enabled: bool


def clean(value):
    if isinstance(value,float) and not math.isfinite(value):
        return None
    if isinstance(value,dict):
        return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):
        return [clean(v) for v in value]
    return value


class SafeJSONResponse(JSONResponse):
    def render(self,content):
        return super().render(clean(content))


def summary(state,names=None,journal=None):
    if not state:
        return None
    result=dict(state); result["books"]={}
    result['fills']=[]
    for currency,book in state["books"].items():
        positions=[]
        for symbol,p in book.get("positions",{}).items():
            mark=book.get("marks",{}).get(symbol,p["average_cost"])
            positions.append(dict(symbol=symbol,name=(names or {}).get(symbol,symbol),**p,mark=mark,value=p["quantity"]*mark,
                                  pnl=p["quantity"]*(mark-p["average_cost"])))
        equity=book["cash"]+sum(p["value"] for p in positions)
        result["books"][currency]={**book,"positions":positions,"equity":equity,"pnl":equity-book["initial_cash"],
                                  "return_rate":equity/book["initial_cash"]-1}
        if journal:
            recorded=journal.fill_count(currency)
            result['books'][currency].update(recorded_fills=recorded,missing_fills=max(0,book['trade_count']-recorded))
    return result


def make_app(runtime=None,config=CONFIG_PATH):
    @asynccontextmanager
    async def lifespan(app):
        app.state.runtime=runtime or Runtime(config)
        yield
        if runtime is None:
            app.state.runtime.shutdown()

    app=FastAPI(title="FinRL-X MoE Operations",lifespan=lifespan,docs_url=None,redoc_url=None,default_response_class=SafeJSONResponse)
    cache={"reader":None,"signature":None,"rows":{},"history":{}}; cache_lock=threading.RLock()

    def rt(request):
        return request.app.state.runtime

    @app.middleware("http")
    async def no_cache(request,call_next):
        response=await call_next(request); response.headers["Cache-Control"]="no-store"
        return response

    @app.get("/api/health")
    def health():
        return {"service":"stockrl","port":8766,"architecture":"finrlx-unified-gpu-moe-v1","project":str(PROJECT_ROOT)}

    @app.get("/api/state")
    def state(request:Request):
        runtime=rt(request);value=runtime.snapshot()
        names={i['symbol']:i.get('name',i['symbol']) for i in read_json(runtime.input_config).get('instruments',[])}
        value["account"]=summary(value["account"],names,runtime.journal)
        value["equity_history"]={c:rt(request).journal.history(c) for c in ("USD","KRW")}
        return value

    @app.get('/api/fills')
    def fill_records(request:Request,currency:str='USD',offset:int=0,limit:int=50,before:int|None=None):
        if currency not in ('KRW','USD') or offset<0 or not 1<=limit<=200:
            raise HTTPException(400,'통화와 조회 범위를 확인하세요.')
        runtime=rt(request);account=runtime.journal.get_state('account') or {}
        cumulative=account.get('books',{}).get(currency,{}).get('trade_count',0)
        recorded=runtime.journal.fill_count(currency)
        return dict(currency=currency,fills=runtime.journal.fills(currency,offset,limit,before),recorded=recorded,
                    cumulative=cumulative,missing=max(0,cumulative-recorded),offset=offset,limit=limit)

    @app.post("/api/controls/{name}")
    def command(name:str,toggle:Toggle,request:Request):
        try:
            return rt(request).command(name,toggle.enabled)
        except ValueError as exc:
            raise HTTPException(409,str(exc)) from exc

    @app.post("/api/events/read")
    def read_events(payload:dict,request:Request):
        rt(request).journal.read_events(payload.get('through')); return {"ok":True}

    @app.get("/api/markets")
    def markets(request:Request):
        from ..market_reader import IncrementalMarketCSV
        runtime=rt(request); config=read_json(runtime.input_config)
        rows={}; recent={}
        with cache_lock:
            path=runtime.root/"live"/"market.csv"
            if path.exists():
                if cache["reader"] is None:
                    cache["reader"]=IncrementalMarketCSV(path,retain_timestamps=128)
                frame,signature=cache["reader"].refresh()
                if frame is not None and len(frame) and signature!=cache['signature']:
                    cache["reader"].processed_through=frame.date.max()
                    for symbol,group in frame.groupby("symbol"):
                        last=group.tail(2).to_dict("records"); rows[symbol]=last[-1]
                        recent[symbol]=[{"time":str(p["date"]),"close":float(p["close"])} for p in group.tail(32).to_dict("records")]
                    cache.update(signature=signature,rows=rows,history=recent)
                rows=cache['rows'];recent=cache['history']
        decisions={d["symbol"]:d for d in runtime.journal.get_state("decisions") or []}
        ticks=read_json(runtime.root/'live'/'quotes.json')
        return {"instruments":[{**item,"quote":rows.get(item["symbol"]),"decision":decisions.get(item["symbol"]),
                                "history":recent.get(item["symbol"],[]),'latest_tick':ticks.get(item['symbol'])} for item in config.get("instruments",[])],
                "source":str(runtime.input_config)}

    @app.get("/api/experts")
    def experts(request:Request):
        runtime=rt(request); snapshot=runtime.snapshot(); values=snapshot["experts"]
        if not values:
            catalog=read_json(runtime.root/"expert_catalog.json") or read_json(EXPERT_ASSETS_DIR/"registry.template.json")
            values=catalog.get("experts",[])
        return {"experts":values,"selected":runtime.settings.enabled_experts,"model":runtime.settings.expert_checkpoint}

    @app.get('/api/library')
    def library(request:Request):
        return rt(request).library.snapshot()

    @app.post('/api/library/{kind}')
    def library_operation(kind:str,payload:dict,request:Request):
        try:return rt(request).library.start(kind,payload)
        except ValueError as exc:raise HTTPException(409,str(exc)) from exc

    @app.get("/api/experts/{key}")
    def expert(key:str,request:Request):
        runtime=rt(request);packets=runtime.journal.evidence().get(key)
        item=runtime.library.snapshot()['catalog'].get('experts',{}).get(key,{})
        sample=item.get('check',{}).get('sample_output')
        return {"id":key,"output":packets or sample,'origin':'운영 출력' if packets else '추가 전 검사 출력' if sample else None}

    @app.post("/api/settings")
    def save_settings(settings:Settings,request:Request):
        runtime=rt(request)
        if runtime.library.active:raise HTTPException(409,'Expert 작업이 완료된 뒤 운영 설정을 변경하세요.')
        library=read_json(runtime.root/'expert-library.json')
        if library and settings.enabled_experts!=library.get('active',[]):
            raise HTTPException(409,'Expert 선택은 MoE 슬롯 관리에서 적용하세요. 추론 검사와 체크포인트를 함께 처리합니다.')
        if runtime.controls["engine"] or any(runtime.process(k) for k in ("agent","learner","experts")):
            raise HTTPException(409,"MoE를 정지한 뒤 설정을 적용하세요.")
        if settings.state_dir!=runtime.root:
            raise HTTPException(400,"운영 중인 상태 저장 위치는 변경할 수 없습니다.")
        atomic_json(settings.model_dump(),runtime.config)
        runtime.settings=settings
        from .data_universe import prepare
        runtime.input_config=prepare(settings)
        return {"ok":True,"settings":settings.model_dump()}

    @app.post("/api/policies/rollback")
    def rollback(payload:dict,request:Request):
        runtime=rt(request)
        if runtime.controls["engine"] or runtime.process("learner") or runtime.process("agent"):
            raise HTTPException(409,"MoE와 학습을 정지한 뒤 복원하세요.")
        try:
            result=runtime.checkpoints.rollback(str(payload.get("file","")))
            saved,_=runtime.checkpoints.load(recover=False)
            library=read_json(runtime.root/'expert-library.json')
            if library:
                active=saved['model_spec'].get('active_experts',saved['expert_ids'])
                library.update(active=active,selection_revision=library.get('selection_revision',0)+1)
                atomic_json(library,runtime.root/'expert-library.json')
                runtime.settings.enabled_experts=active;atomic_json(runtime.settings.model_dump(),runtime.config)
            with runtime.journal.transaction():
                runtime.journal.db.execute('UPDATE transitions SET learned=-1 WHERE learned IS NULL')
                runtime.journal.db.execute('DELETE FROM pending')
                account=runtime.journal.get_state('account')
                if account:account['pending']={};runtime.journal.set_state('account',account)
            return result
        except ValueError as exc:
            raise HTTPException(400,str(exc)) from exc

    @app.get("/api/provider")
    def provider(request:Request):
        return public_status(rt(request).root)

    @app.post("/api/provider/connect")
    def connect(payload:dict,request:Request):
        try:
            return connect_credentials(rt(request).root,str(payload.get("environment","real")),
                str(payload.get("app_key","")),str(payload.get("secret","")),str(payload.get("account","")))
        except (ValueError,RuntimeError) as exc:
            raise HTTPException(400,str(exc)) from exc

    @app.post("/api/provider/test")
    def test_provider(request:Request):
        try:
            return test_connection(rt(request).root)
        except (ValueError,RuntimeError) as exc:
            raise HTTPException(400,str(exc)) from exc

    @app.post("/api/provider/clear")
    def clear_provider(request:Request):
        return clear_credentials(rt(request).root,"kiwoom")

    @app.post('/api/model/open-directory')
    def open_model_directory(request:Request):
        import os
        path=rt(request).settings.resolve(rt(request).settings.expert_checkpoint).parent
        if not path.is_dir():
            raise HTTPException(404,'모델 폴더가 없습니다.')
        os.startfile(path)
        return {'ok':True}

    @app.post('/api/evaluation')
    def evaluate(payload:dict,request:Request):
        import pandas as pd
        from .weights import evaluate_recorded_weights
        runtime=rt(request);currency=str(payload.get('currency','USD'))
        if currency not in ('USD','KRW'):raise HTTPException(400,'통화를 선택하세요.')
        records=runtime.journal.weights(currency)
        if len(records)<4:raise HTTPException(409,'동일 통화의 실제 비중 기록이 4개 이상 필요합니다.')
        with cache_lock:
            from ..market_reader import IncrementalMarketCSV
            reader=IncrementalMarketCSV(runtime.root/'live'/'market.csv')
            frame,_=reader.refresh()
        weights=pd.DataFrame([w for _,w in records],index=pd.to_datetime([t for t,_ in records]))
        frame['date']=pd.to_datetime(frame.date,utc=True).dt.tz_localize(None)
        prices=frame.pivot_table(index='date',columns='symbol',values='close').ffill()
        columns=[s for s in weights.columns if s in prices.columns]
        prices=prices.loc[prices.index>=weights.index.min(),columns].dropna(how='all').ffill().dropna()
        if prices.empty:raise HTTPException(409,'기록된 비중과 가격의 평가 구간이 겹치지 않습니다.')
        account=summary(runtime.journal.get_state('account'))
        result=evaluate_recorded_weights(prices,weights[columns],runtime.settings.risk.fee+runtime.settings.risk.slippage,
                                        account['books'][currency]['initial_cash'] if account else 10000)
        return {'currency':currency,**result}

    @app.get("/assets/{path:path}")
    def asset(path:str):
        root=(PROJECT_ROOT/"frontend"/"dist"/"assets").resolve(); file=(root/path).resolve()
        if not file.is_relative_to(root) or not file.is_file():
            raise HTTPException(404)
        return FileResponse(file)

    @app.get("/")
    def index():
        file=PROJECT_ROOT/"frontend"/"dist"/"index.html"
        if not file.exists():
            raise HTTPException(503,"frontend에서 npm run build를 실행하세요.")
        return FileResponse(file)

    return app


def serve(host="127.0.0.1",port=8766,open_browser=True,config=CONFIG_PATH):
    import uvicorn
    if open_browser:
        import webbrowser
        threading.Timer(1,lambda:webbrowser.open(f"http://127.0.0.1:{port}/")).start()
    uvicorn.run(make_app(config=config),host=host,port=port,log_level="warning")
