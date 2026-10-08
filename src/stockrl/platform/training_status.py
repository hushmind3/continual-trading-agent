"""One actionable learning state derived from actual controls, workers and replay."""
import time


def readiness(controls, workers, replay, batch_size):
    learner=workers.get('learner',{});agent=workers.get('agent',{})
    ready=replay.get('batch_ready',0);pending=replay.get('pending',0)
    result=dict(ready=ready,required=batch_size,remaining=max(0,batch_size-ready),pending=pending,action=None)
    def status(code,label,detail,action=None):
        return {**result,'code':code,'label':label,'detail':detail,'action':action}
    if learner.get('error'):return status('error','학습 오류',learner['error'])
    if not controls.get('engine'):return status('engine_off','MoE 정지','MoE를 실행해야 시장 판단과 학습이 진행됩니다.','engine')
    if not controls.get('learning'):return status('paused','학습 정지','모인 경험은 유지하며 가중치 업데이트만 멈춰 있습니다.','learning')
    if learner.get('status')=='training':return status('training','가중치 업데이트 중',f"확정된 경험 {learner.get('samples',ready)}개를 학습하고 있습니다.")
    if not learner.get('alive'):return status('starting','학습기 준비 중','저장된 모델과 optimizer 상태를 복원하고 있습니다.')
    if ready>=batch_size:
        seconds=max(0,int(learner.get('next_update_at',0)-time.time()))
        return status('cooldown' if seconds else 'ready','다음 업데이트 준비',f'저장·업데이트 간격 {seconds}초 남음' if seconds else '학습 배치가 모였습니다. 다음 업데이트를 시작합니다.')
    if not controls.get('paper'):return status('paper_off','가상체결 정지',f'확정 경험 {ready}/{batch_size}개. 가상체결을 시작하면 행동과 손익으로 새 경험을 만듭니다.','paper')
    if not controls.get('feed'):return status('feed_off','시세 수집 정지','다음 시세가 있어야 행동의 손익을 확정할 수 있습니다.','feed')
    if not replay.get('total') and pending:
        return status('settling','첫 손익 확정 대기',f'행동 {pending}건의 다음 시장 결과를 기다립니다. 확정 경험 {ready}/{batch_size}개.')
    if not replay.get('total') and not pending:
        detail=agent.get('error') or agent.get('message') or '사용 가능한 Expert 출력과 새로운 완료 시세가 필요합니다.'
        return status('observing','첫 학습 경험 생성 중',detail)
    return status('collecting','학습 경험 수집 중',f'같은 종목 구성 {ready}/{batch_size}개 · {batch_size-ready}개 더 필요 · 결과 대기 {pending}건')
