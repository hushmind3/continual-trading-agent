"""Process liveness is separate from observed work and source-data freshness."""
from collections import deque
from datetime import datetime,timezone
import threading


def timestamp(value):
    if isinstance(value,(float,int)):return float(value)
    if not value:return None
    try:
        parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return parsed.replace(tzinfo=timezone.utc).timestamp() if parsed.tzinfo is None else parsed.timestamp()
    except ValueError:return None


class ProgressTracker:
    def __init__(self):self.history={};self.lock=threading.Lock()

    def snapshot(self,state):
        now=state['time'];workers=state['workers'];experts=[e for e in state['experts'] if e.get('enabled') is not False]
        counts={
            'feed':{'new_bars':workers['feed'].get('new_rows_total'), 'polls':workers['feed'].get('poll_cycles_total')},
            'experts':{'inferences':sum(e.get('inference_count',0) or 0 for e in experts),'new_inputs':sum(e.get('new_input_count',0) or 0 for e in experts)},
            'agent':{'decisions':workers['agent'].get('decision_batches_total'),'market_batches':workers['agent'].get('market_batches_total')},
            'learner':{'updates':workers['learner'].get('optimizer_steps')},
        }
        last={
            'feed':timestamp(workers['feed'].get('last_new_bar_at')),
            'experts':max((e.get('last_completed_at',0) or 0 for e in experts),default=0) or None,
            'agent':timestamp(workers['agent'].get('last_decision_at')),
            'learner':timestamp(state.get('last_learning',{}).get('time')),
        }
        result={}
        with self.lock:
            for role,worker in workers.items():
                identity=(worker.get('pid'),worker.get('created_at'),tuple(e['id'] for e in experts) if role=='experts' else None)
                previous=self.history.get(role)
                points=previous[1] if previous and previous[0]==identity else deque(maxlen=180)
                values=counts[role]
                if points and any(v is not None and points[-1][1].get(k) is not None and v<points[-1][1][k] for k,v in values.items()):points.clear()
                while points and points[0][0]<now-60:points.popleft()
                base=points[0] if points else (now,values)
                changes={k:max(0,v-base[1][k]) if v is not None and base[1].get(k) is not None else None for k,v in values.items()}
                points.append((now,values.copy()));self.history[role]=(identity,points)
                observed=max(0,now-base[0]);heartbeat=timestamp(worker.get('heartbeat'))
                primary={'feed':'new_bars','experts':'inferences','agent':'decisions','learner':'updates'}[role]
                advanced=(changes.get(primary) or 0)>0
                if worker.get('error'):code,label='error','오류'
                elif not worker.get('alive'):code,label='stopped','서비스 정지'
                elif role=='learner' and worker.get('requested') is False and state['controls'].get('engine'):code,label='paused','학습 정지'
                elif worker.get('requested') is False:code,label='stopping','정지 중'
                elif heartbeat and now-heartbeat>max(30,state['settings']['resources']['inference_timeout_seconds']):code,label='unresponsive','응답 지연 · 진행 확인 필요'
                elif advanced:code,label='progress','실제 처리 증가'
                elif role=='learner':code,label='waiting',state['training']['label']
                elif role=='agent' and worker.get('message'):code,label='waiting','새 판단 대기'
                elif role=='feed' and observed>=10:code,label='waiting','새 저장 봉 대기'
                elif role=='experts' and observed>=10:code,label='waiting','완료된 분석 증가 없음'
                else:code,label='observing','변화 관찰 중'
                detail=worker.get('error') or (state['training']['detail'] if role=='learner' else worker.get('message'))
                if role=='feed' and not advanced:detail='수집기 응답과 별개로 새로 저장한 완료 봉의 증가를 확인합니다. 중복 조회는 진행으로 세지 않습니다.'
                if role=='experts':detail='분석 횟수와 새 입력 횟수를 구분합니다. 같은 시세의 재분석만 증가해도 새 판단·학습이 생긴다는 뜻은 아닙니다.'
                result[role]=dict(code=code,label=label,service_alive=bool(worker.get('alive')),heartbeat_at=heartbeat,last_completed_at=last[role],
                    source_as_of=worker.get('source_as_of') if role=='feed' else max((e.get('latest_input_as_of') or e.get('last_as_of') or '' for e in experts),default='') if role=='experts' else worker.get('market_cursor') if role=='agent' else None,
                    counters=values,changes=changes,observed_seconds=min(60,int(observed)),window_seconds=60,detail=detail)
        return result
