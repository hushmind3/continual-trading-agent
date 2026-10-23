"""Explicit adapter contract; discovery never starts engines or business tasks."""
from typing import Protocol


class Adapter(Protocol):
    title: str

    def targets(self) -> list[dict]: ...
    def inspect(self, target: str) -> dict: ...


class PlatformModuleAdapter:
    title = '플랫폼 등록 기능'

    def targets(self):
        from menu_registry import MODULE_ENTRIES
        return [{'id': metadata['id'], 'name': getattr(entry, 'MENU', {}).get('title') or metadata['group']['title'],
                 'available': not bool(getattr(entry, 'load_error', None)),
                 'error': getattr(entry, 'load_error', None)}
                for metadata, entry in MODULE_ENTRIES if metadata['id'] != 'nazarick']

    def inspect(self, target):
        from menu_registry import MODULE_ENTRIES
        found = next(((metadata, entry) for metadata, entry in MODULE_ENTRIES if metadata['id'] == target), None)
        if found is None:
            raise ValueError('대상 기능이 현재 플랫폼에 등록되어 있지 않습니다.')
        metadata, entry = found
        if error := getattr(entry, 'load_error', None):
            raise ValueError('대상 기능 등록 실패: ' + str(error))
        menus = getattr(entry, 'MENUS', None) or getattr(entry, 'GROUP', {}).get('menus') or (entry.MENU,)
        return {'message': '현재 서버의 기능 등록과 API 연결 규격을 확인했습니다.',
                'module': metadata['id'], 'menus': [menu['title'] for menu in menus],
                'operations': [operation for menu in menus for operation in menu['operations']],
                'scope': '등록 확인만 수행했습니다. 엔진 가동·추론·업무 실행은 확인하지 않았습니다.'}


ADAPTERS: dict[str, Adapter] = {'platform_module': PlatformModuleAdapter()}


def catalog():
    return [{'id': key, 'name': adapter.title, 'targets': adapter.targets()} for key, adapter in ADAPTERS.items()]
