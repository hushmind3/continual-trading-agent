"""Explicit input capabilities checked before a frozen asset enters the MoE."""
SUPPORTED_MARKET={'chronos','timesfm','kronos','exaone','fincast','timemoe','toto'}
SUPPORTED_STOCK={'adilbai','msft','a2c','ppo','sac'}


def input_contract(entry):
    stock=entry.get('stock_policy')
    if stock:
        kind=stock.get('kind')
        if kind not in SUPPORTED_STOCK:
            return dict(supported=False,reason='현재 입력 생성기가 지원하지 않는 주식 정책입니다.',pipeline='unsupported')
        return dict(supported=True,pipeline='stock',requires=['완료 일봉','기술 지표','USD 계좌'],
                    universe=list(stock['universe']),minimum_history=128)
    backend=entry.get('backend')
    if backend not in SUPPORTED_MARKET:
        return dict(supported=False,reason='이 모델의 원본 입력을 만드는 파이프라인이 등록돼 있지 않습니다.',pipeline='unsupported')
    daily=backend in ('chronos','timesfm')
    return dict(supported=True,pipeline=backend,requires=['완료 일봉','SPY 초과수익률'] if daily else ['완료 OHLCV'] if backend=='kronos' else ['완료 가격 시계열'],
                minimum_history=32,universe=None)


def descriptor(key,package,reference):
    entry=package['entry'];contract=input_contract(entry)
    types=sorted({str(v.dtype).removeprefix('torch.') for v in package.get('state_dict',{}).values() if v.is_floating_point()})
    precision=package.get('representation') or '/'.join({'float32':'FP32','float16':'FP16','bfloat16':'BF16'}.get(t,t) for t in types) or entry.get('dtype','native')
    return dict(id=key,name=entry.get('name',key),backend=entry.get('backend'),
                executor=package.get('executor','torch_native'),representation=precision,
                role='action' if entry.get('stock_policy') else 'market',
                parameters=entry.get('parameters'),feature_size=package['feature_size'],
                package=reference,input=contract,check=dict(status='untested' if contract['supported'] else 'unsupported',
                detail='실제 입력으로 추론 검사 전' if contract['supported'] else contract['reason']))
