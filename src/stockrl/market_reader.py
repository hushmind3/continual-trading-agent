"""Incremental market CSV reader, independent of model and learner imports."""
from __future__ import annotations
import hashlib
import io
from pathlib import Path

class IncrementalMarketCSV:
    """Read an append-only feed once, then parse only complete appended rows."""
    def __init__(self, path: str | Path, retain_timestamps: int = 4096):
        self.path=Path(path); self.retain_timestamps=retain_timestamps
        self.frame=None; self.offset=0; self.partial=b""; self.header=b""; self.fingerprint=None
        self.processed_through=None

    def _fingerprint(self):
        stat=self.path.stat()
        with self.path.open("rb") as stream:
            prefix=stream.read(2048)
        return stat.st_size,stat.st_mtime_ns,getattr(stat,"st_ino",0),hashlib.sha256(prefix).digest()

    def _trim(self, frame):
        import pandas as pd
        if frame.empty or "date" not in frame or "symbol" not in frame:
            return frame
        stamps=pd.to_datetime(frame["date"],utc=True,errors="coerce")
        unique=stamps.dropna().drop_duplicates().sort_values()
        if len(unique)<=self.retain_timestamps:
            return frame
        cutoff=unique.iloc[-self.retain_timestamps]
        # Keep all unprocessed bars, plus the model's input history. A restart
        # or a slow observer must not silently discard the next rolling windows.
        if self.processed_through is None:
            return frame
        processed=pd.Timestamp(self.processed_through)
        if processed.tzinfo is None:
            processed=processed.tz_localize("UTC")
        else:
            processed=processed.tz_convert("UTC")
        prior=unique.loc[unique<=processed]
        if len(prior):
            cutoff=min(cutoff,prior.iloc[-min(128,len(prior))])
        recent=frame.loc[stamps>=cutoff]
        carry=frame.groupby("symbol",sort=False).tail(128)
        carry=carry.loc[stamps.loc[carry.index]<cutoff]
        return pd.concat((carry,recent),ignore_index=True).sort_values(
            ["date","symbol"],kind="stable").reset_index(drop=True)

    def refresh(self):
        import pandas as pd
        signature=self._fingerprint()
        reset=(self.frame is None or signature[0]<self.offset or
               (self.fingerprint is not None and signature[2:]!=self.fingerprint[2:]))
        if reset:
            data=self.path.read_bytes()
            end=data.rfind(b"\n")+1
            complete=data[:end]
            self.partial=data[end:]
            self.header=complete.splitlines(keepends=True)[0] if complete else b""
            self.frame=pd.read_csv(io.BytesIO(complete)) if complete else pd.DataFrame()
            self.offset=len(data)
            self.frame=self._trim(self.frame)
        elif signature[0]>self.offset:
            with self.path.open("rb") as stream:
                stream.seek(self.offset); appended=stream.read()
            self.offset+=len(appended)
            combined=self.partial+appended
            end=combined.rfind(b"\n")+1
            complete=combined[:end]; self.partial=combined[end:]
            if complete:
                fresh=pd.read_csv(io.BytesIO(self.header+complete))
                self.frame=pd.concat((self.frame,fresh),ignore_index=True)
                self.frame=self.frame.drop_duplicates(["date","symbol"],keep="last")
                self.frame=self._trim(self.frame)
        self.fingerprint=signature
        return self.frame,signature
