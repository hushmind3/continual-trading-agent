"""Persist the CLI job outcome; preserve saved policies before a new run."""
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from .framework import ROOT
from .state_io import read_json, atomic_json, update_json


def main():
    root = ROOT / "runtime/official"
    job_id = sys.argv[1]
    for _ in range(100):
        job = read_json(root / "job.json")
        if job.get("id") == job_id:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("작업 정보를 읽지 못했습니다.")
    job=update_json(root/'job.json',lambda current:{**current,'status':'running'} if current.get('id')==job_id and current.get('status')=='starting' else None)
    if job.get('id')!=job_id or job.get('status')!='running':return
    exit_code = 0;failure=None
    try:
        if job['command']=='framework':
            from .platform.framework_operations import execute,preview
            result=execute(job['action'],job['parameters'],root/job['output'])
            atomic_json(result,root/job['output']/'result.json')
            job['result']=preview(result)
            return
        if job["command"]=="collect":
            from .framework import finrlx
            frame=finrlx("data.data_fetcher").fetch_price_data(
                job["symbols"],job["start_date"],job["end_date"])
            print("FinRL-X 가격 수집 완료:",len(frame),"행",flush=True)
            return
        if job["command"] == "train" and not job.get('output'):
            backup = root / "archives" / job_id
            for name in (job.get('algorithm','sac')+'.zip', "replay.pkl", "dataset.json"):
                if (root / name).is_file():
                    backup.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(root / name, backup / name)
            print("학습 저장 전: 이전 정책·Replay는 archives에 보관합니다.", flush=True)
        args = ["stockrl", job["command"], "--currency", job["currency"], "--symbols", *job["symbols"]]
        args.extend(['--algorithm',job.get('algorithm','sac')])
        if job.get('total_timesteps') is not None:args.extend(['--total-timesteps',str(job['total_timesteps'])])
        if job["resume"]:
            args.append("--resume")
        if job.get('output'):args.extend(['--output',str(root/job['output'])])
        if job.get('champion_path'):args.extend(['--champion-path',job['champion_path']])
        if job.get('champion_output'):args.extend(['--champion-output',job['champion_output']])
        if job.get('checkpoint_path'):args.extend(['--checkpoint-path',job['checkpoint_path']])
        sys.argv = args
        from .official_cli import main as official_main
        official_main()
        if job["command"]=="train":
            print('학습 결과 저장 완료. 운영 반영은 모델 선택 화면에서 직접 승인하세요.',flush=True)
    except BaseException:
        exit_code = 1;failure=str(sys.exc_info()[1])
        traceback.print_exc()
        if job['command']=='framework':
            from .platform.framework_operations import ACTIONS
            row=ACTIONS[job['action']]
            result_path=root/job['output']/'result.json';failed=read_json(result_path)
            failed.update(action=job['action'],module=row[2],function=row[3],status='failed',error=str(sys.exc_info()[1]))
            atomic_json(failed,result_path)
    finally:
        def finished(current):
            if current.get('id')!=job_id or current.get('status')=='stopped':return None
            if job.get('result') is not None:current['result']=job['result']
            if failure:current.update(error=failure,detail=failure)
            else:
                current.pop('error',None);current.pop('detail',None)
            current.update(status="succeeded" if exit_code == 0 else "failed", exit_code=exit_code,
                           finished_at=datetime.now(timezone.utc).isoformat())
            return current
        update_json(root/'job.json',finished)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
