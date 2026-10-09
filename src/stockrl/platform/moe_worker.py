"""Unified resident inference and asynchronous central learning in one GPU process."""
import argparse
import threading
import time
import torch
from .config import load_settings,CONFIG_PATH
from .moe_session import MoESession
from .worker_state import publish
from . import agent_worker,expert_worker,learner


def run(settings,config=CONFIG_PATH):
    torch.set_num_threads(settings.learning.cpu_threads)
    session=MoESession(settings)
    functions={'experts':lambda:expert_worker.run(settings,config,session=session),
               'agent':lambda:agent_worker.run(settings,session=session),
               'learner':lambda:learner.run(settings,session=session)}
    def worker(role):
        try:functions[role]()
        except BaseException as exc:
            session.failures[role]=exc;session.closing.set()
            publish(settings,role,status='error',error=f'{type(exc).__name__}: {exc}')
    threads=[threading.Thread(target=worker,args=(role,),name='moe-'+role) for role in functions]
    for thread in threads:thread.start()
    try:
        while not session.stopped('agent') and all(t.is_alive() for t in threads):time.sleep(.2)
    finally:
        session.closing.set()
        for thread in threads:thread.join()
    # Frozen bodies stay mapped/resident during operation; only the small learned
    # checkpoints are written per update. Seal the full portable Champion after release.
    from .checkpoint import Checkpoints
    checkpoints=Checkpoints(settings.state_dir/'policies',settings.resources.revisions)
    state,_=checkpoints.load()
    if state:checkpoints.mirror(state)
    if session.failures:
        raise RuntimeError('통합 MoE 작업 실패: '+', '.join(f'{r}: {e}' for r,e in session.failures.items()))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',default=str(CONFIG_PATH));args=parser.parse_args()
    run(load_settings(args.config),args.config)
