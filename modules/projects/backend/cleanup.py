"""Quarantine generated residue without removing installed applications or data."""
from datetime import datetime
import time
from . import installer,runtime,store


def clean():
    with store.LOCK,runtime.LOCK:
        if installer.JOBS or runtime.busy_reason():raise ValueError('진행 중인 작업이 끝난 뒤 정리하세요.')
        candidates=list((store.STATE/'projects').glob('*/exports/*.zip'))
        candidates += [path for path in (store.STATE/'imports').glob('*') if path.is_file() and time.time()-path.stat().st_mtime>3600]
        moved=[];size=0
        for path in candidates:
            resolved=path.resolve()
            if path.is_symlink() or not resolved.is_relative_to(store.STATE.resolve()):continue
            relative=resolved.relative_to(store.ROOT.resolve())
            target=store.ROOT/'휴지통'/relative
            if target.exists():target=target.with_name(target.stem+'-'+datetime.now().strftime('%Y%m%d%H%M%S%f')+target.suffix)
            target.parent.mkdir(parents=True,exist_ok=True)
            size+=path.stat().st_size;path.rename(target);moved.append(str(relative))
        return {'files':len(moved),'bytes':size,'detail':f'이전 내보내기·임시 파일 {len(moved)}개를 휴지통으로 이동했습니다.'}
