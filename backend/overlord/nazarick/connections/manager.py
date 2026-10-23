"""Connection definitions, registration checks and removal, behind one API."""
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .. import adapters, store

MENU = {'id': 'overlord/nazarick/connections', 'title': '연결 대상',
        'operations': ['overlord/nazarick/connections/']}
router = APIRouter(prefix='/api/overlord/nazarick/connections')


class Definition(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    name: str = Field(min_length=1, max_length=80)
    category: Literal['execution', 'data', 'identity', 'payment', 'distribution', 'custom']
    adapter: Literal['planned', 'platform_module'] = 'planned'
    target: str = Field(default='', max_length=100)
    notes: str = Field(default='', max_length=1000)


class Identity(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[a-f0-9]{32}$')


def find(db, key):
    row = db.execute('SELECT * FROM connections WHERE id=?', (key,)).fetchone()
    if row is None:
        raise HTTPException(404, '등록한 연결 대상을 찾을 수 없습니다.')
    return dict(row)


@router.get('/list')
def listing():
    return {'items': store.connections(), 'adapters': adapters.catalog()}


@router.post('/save')
def save(value: Definition):
    if value.adapter != 'planned':
        adapter = adapters.ADAPTERS[value.adapter]
        if value.target not in {item['id'] for item in adapter.targets()}:
            raise HTTPException(400, '현재 등록된 플랫폼 기능을 선택하세요.')
    elif value.target:
        raise HTTPException(400, '연결 예정 대상은 어댑터 대상 ID를 지정할 수 없습니다.')
    stamp = store.now()
    with store.database() as db:
        previous = find(db, value.id) if value.id else None
        item = {**value.model_dump(), 'id': value.id or uuid4().hex,
                'status': 'planned' if value.adapter == 'planned' else 'unchecked', 'checked_at': None,
                'created_at': previous['created_at'] if previous else stamp, 'updated_at': stamp}
        db.execute('''INSERT INTO connections VALUES (:id,:name,:category,:adapter,:target,:notes,
                      :status,:checked_at,:created_at,:updated_at)
                      ON CONFLICT(id) DO UPDATE SET name=excluded.name,category=excluded.category,
                      adapter=excluded.adapter,target=excluded.target,notes=excluded.notes,
                      status=excluded.status,checked_at=NULL,updated_at=excluded.updated_at''', item)
        store.event(db, item, 'updated' if previous else 'created', 'saved',
                    {'message': '연결 대상을 수정했습니다.' if previous else '연결 대상을 등록했습니다.'})
    return item


@router.post('/inspect')
def inspect(value: Identity):
    with store.database() as db:
        item = find(db, value.id)
        adapter = adapters.ADAPTERS.get(item['adapter'])
        if adapter is None:
            raise HTTPException(409, '외부 연결부는 아직 구현되지 않았습니다. 연결 예정 상태입니다.')
        try:
            detail = adapter.inspect(item['target'])
            status = 'registered'
        except ValueError as exc:
            detail, status = {'message': str(exc)}, 'failed'
        stamp = store.now()
        db.execute('UPDATE connections SET status=?,checked_at=?,updated_at=? WHERE id=?',
                   (status, stamp, stamp, value.id))
        store.event(db, item, 'inspected', status, detail)
    return {'status': status, 'detail': detail}


@router.post('/remove')
def remove(value: Identity):
    with store.database() as db:
        item = find(db, value.id)
        db.execute('DELETE FROM connections WHERE id=?', (value.id,))
        store.event(db, item, 'removed', 'removed', {'message': '연결 정의만 제거했습니다. 대상 기능과 데이터는 유지됩니다.'})
    return {'removed': True}
