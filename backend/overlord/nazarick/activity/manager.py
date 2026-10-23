"""Persisted activity submenu; no simulated jobs or generated success counts."""
from fastapi import APIRouter
from .. import store

MENU = {'id': 'overlord/nazarick/activity', 'title': '작업 기록',
        'operations': ['overlord/nazarick/activity/']}
router = APIRouter(prefix='/api/overlord/nazarick/activity')


@router.get('/list')
def listing():
    return {'items': store.activity()}
