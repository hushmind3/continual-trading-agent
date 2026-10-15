"""Drive original Hermes GoalManager/LoopManager through the existing worker."""
import time
from dataclasses import asdict

def snapshot(session_id,recover=False):
    from hermes_cli.goals import GoalManager
    from hermes_cli.loops import LoopManager
    goal,loop=GoalManager(session_id),LoopManager(session_id)
    if recover:
        for manager in (goal,loop):
            if manager.is_active():manager.pause(reason='실행 연결이 종료되었습니다. 재개할 수 있습니다.')
    return {'goal':asdict(goal.state) if goal.state else None,'loop':asdict(loop.state) if loop.state else None}

def run(worker,agent,cfg,session_id,prompt,history,request):
    mode=request.get('mode','chat')
    if mode=='chat':return agent.run_conversation(prompt,conversation_history=history,task_id=session_id)
    if mode not in ('goal','loop'):raise ValueError('지원하지 않는 실행 방식입니다.')
    from hermes_cli.goals import GoalManager,goal_kick_prompt
    from hermes_cli.loops import LoopManager
    native=worker.native_config()
    native.setdefault('auxiliary',{})['goal_judge']={'provider':'custom','model':cfg['model'],
        'base_url':cfg['base_url'],'api_key':cfg.get('api_key') or 'local'}
    worker.write_config(native)
    manager=GoalManager(session_id) if mode=='goal' else LoopManager(session_id)
    other=LoopManager(session_id) if mode=='goal' else GoalManager(session_id)
    if other.is_active():other.pause(reason='실행 방식 변경')
    if request.get('resume'):
        if not manager.state:raise ValueError('재개할 작업이 없습니다.')
        manager.resume()
    elif mode=='goal':manager.set(prompt,max_turns=max(1,min(1000,int(request.get('max_turns') or 20))))
    else:
        interval=request.get('interval_seconds')
        if interval is not None and not 1<=int(interval)<=31536000:raise ValueError('반복 간격이 올바르지 않습니다.')
        manager.set(prompt,interval_seconds=int(interval) if interval is not None else None,
            times=max(0,min(100000,int(request.get('times',5)))),until=str(request.get('until') or ''))
    def publish():
        state=asdict(manager.state) if manager.state else {}
        with worker.lock:worker.job['autonomy']={**state,'mode':mode,'cadence':state.get('mode')}
    current=goal_kick_prompt(manager.state.goal,prompt) if mode=='goal' else None
    result={}
    try:
        while manager.is_active() and not worker.stopping:
            publish()
            if mode=='goal' and manager.is_waiting():
                time.sleep(.25)
                continue
            if mode=='loop':
                current=manager.fire_tick()
                if current is None:
                    time.sleep(.25)
                    continue
            worker.event('autonomy_turn',{'mode':mode,'state':asdict(manager.state)})
            result=agent.run_conversation(current,conversation_history=history,task_id=session_id)
            if result.get('error'):raise RuntimeError(str(result['error']))
            if worker.stopping:break
            response=result.get('final_response') or ''
            if mode=='goal':
                decision=manager.evaluate_after_turn(response)
                current=decision.get('continuation_prompt') or manager.next_continuation_prompt()
            else:decision=manager.complete_tick(response)
            worker.event('autonomy_decision',decision);publish()
            history=worker.session(session_id)['messages']
        return result
    except Exception:
        manager.pause(reason='실행 오류')
        publish()
        raise
    finally:
        if worker.stopping:manager.pause(reason='사용자 중지')
        publish()
