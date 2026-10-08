"""Official Kiwoom SDK for OAuth/transport; existing normalized domestic bar parser."""
import asyncio
from datetime import datetime,timezone
import threading
import time
from zoneinfo import ZoneInfo
from kiwoom import KiwoomAuth,KiwoomClient,KiwoomWebSocketClient
from kiwoom.core.secrets import StaticSecretProvider
from kiwoom.core.token_store import MemoryTokenStore
from ..kiwoom_stream import KiwoomRealtimeStream,_number
from ..provider_credentials import get_credentials,read_settings
from ..state_io import atomic_json,read_json


class DomesticQuotes(KiwoomRealtimeStream):
    def _flush(self,symbol,bar):
        if not hasattr(self,'first_buckets'):self.first_buckets={}
        if symbol not in self.first_buckets:
            self.first_buckets[symbol]=bar['_bucket']
            return
        super()._flush(symbol,bar)


class USQuotes(DomesticQuotes):
    def _on_message(self,message):
        if message.get('trnm')!='REAL':return
        for event in message.get('data',[]):
            if event.get('type')!='FE':continue
            item=event.get('item',{})
            code=str(item.get('jmcode','') if isinstance(item,dict) else item).upper()
            if code not in self.by_code and code[:2] in ('NA','ND','NY'):
                code=code[2:]
            instrument=self.by_code.get(code); values=event.get('values',{})
            if not instrument:continue
            price=_number(values.get('10'),absolute=True)
            clock=str(values.get('51020') or '').zfill(6)
            day=str(values.get('22') or datetime.now(ZoneInfo('America/New_York')).strftime('%Y%m%d'))
            if not price or len(day)!=8 or len(clock)!=6 or not (day+clock).isdigit():continue
            local=datetime.strptime(day+clock,'%Y%m%d%H%M%S').replace(tzinfo=ZoneInfo('America/New_York'))
            bucket=local.astimezone(timezone.utc).replace(second=0,microsecond=0)
            symbol=instrument['symbol']; old=self.bars.get(symbol)
            if old and bucket<old['_bucket']:continue
            if old and bucket>old['_bucket']:
                self._flush(symbol,old);old=None
            volume=abs(_number(values.get('15')) or 0)
            if old is None:
                self.bars[symbol]={'_bucket':bucket,'date':bucket.isoformat(),'symbol':symbol,
                    'market':instrument.get('market','US'),'asset_class':instrument.get('asset_class','equity'),
                    'open':price,'high':price,'low':price,'close':price,'volume':volume,
                    'bid':_number(values.get('28'),absolute=True),'ask':_number(values.get('27'),absolute=True),'trade_count':1}
            else:
                old.update(high=max(old['high'],price),low=min(old['low'],price),close=price,
                           volume=old['volume']+volume,trade_count=old['trade_count']+1)
            self._set(last_message_utc=datetime.now(timezone.utc).isoformat(),last_error=None)


