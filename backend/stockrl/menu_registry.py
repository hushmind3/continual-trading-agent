"""Import five large-menu managers; expose their existing backend connections."""
from .trading.trading_menu_manager import GROUP as TRADING
from .finrl.finrl_menu_manager import GROUP as FINRL
from .finrl_trading.finrl_trading_menu_manager import GROUP as FINRL_TRADING
from .extensions.extensions_menu_manager import GROUP as EXTENSIONS
from .management.management_menu_manager import GROUP as MANAGEMENT

GROUPS=(TRADING,FINRL,FINRL_TRADING,EXTENSIONS,MANAGEMENT)
_routes_by_menu={}

def owner(operation):
    if operation.startswith('framework/') and operation.count('/')==1:
        from .finrl.operations import ACTIONS as finrl_actions
        from .finrl_trading.operations import ACTIONS as trading_actions
        action=operation.split('/',1)[1]
        if action not in ('stock_data','stock_train','stock_backtest'):
            if action in finrl_actions:return 'finrl','frameworks'
            if action in trading_actions:return 'finrl_trading','finrl-trading'
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
        menus=set(('frameworks','finrl-trading','project-modules','finrl','stock-training','backtest','system') if operation=='framework/{action}' else (owner(operation)[1],))
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
        menu='finrl-trading' if module.startswith('FinRL-X:') else 'frameworks' if module.startswith('FinRL:') else 'project-modules'
    for route in _routes_by_menu.get(menu,()):
        match,child=route.matches(scope)
        if match==Match.FULL:return route,{**scope,**child}
    return None

def catalog(routes):
    from pydantic import TypeAdapter
    from .platform.framework_operations import action_list
    actions=action_list()
    for action in actions:
        action['group']='finrl_trading' if action['module'].startswith('FinRL-X:') else 'finrl' if action['module'].startswith('FinRL:') else 'extensions'
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
    for route in routes:
        if not hasattr(route,'endpoint') or not route.path.startswith('/api/'):continue
        operation=route.path.removeprefix('/api/')
        group,menu=owner(operation)
        body={'type':'object','additionalProperties':True}
        if route.body_field:
            annotation=route.body_field.field_info.annotation
            body=TypeAdapter(annotation).json_schema()
        commands.append({'operation':operation,'methods':sorted(route.methods or ()),
            'module':route.endpoint.__module__,'function':route.endpoint.__name__,
            'group':group,'menu':menu,'description':route.description or '',
            'path_schema':fields(route.dependant.path_params),
            'query_schema':fields(route.dependant.query_params),'body_schema':body})
    return {'groups':[{'id':g['id'],'title':g['title'],'menus':list(g['menus'])} for g in GROUPS],
        'actions':actions,'commands':commands}
