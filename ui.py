"""Native Streamlit controls for official APIs and frozen Expert parts."""
from pathlib import Path
import sys,subprocess,os,json,zipfile
import streamlit as st
import psutil
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from stockrl.expert_registry_native import ExpertRegistry
from stockrl.framework import sac_example
from stockrl.state_io import read_json

st.set_page_config(page_title='FinRL-X · 공식 SAC',layout='wide')
st.title('FinRL-X · 공식 SAC')
st.caption('새 정책 · 공식 Actor/Critic/SAC/Adam/Replay · 동결 Expert 관측 연결')
_,parameters,timesteps=sac_example()
with st.expander('적용된 공식 설정과 구조',expanded=True):
    st.write('FinRL-X 원본 train_sac()를 호출합니다. 예제 설정을 변경하지 않습니다.')
    st.json(parameters)
    st.write('학습 환경: FinRL 원본 NumPy StockTradingEnv · 중앙 네트워크: SB3 기본 256/256 · 이전 중앙 가중치·optimizer·Replay 승계 없음')
left,right=st.columns(2)
with left:
    currency=st.selectbox('데이터 통화',['USD','KRW'])
    instruments=read_json(ROOT/'configs/instruments.json').get('instruments',[])
    markets=['KRX','KOSDAQ'] if currency=='KRW' else ['US','NASDAQ','NYSE','NYSEARCA','AMEX']
    names=sorted({i['symbol'] for i in instruments if i.get('market') in markets and i.get('asset_class') in ['equity','etf']})
    symbols=st.multiselect('학습 종목 — 선택하지 않으면 저장된 해당 시장 전체',names)
    st.caption('공식 환경의 행동 차원은 이번 종목 구성에 맞춰 정해집니다. 종목 구성을 바꾸면 새 정책으로 시작합니다.')
    st.write('원본 예제 실행 단계:',timesteps)
    root=ROOT/'runtime/official';root.mkdir(parents=True,exist_ok=True)
    pidfile=root/'training.pid';log=root/'training.log'
    running=False
    if pidfile.exists():
        try:
            process=psutil.Process(int(pidfile.read_text()));running='stockrl.official_cli' in ' '.join(process.cmdline()) and process.is_running()
        except (ValueError,psutil.Error):pass
    st.write('학습 프로세스 실행 중' if running else '학습 실행 대기')
    saved=list(root.rglob('*.zip'))
    if saved:
        latest=max(saved,key=lambda p:p.stat().st_mtime)
        try:
            with zipfile.ZipFile(latest) as package:state=json.loads(package.read('data'))
            st.write('마지막 저장된 정책:',state.get('num_timesteps',0),'개 경험 수집 /',state.get('_n_updates',0),'회 학습 업데이트')
            st.caption('저장 파일: '+latest.name+' · 현재 실행의 진행도는 아래 공식 진행 로그에서 확인합니다.')
        except (OSError,ValueError,KeyError,zipfile.BadZipFile):pass
    resume=st.checkbox('이번 공식 SAC 정책·Replay에서 이어 학습',disabled=not (root/'sac.zip').exists())
    train_clicked=st.button('공식 SAC 이어 학습' if resume else '공식 SAC 새 학습 실행',disabled=running)
    st.caption('원본 BacktestEngine은 투자 비중을 합계 100%로 정규화합니다. 환경의 현금 비중과 같은 평가가 아니며 학습에 사용한 기간의 재평가는 독립 검증이 아닙니다.')
    evaluate_clicked=st.button('FinRL-X 원본 백테스트',disabled=running or not (root/'sac.zip').exists())
    if train_clicked or evaluate_clicked:
        env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src');env['PYTHONUTF8']='1'
        with log.open('w',encoding='utf8') as output:
            command=[sys.executable,'-m','stockrl.official_cli','backtest' if evaluate_clicked else 'train','--currency',currency]
            if symbols:command.extend(['--symbols',*symbols])
            if resume and train_clicked:command.append('--resume')
            child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        pidfile.write_text(str(child.pid));st.rerun()
    if st.button('실행 로그 갱신'):st.rerun()
    if log.exists():st.code(log.read_text(encoding='utf8',errors='replace')[-10000:])
with right:
    exec((ROOT/'expert_ui.py').read_text(encoding='utf8'))
    with st.expander('Expert 실제 실행 결과',expanded=True):
        status=read_json(ROOT/'runtime/experts/status.json')
        if status:st.json(status)
        else:st.caption('현재 실행 결과가 없습니다. 학습을 실행하면 성공 여부·입력 부족 사유·GPU 측정값을 표시합니다.')
