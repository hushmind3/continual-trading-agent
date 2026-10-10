"""Persist the CLI job outcome; preserve saved policies before a new run."""
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from .framework import ROOT
from .state_io import read_json, atomic_json


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
    job["status"] = "running"
    atomic_json(job, root / "job.json")
    exit_code = 0
    try:
        if job["command"]=="collect":
            from .framework import finrlx
            frame=finrlx("data.data_fetcher").fetch_price_data(
                job["symbols"],job["start_date"],job["end_date"])
            print("FinRL-X 가격 수집 완료:",len(frame),"행",flush=True)
            return
        if job["command"] == "train":
            backup = root / "archives" / job_id
            for name in ("sac.zip", "replay.pkl", "dataset.json"):
                if (root / name).is_file():
                    backup.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(root / name, backup / name)
            print("학습 저장 전: 이전 SAC·Replay는 archives에 보관합니다.", flush=True)
        args = ["stockrl", job["command"], "--currency", job["currency"], "--symbols", *job["symbols"]]
        if job["resume"]:
            args.append("--resume")
        sys.argv = args
        from .official_cli import main as official_main
        official_main()
        if job["command"]=="train":
            atomic_json({"path":"sac.zip"},root/"active-checkpoint.json")
    except BaseException:
        exit_code = 1
        traceback.print_exc()
    finally:
        current = read_json(root / "job.json")
        if current.get("id") == job_id and current.get("status") != "stopped":
            current.update(status="succeeded" if exit_code == 0 else "failed", exit_code=exit_code,
                           finished_at=datetime.now(timezone.utc).isoformat())
            atomic_json(current, root / "job.json")
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
