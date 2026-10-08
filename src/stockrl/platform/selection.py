"""Hot slot selection without resizing tensors or restarting market inference."""
from ..state_io import read_json,atomic_json


class SlotDisabled(InterruptedError):pass


def selection(settings,default):
    value=read_json(settings.state_dir/'expert-library.json')
    return value.get('selection_revision',0),value.get('active',default)


def acknowledge(settings,revision):
    path=settings.state_dir/'library-job.json';value=read_json(path)
    if value.get('stage')=='checkpoint_requested' and value.get('selection_revision')==revision:
        atomic_json({**value,'stage':'complete','detail':'구성 적용 · 학습 체크포인트 저장 완료'},path)
