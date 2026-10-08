"""Write a byte-count/checksum inventory for downloaded public artifacts."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
FILES=[
"data/external_sources/nasdaq/01302019.NASDAQ_ITCH50.gz",
"data/external_sources/fi2010/BenchmarkDatasets.zip",
"data/external_sources/finrl_base/FinRL-master.zip",
"data/external_sources/finrl_base/dow30_vix_daily.csv",
"data/external_sources/finrl_imitation/full_data.csv","data/external_sources/finrl_imitation/merged.csv",
"data/external_sources/finrl_imitation/trade_data.csv","data/external_sources/finrl_imitation/trade_tech.csv",
"data/external_sources/finrl_imitation/train_data.csv","data/external_sources/finrl_imitation/train_tech.csv",
"data/external_sources/trademaster/order_execution_BTC/train.csv",
"data/external_sources/trademaster/order_execution_BTC/valid.csv",
"data/external_sources/trademaster/order_execution_BTC/test.csv",
"data/external_sources/trademaster/LSTM.pth",
"runtime-global-research-pretrain/teacher_replay.pt",
"runtime-global-research-pretrain/candidate.pt",
]

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()

rows=[]
for rel in FILES:
 p=ROOT/rel
 if p.exists(): rows.append({"path":rel,"bytes":p.stat().st_size,"sha256":digest(p)})
out=ROOT/"data/external_sources/manifest.json"
out.write_text(json.dumps({"artifacts":rows},indent=2),encoding='utf8')
print(f"wrote {out} ({len(rows)} files)")
