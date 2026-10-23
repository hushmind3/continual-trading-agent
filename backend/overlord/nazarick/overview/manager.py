"""Foundation overview submenu, using existing local platform registrations."""
from fastapi import APIRouter
from .. import adapters, store

MENU = {'id': 'overlord/nazarick/overview', 'title': '기반 개요',
        'operations': ['overlord/nazarick/overview']}
router = APIRouter(prefix='/api/overlord/nazarick')


@router.get('/overview')
def overview():
    return {'name': '나자릭', 'schema': 1, 'connections': store.connections(),
            'activity': store.activity(), 'adapters': adapters.catalog()}
