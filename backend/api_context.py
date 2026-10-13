"""Shared HTTP context; menu implementations live in their own folders."""
from __future__ import annotations
import subprocess
import ast
import csv
import json
import math
import os
import re
import sqlite3
import sys
import time
import uuid
import zipfile
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from starlette.routing import Route
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from stockrl import ROOT
from stockrl.finrl.framework import CASH_ENVIRONMENT
from stockrl.finrl.framework import policy_files
from stockrl.finrl.framework import policy_checkpoint
from stockrl.finrl.framework import sac_example
from stockrl.finrl.framework import finrl_file
from stockrl.finrl.framework import champion_structure_environment
from stockrl.finrl_trading import finrlx
from stockrl.state_io import atomic_json
from stockrl.state_io import read_json
from stockrl.state_io import update_json
from api_transport import FiniteJSONResponse
from api_transport import UnifiedAPI
from stockrl.platform.resources import ResourceMonitor
from stockrl.platform.system_operations import system
from stockrl.platform.system_operations import apply_state
from stockrl.platform.system_operations import apply_running
from stockrl.platform.system_operations import start_apply
from stockrl.platform.system_operations import busy
from stockrl.platform.system_operations import check_system
from stockrl.trading.operation_control.operations_runtime import runtime
from stockrl.platform.library_operations import library as library_manager
from stockrl.expert_registry_native import ExpertRegistry
from finrl.agents.stablebaselines3.models import MODELS
from stable_baselines3.common.off_policy_algorithm import OffPolicyAlgorithm
RUNTIME = ROOT / "runtime/official"
DB = ROOT / "data/finrl_trading.db"
MODEL_DIR = Path.home() / "Desktop/모델"
ENVIRONMENT = CASH_ENVIRONMENT
app = FastAPI(title="Local project platform", version="2",default_response_class=FiniteJSONResponse)
private_api=APIRouter(default_response_class=FiniteJSONResponse)
FRONTEND_DIST = ROOT / "frontend/dist"
resource_monitor = ResourceMonitor(ROOT)
database_cache = {"stamp": None, "value": None}
