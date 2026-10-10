"""Immutable frozen Expert packages and their referenced weight files."""
from __future__ import annotations

import gc
import hashlib
import os
import json
from pathlib import Path
import torch


PACKAGE_FORMAT='frozen_expert_package_v1'
HEADER_FORMAT='registered_vertical_trading_moe_v2'


def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def package_path(header_path, reference):
    root=Path(header_path).resolve().parent
    path=(root/reference['file']).resolve()
    if not path.is_relative_to(root):raise ValueError('Expert 패키지는 모델 폴더 안에 있어야 합니다.')
    if not path.is_file() or path.stat().st_size!=reference['bytes']:
        raise ValueError('Expert 패키지가 없거나 크기가 달라졌습니다: '+path.name)
    return path


def load_package(header_path,reference,verify=False):
    path=package_path(header_path,reference)
    if verify and digest(path)!=reference['sha256']:raise ValueError('Expert 패키지 checksum이 다릅니다.')
    saved=json.loads(path.read_text(encoding='utf8')) if path.suffix=='.json' else torch.load(path,map_location='cpu',weights_only=True,mmap=True)
    if saved.get('format')!=PACKAGE_FORMAT:raise ValueError('Frozen Expert 패키지 형식이 아닙니다.')
    if saved.get('weight_asset'):
        weight=package_path(header_path,saved['weight_asset'])
        if verify and digest(weight)!=saved['weight_asset']['sha256']:raise ValueError('GGUF 고정 가중치 checksum이 다릅니다.')
    return saved


def atomic_torch_save(value, path):
    temporary=path.with_suffix('.partial')
    try:
        with temporary.open('wb') as stream:
            torch.save(value,stream);stream.flush();os.fsync(stream.fileno())
        return temporary
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
