"""Call original FinRL-X/FinRL/SB3 APIs, with only frozen Expert registration added."""
import argparse
from pathlib import Path
from .framework import ROOT,prices,train,backtest
from .expert_registry_native import ExpertRegistry


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['train','backtest','experts'])
    parser.add_argument('--currency',choices=['USD','KRW'],default='USD')
    parser.add_argument('--symbols',nargs='+')
    parser.add_argument('--resume',action='store_true',help='이번 공식 SAC 실행에서 생성한 정책과 Replay만 복원')
    args=parser.parse_args();registry=ExpertRegistry()
    if args.command=='experts':
        for key,item in registry.catalog()['experts'].items():print(key,item['name'],'active' if key in registry.catalog()['active'] else 'stored')
        return
    (ROOT/'runtime/official').mkdir(parents=True,exist_ok=True)
    frame=prices(args.currency,args.symbols)
    if frame.empty:raise ValueError('공식 DataStore에 해당 시장의 실제 가격 데이터가 없습니다.')
    if args.command=='backtest':
        result=backtest(frame,registry);print(result.to_metrics_dataframe().to_string())
        result.portfolio_values.to_csv(ROOT/'runtime/official/backtest.csv')
        # Persist official engine metrics for the HTTP/UI adapter.
        from .state_io import atomic_json
        import math
        metrics=result.to_metrics_dataframe()
        records={str(index):{str(key):float(value) if isinstance(value,(int,float)) and math.isfinite(value) else str(value) if not isinstance(value,(int,float)) else None for key,value in row.items()} for index,row in metrics.iterrows()}
        atomic_json({'currency':args.currency,'symbols':sorted(frame.symbol.unique()),
            'strategies':records},ROOT/'runtime/official/backtest_metrics.json')
        result.weights_history.to_csv(ROOT/'runtime/official/backtest_weights.csv')
        result.trades.to_csv(ROOT/'runtime/official/backtest_trades.csv')
        return
    model=train(frame,registry,args.resume)
    print('Saved official SAC:',ROOT/'runtime/official/sac.zip')


if __name__=='__main__':main()
