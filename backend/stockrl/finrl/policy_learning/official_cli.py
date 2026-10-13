"""Run FinRL/SB3 training with optional frozen Expert integration."""
import argparse
from pathlib import Path
from stockrl import ROOT
from stockrl.finrl.price_data.operations import prices
from stockrl.finrl.framework import train
from stockrl.expert_registry_native import ExpertRegistry


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['train','experts'])
    parser.add_argument('--currency',choices=['USD','KRW'],default='USD')
    parser.add_argument('--symbols',nargs='+')
    parser.add_argument('--resume',action='store_true',help='이번 공식 SAC 실행에서 생성한 정책과 Replay만 복원')
    parser.add_argument('--algorithm',default='sac',help='설치된 FinRL MODELS의 알고리즘')
    parser.add_argument('--total-timesteps',type=int)
    parser.add_argument('--output',type=Path,help='기존 정책과 분리할 신규 SAC 결과 경로')
    parser.add_argument('--checkpoint',type=Path,help='이어 학습할 기존 정책 ZIP 경로')
    parser.add_argument('--champion-path',type=Path,help='통합 SAC Champion PT')
    parser.add_argument('--champion-output',type=Path,help='학습 결과로 발행할 새 Champion PT')
    args=parser.parse_args();registry=ExpertRegistry();champion=None
    try:
        if args.champion_path and args.command=='train':
            from stockrl.platform.sac_champion import load_spec
            champion=load_spec(args.champion_path)
            registry=ExpertRegistry(champion=champion,source_checkpoint=args.checkpoint)
        if args.command=='experts':
            for key,item in registry.catalog()['experts'].items():print(key,item['name'],'active' if key in registry.catalog()['active'] else 'stored')
            return
        (ROOT/'runtime/official').mkdir(parents=True,exist_ok=True)
        frame=prices(args.currency,args.symbols)
        if frame.empty:raise ValueError('공식 DataStore에 해당 시장의 실제 가격 데이터가 없습니다.')
        model=train(frame,registry,args.resume,args.output,args.champion_path,args.champion_output,args.algorithm,args.total_timesteps,champion=champion)
        print('Saved FinRL policy:',(args.output or ROOT/'runtime/official')/(args.algorithm+'.zip'))

    finally:
        registry.close(cleanup=True)
        from stockrl.platform.system_operations import system
        system.close_models()


if __name__=='__main__':main()
