"""Document the existing single /api gateway using its registered route schemas."""
from copy import deepcopy

from fastapi.openapi.utils import get_openapi


def register_api_docs(app, router):
    def openapi():
        if app.openapi_schema is not None:
            return app.openapi_schema
        native = get_openapi(title=app.title, version=app.version, routes=router.routes)
        components = deepcopy(native.get('components', {}))
        schemas = components.setdefault('schemas', {})
        commands = []
        for path, methods in native['paths'].items():
            if not path.startswith('/api/'):
                continue
            operation = path.removeprefix('/api/')
            for method, detail in methods.items():
                if method not in ('get', 'post'):
                    continue
                payload = detail.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema')
                if payload is None:
                    parameters = [p for p in detail.get('parameters', []) if p.get('in') == 'query']
                    payload = {'type': 'object', 'properties': {p['name']: p.get('schema', {}) for p in parameters}}
                    required = [p['name'] for p in parameters if p.get('required')]
                    if required:
                        payload['required'] = required
                command_name = 'Command_' + detail['operationId']
                operation_schema = {'type': 'string', 'default': operation}
                if '{' not in operation:
                    operation_schema['enum'] = [operation]
                schemas[command_name] = {
                    'title': method.upper() + ' ' + operation,
                    'type': 'object',
                    'description': detail.get('description', '') + (' 경로의 {변수}는 operation 안에서 실제 값으로 바꾸세요.' if '{' in operation else ''),
                    'required': ['operation', 'payload'],
                    'properties': {'operation': operation_schema, 'payload': payload},
                }
                commands.append({'$ref': '#/components/schemas/' + command_name})
        response = {'200': {'description': '선택한 명령의 응답'}, '422': {'description': '입력값 검증 실패'}}
        app.openapi_schema = {
            'openapi': native['openapi'],
            'info': {'title': '백엔드 API', 'version': app.version,
                     'description': '모든 명령은 기존 단일 /api로 전달됩니다. POST의 요청 형식에서 명령을 선택하세요. 직접 실행은 Try it out → Execute를 누른 경우에만 수행합니다.'},
            'paths': {'/api': {
                'get': {'tags': ['단일 API'], 'summary': '읽기 전용 명령 조회', 'operationId': 'readCommand',
                        'parameters': [
                            {'name': 'operation', 'in': 'query', 'required': True, 'schema': {'type': 'string', 'default': 'health'}},
                            {'name': 'payload', 'in': 'query', 'schema': {'type': 'string', 'default': '{}'}, 'description': 'JSON 객체를 문자열로 입력합니다.'}],
                        'responses': response},
                'post': {'tags': ['단일 API'], 'summary': '등록된 백엔드 명령 실행', 'operationId': 'executeCommand',
                         'requestBody': {'required': True, 'content': {'application/json': {
                             'schema': {'oneOf': commands},
                             'example': {'operation': 'health', 'payload': {}}}}},
                         'responses': response},
            }},
            'components': components,
        }
        return app.openapi_schema

    app.openapi = openapi
