"""Bounded live collection: full batches first, timed smaller homogeneous batches next."""
import time


def batch_plan(replay, settings, now=None):
    target=settings if isinstance(settings,int) else settings.batch_size
    minimum=target if isinstance(settings,int) else min(target,settings.minimum_batch_size)
    wait=0 if isinstance(settings,int) else settings.batch_wait_seconds
    now=time.time() if now is None else now
    groups=replay.get('groups',[])
    full=[g for g in groups if g['ready']>=target]
    eligible=[g for g in groups if g['ready']>=minimum and now-g.get('oldest_created',now)>=wait]
    group=min(full or eligible,key=lambda g:g.get('oldest_created',now),default=None)
    waiting=max(groups,key=lambda g:(g['ready'],-g.get('oldest_created',now)),default=None)
    ready=group['ready'] if group else replay.get('batch_ready',0)
    required=target if not group or full else min(target,ready)
    observed=group or waiting
    return dict(ready=ready,required=required,target=target,minimum=minimum,adaptive=bool(group and not full),
                collection_wait_seconds=max(0,int(wait-(now-observed.get('oldest_created',now)))) if observed else wait)