class BrokerStreams:
    def __init__(self,collector):
        self.collector=collector;self.stop=collector.broker_stop;self.thread=None;self.states={}
        cfg=read_settings(collector.runtime_dir);self.environment=cfg['environment']
        credentials=get_credentials(collector.runtime_dir,self.environment)
        provider=StaticSecretProvider(credentials['app_key'],credentials['secret'])
        self.auth=KiwoomAuth('real' if self.environment=='real' else 'demo',provider,MemoryTokenStore(),timeout_seconds=10)
        self.domestic=list(collector.broker_instruments)
        self.collector.latest_quotes={}
        self.us=[i for i in collector.instruments if i.get('market') in ('US','NASDAQ','NYSE','AMEX')
                 and i.get('asset_class') in ('equity','etf') and self.environment=='real']

    def status(self,region,state):
        self.states[region]=state
        merged={'connected':any(s.get('connected') for s in self.states.values()),
                'last_error':'; '.join(s.get('last_error') or '' for s in self.states.values()).strip('; '),
                'last_message_utc':max((s.get('last_message_utc') or '' for s in self.states.values()),default='') or None}
        for region,item in self.states.items():
            merged[f'{region}_connected']=bool(item.get('connected'))
        self.collector.broker_status.update(merged)

    def resolve_us(self):
        path=self.collector.runtime_dir/'kiwoom_us_exchanges.json'; cache=read_json(path)
        rest=KiwoomClient(self.auth,timeout_seconds=10);items=[]
        try:
            for instrument in self.us:
                if self.stop.is_set():break
                symbol=instrument.get('provider_symbol',instrument['symbol'])
                entry=cache.get(symbol)
                if entry is None:
                    try:
                        response=rest.request(api_id='usa10098',path='/api/us/stkinfo',body={'stk_cd':symbol}).body
                        entry=next((r for r in response.get('list',[]) if r.get('stex_tp') in ('ND','NY','NA')),None)
                        if entry:cache[symbol]=entry
                    except Exception as exc:
                        self.status('us',{'connected':False,'last_error':f'{symbol} 거래소 조회: {exc}'})
                    time.sleep(.25)
                if entry:items.append({'jmcode':entry.get('stk_cd',symbol),'stex_tp':entry['stex_tp']})
            atomic_json(cache,path)
        finally:rest.session.close()
        return items

    async def stream(self,region,parser,items,path,kind):
        retries=2
        while not self.stop.is_set():
            client=KiwoomWebSocketClient(self.auth,timeout_seconds=10)
            try:
                await client.connect(api_url=path)
                groups=[items[i:i+50] for i in range(0,len(items),50)]
                for i,group in enumerate(groups,1):
                    await client.send({'trnm':'REG','grp_no':str(i),'refresh':'1','data':[{'item':group,'type':[kind]}]})
                acknowledged=0
                while not self.stop.is_set():
                    try:message=await asyncio.wait_for(client.recv(),timeout=1)
                    except asyncio.TimeoutError:message={}
                    if message.get('trnm')=='REG':
                        if int(message.get('return_code',0))!=0:raise RuntimeError(message.get('return_msg','구독 실패'))
                        acknowledged+=1
                        if acknowledged>=len(groups):parser._set(connected=True,last_error=None)
                    else:
                        parser._on_message(message)
                        for event in message.get('data',[]) if message.get('trnm')=='REAL' else []:
                            item=event.get('item',{})
                            code=str(item.get('jmcode','') if isinstance(item,dict) else item).split('.')[0]
                            instrument=parser.by_code.get(code)
                            values=event.get('values',{})
                            if not instrument:continue
                            price=_number(values.get('10'),absolute=True)
                            clock=str(values.get('51020') if region=='us' else values.get('20') or '').zfill(6)
                            zone=ZoneInfo('America/New_York' if region=='us' else 'Asia/Seoul')
                            day=str(values.get('22') or datetime.now(zone).strftime('%Y%m%d')) if region=='us' else datetime.now(zone).strftime('%Y%m%d')
                            if price and len(clock)==6 and (day+clock).isdigit():
                                moment=datetime.strptime(day+clock,'%Y%m%d%H%M%S').replace(tzinfo=zone).astimezone(timezone.utc)
                                self.collector.latest_quotes[instrument['symbol']]={'date':moment.isoformat(),'price':price,'provider':'kiwoom'}
                    now=datetime.now(timezone.utc).replace(second=0,microsecond=0)
                    for symbol,bar in list(parser.bars.items()):
                        if bar['_bucket'].astimezone(timezone.utc)<now:
                            parser._flush(symbol,bar);parser.bars.pop(symbol,None)
                retries=2
            except Exception as exc:
                parser._set(connected=False,last_error=f'{type(exc).__name__}: {exc}')
                for _ in range(retries):
                    if self.stop.is_set():break
                    await asyncio.sleep(1)
                retries=min(60,retries*2)
            finally:await client.close()
        parser._set(connected=False)

    async def run_async(self):
        await asyncio.to_thread(self.auth.get_access_token)
        tasks=[]
        if self.domestic:
            parser=DomesticQuotes(self.collector.runtime_dir,self.domestic,self.stop,self.collector.broker_rows,
                                        lambda state:self.status('kr',state))
            tasks.append(asyncio.create_task(self.stream('kr',parser,parser.subscription_codes,'/api/dostk/websocket','0B')))
        if self.us:
            items=await asyncio.to_thread(self.resolve_us)
            if items:
                registered={i['jmcode'] for i in items}
                instruments=[i for i in self.us if i.get('provider_symbol',i['symbol']) in registered]
                self.collector.broker_symbols.update(i['symbol'] for i in instruments)
                parser=USQuotes(self.collector.runtime_dir,instruments,self.stop,self.collector.broker_rows,
                                lambda state:self.status('us',state))
                tasks.append(asyncio.create_task(self.stream('us',parser,items,'/api/us/websocket','FE')))
        if tasks:await asyncio.gather(*tasks)

    def start(self):
        def target():
            try:asyncio.run(self.run_async())
            except Exception as exc:self.collector.broker_status.update(connected=False,last_error=f'{type(exc).__name__}: {exc}')
        self.thread=threading.Thread(target=target,name='kiwoom-sdk-streams',daemon=True);self.thread.start()

    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=10)
