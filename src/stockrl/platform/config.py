from __future__ import annotations

import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from ..paths import PROJECT_ROOT, DEFAULT_MODEL_DIR


class LearningSettings(BaseModel):
    batch_size: int = Field(32, ge=4, le=1024)
    epochs: int = Field(4, ge=1, le=20)
    learning_rate: float = Field(0.0003, gt=0, le=0.01)
    discount: float = Field(0.99, ge=0, le=1)
    clip_epsilon: float = Field(0.2, gt=0, lt=1)
    entropy_coefficient: float = Field(0.002, ge=0, le=0.1)
    max_policy_lag: int = Field(2, ge=0, le=10)
    checkpoint_seconds: int = Field(60, ge=5)
    cpu_threads: int = Field(2, ge=1)


class ResourceSettings(BaseModel):
    ram_reserve_gib: float = Field(4, ge=1)
    vram_reserve_gib: float = Field(1.5, ge=0.5)
    expert_cache_count: int = Field(3, ge=1, le=20)
    market_refresh_seconds: int = Field(300, ge=30)
    inference_timeout_seconds: int = Field(180, ge=10)
    journal_limit_mib: int = Field(512, ge=32)
    retained_transitions: int = Field(10000, ge=256)
    revisions: int = Field(5, ge=2, le=50)
    disk_reserve_gib: float = Field(2, ge=0.1)
    market_queue_batches: int = Field(64, ge=4, le=1024)


class DataSettings(BaseModel):
    poll_seconds: float = Field(15, ge=1)
    timeout_seconds: float = Field(10, ge=1, le=60)


class RiskSettings(BaseModel):
    max_asset_weight: float = Field(0.25, gt=0, le=1)
    max_exposure: float = Field(0.9, ge=0, le=1)
    max_turnover: float = Field(0.25, gt=0, le=1)
    max_drawdown: float = Field(0.15, gt=0, le=1)
    freshness_seconds: int = Field(300, ge=60)
    fee: float = Field(0.001, ge=0, lt=0.1)
    slippage: float = Field(0.0001, ge=0, lt=0.1)


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    runtime: str = "runtime/finrlx"
    instruments: str = "configs/live_symbols_korea.json"
    expert_checkpoint: str = str(DEFAULT_MODEL_DIR / "champion.pt")
    enabled_experts: list[str] = Field(default_factory=list)
    learning: LearningSettings = Field(default_factory=LearningSettings)
    resources: ResourceSettings = Field(default_factory=ResourceSettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    data: DataSettings = Field(default_factory=DataSettings)

    def resolve(self, value: str) -> Path:
        path = Path(value).expanduser()
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def state_dir(self) -> Path:
        path = self.resolve(self.runtime).resolve()
        if not path.is_relative_to(PROJECT_ROOT.resolve()):
            raise ValueError("운영 상태는 프로젝트 runtime 폴더 안에 저장해야 합니다.")
        path.mkdir(parents=True, exist_ok=True)
        return path


CONFIG_PATH = PROJECT_ROOT / "configs" / "operations.json"


def load_settings(path: Path = CONFIG_PATH) -> Settings:
    return Settings.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
