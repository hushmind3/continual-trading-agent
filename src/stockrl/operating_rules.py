"""Shared, explicit operating settings and the KST daily boundary."""
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SEOUL = ZoneInfo("Asia/Seoul")
RULES_PATH = Path(__file__).resolve().parents[2]/"configs"/"online_learning.json"


def operating_rules(path=None):
    path=Path(path) if path is not None else RULES_PATH
    rules=json.loads(path.read_text(encoding="utf-8"))
    if not 0 <= int(rules["account_reset_hour_kst"]) <= 23:
        raise ValueError("account_reset_hour_kst must be 0..23")
    if int(rules["validation_min_market_minutes"]) < 1:
        raise ValueError("validation_min_market_minutes must be positive")
    for key in ("training_batch_size","training_optimizer_steps","checkpoint_every_updates","evidence_cache_rows",
                'evaluation_max_observations','evaluation_min_observations','market_expert_refresh_seconds',
                'max_policy_lag','learner_queue_capacity','learner_ram_reserve_mib','native_vram_reserve_mib','cpu_threads',
                'runtime_restart_attempts','runtime_restart_base_seconds'):
        if int(rules[key]) < 1:
            raise ValueError(f"{key} must be positive")
    if int(rules['reward_credit_observations']) < 1:
        raise ValueError("reward_credit_observations must be positive")
    if int(rules['reward_credit_seconds']) < 1:
        raise ValueError("reward_credit_seconds must be positive")
    if float(rules['reward_credit_discount']) != 1.0:
        raise ValueError("net-equity reward uses undiscounted credit (1.0)")
    if rules['reward_credit_kind'] not in ('seconds','bars'):raise ValueError('reward_credit_kind must be seconds or bars')
    for key in ('learning_rate','gradient_clip_norm','checkpoint_interval_seconds','inference_poll_seconds','training_reward_scale'):
        value=float(rules[key])
        if not math.isfinite(value) or value<=0:raise ValueError(key+' must be finite and positive')
    for key in ('value_loss_weight','router_entropy_weight','replay_rejection_tolerance','promotion_min_delta','promotion_min_return','promotion_drawdown_tolerance'):
        if not math.isfinite(float(rules[key])) or float(rules[key])<0:raise ValueError(key+' must be finite and nonnegative')
    if not 0<float(rules['evaluation_replay_fraction'])<1:raise ValueError('evaluation_replay_fraction must be between zero and one')
    if not 0<float(rules['policy_clip_epsilon'])<1:raise ValueError('policy_clip_epsilon must be between zero and one')
    if int(rules['learner_queue_capacity'])!=1:raise ValueError('one outstanding learner batch is supported')
    if not isinstance(rules['stable_champion'],bool):raise ValueError('stable_champion must be boolean')
    if not math.isfinite(float(rules['max_importance_ratio'])) or float(rules['max_importance_ratio'])<1:raise ValueError('max_importance_ratio must be finite and >=1')
    if int(rules['evaluation_max_observations'])<int(rules['evaluation_min_observations']):raise ValueError('evaluation maximum is below minimum')
    if int(rules['evidence_cache_rows'])<int(rules['evaluation_max_observations']):raise ValueError('evidence cache cannot hold the evaluation interval')
    for key,default in (("goal_target_multiple",10.0),("goal_win_bonus_points",100.0)):
        value=float(rules.get(key,default))
        if not math.isfinite(value) or value <= (1.0 if key=="goal_target_multiple" else 0.0):
            raise ValueError(f"{key} must be finite and positive (target > 1)")
    return rules


def daily_boundary(now=None, hour=7):
    local=(now or datetime.now(timezone.utc)).astimezone(SEOUL)
    boundary=local.replace(hour=hour,minute=0,second=0,microsecond=0)
    if local < boundary:
        boundary-=timedelta(days=1)
    return boundary.date().isoformat(), (boundary+timedelta(days=1)).astimezone(timezone.utc).isoformat()
