"""Bounded inactivity checks and ownership-safe cancellation of live agent work."""
import time

ACTIVE_STATES = ('starting', 'running', 'stopping')


class ProgressWindow:
    def __init__(self, seconds=900):
        self.seconds = seconds
        self.changed = time.monotonic()
        self.signature = None

    def observe(self, job):
        metrics = job.get('metrics') or {}
        events = job.get('events') or []
        signature = (job.get('state'), job.get('live_text'), len(events),
                     tuple(metrics.get(key) for key in ('input_tokens', 'output_tokens', 'api_calls', 'context_tokens')),
                     str(events[-1]) if events else '')
        now = time.monotonic()
        if signature != self.signature:
            self.signature = signature; self.changed = now
        return now - self.changed >= self.seconds


def stop_owned(bridge, session):
    bridge.call('stop', {'session_id': session})
    while True:
        job = bridge.call('status')['job']
        if job.get('session_id') != session or job['state'] not in ACTIVE_STATES: return
        time.sleep(.2)


def wait_owned(bridge, session, cancelled, execution):
    watch = ProgressWindow()
    deadline = time.monotonic() + 900
    while True:
        job = bridge.call('status')['job']
        if job.get('session_id') != session: raise ValueError('하네스 작업의 실행 소유권이 바뀌었습니다.')
        if job['state'] not in ACTIVE_STATES: return job
        idle = watch.observe(job)
        if cancelled.is_set() or (idle if execution else time.monotonic() > deadline):
            stop_owned(bridge, session)
            if cancelled.is_set(): raise ValueError('소유자가 앱 실행을 중지했습니다.')
            raise ValueError('900초 동안 실행 진행이 없어 중지했습니다.' if execution else '대화 응답 시간이 초과돼 중지했습니다.')
        cancelled.wait(.4)
