"""Import large-menu managers; expose their existing backend connections."""
from stockrl.trading.trading_menu_manager import GROUP as TRADING
from stockrl.trading.trading_menu_manager import ROUTERS as TRADING_ROUTERS
from stockrl.finrl.finrl_menu_manager import GROUP as FINRL
from stockrl.finrl.finrl_menu_manager import ROUTERS as FINRL_ROUTERS
from stockrl.extensions.extensions_menu_manager import GROUP as EXTENSIONS
from stockrl.extensions.extensions_menu_manager import ROUTERS as EXTENSIONS_ROUTERS
from stockrl.management.management_menu_manager import GROUP as MANAGEMENT
from stockrl.management.management_menu_manager import ROUTERS as MANAGEMENT_ROUTERS
from rea.rea_menu_manager import GROUP as REA
from rea.rea_menu_manager import ROUTERS as REA_ROUTERS

GROUPS=(TRADING,FINRL,REA,EXTENSIONS,MANAGEMENT)
_routes_by_menu={}

def owner(operation):
    if operation=='framework/native_call':return 'management','backend-browser'
    for group in GROUPS:
        for menu in group['menus']:
            if any(operation==pattern or pattern.endswith('/') and operation.startswith(pattern) for pattern in menu['operations']):
                return group['id'],menu['id']
    return 'management','system'

def bind(routes):
    """Bind existing handlers once without moving state/model ownership."""
    _routes_by_menu.clear()
    for route in routes:
        if not hasattr(route,'endpoint') or not route.path.startswith('/api/'):continue
        operation=route.path.removeprefix('/api/')
        menus=set(('frameworks','project-modules','system','backend-browser') if operation=='framework/{action}' else (owner(operation)[1],))
        for group in GROUPS:
            for menu in group['menus']:
                if any(not pattern.endswith('/') and route.path_regex.fullmatch('/api/'+pattern) for pattern in menu['operations']):menus.add(menu['id'])
        for menu in menus:_routes_by_menu.setdefault(menu,[]).append(route)

def dispatch(scope,parameters):
    from starlette.routing import Match
    operation=scope['path'].removeprefix('/api/')
    menu=owner(operation)[1]
    if operation=='framework/native_call':
        module=str(parameters.get('module',''))
        menu='frameworks' if module.startswith('FinRL:') else 'backend-browser'
    for route in _routes_by_menu.get(menu,()):
        match,child=route.matches(scope)
        if match==Match.FULL:return route,{**scope,**child}
    return None

def catalog(routes):
    from pydantic import TypeAdapter
    from stockrl.platform.framework_operations import action_list
    actions=action_list()
    for action in actions:
        action['group'],action['menu_id']=owner('framework/'+action['id'])
    def fields(values):
        properties={};required=[]
        for field in values:
            schema=TypeAdapter(field.field_info.annotation).json_schema()
            schema['title']=field.alias
            if field.field_info.description:schema['description']=field.field_info.description
            properties[field.alias]=schema
            if field.required:required.append(field.alias)
        return {'type':'object','properties':properties,'required':required}
    commands=[]
    registered_paths={route.path for route in routes if hasattr(route,'endpoint')}
    for route in routes:
        if not hasattr(route,'endpoint') or not route.path.startswith('/api/'):continue
        operation=route.path.removeprefix('/api/')
        group,menu=owner(operation)
        body={'type':'object','additionalProperties':True}
        if route.body_field:
            annotation=route.body_field.field_info.annotation
            body=TypeAdapter(annotation).json_schema()
        command={'operation':operation,'methods':sorted(route.methods or ()),
            'module':route.endpoint.__module__,'function':route.endpoint.__name__,
            'group':group,'menu':menu,'description':route.description or '',
            'path_schema':fields(route.dependant.path_params),
            'query_schema':fields(route.dependant.query_params),'body_schema':body}
        commands.append(command)
        if operation=='framework/{action}':
            for action in actions:
                if '/api/framework/'+action['id'] in registered_paths:continue
                properties={key:{'title':key} for key in action['fields']}
                for key in ('kwargs','init_kwargs','env_kwargs'):
                    if key in properties:properties[key]['type']='object'
                for key in ('symbols','steps','argv'):
                    if key in properties:properties[key]['type']='array'
                if 'symbols' in properties:properties['symbols']['items']={'type':'string'}
                commands.append({**command,'operation':'framework/'+action['id'],
                    'group':action['group'],'menu':action['menu_id'],
                    'description':action['name']+' · '+action['module']+' · '+action['function'],
                    'path_schema':{'type':'object','properties':{}},
                    'body_schema':{**body,'properties':properties}})
    return {'groups':[{'id':g['id'],'title':g['title'],'menus':list(g['menus'])} for g in GROUPS],
        'actions':actions,'commands':commands}


def register_api(api,app):
    """Collect small-menu routers through the five large-menu coordinators."""
    for routers in (TRADING_ROUTERS,FINRL_ROUTERS,REA_ROUTERS,EXTENSIONS_ROUTERS,MANAGEMENT_ROUTERS):
        for router in routers:
            api.include_router(router)
            app.router.on_startup.extend(router.on_startup)
            app.router.on_shutdown.extend(router.on_shutdown)
    bind(api.routes)
