"""Import large-menu managers; expose their existing backend connections."""
from platform_modules import registrations, ROOT

MODULE_ENTRIES=registrations()
_group_map={}
for metadata,entry in sorted(MODULE_ENTRIES,key=lambda pair:pair[0].get('order',100)):
    group=metadata['group']
    menus=getattr(entry,'MENUS',None) or getattr(entry,'GROUP',{}).get('menus') or (entry.MENU,)
    target=_group_map.setdefault(group['id'],{'id':group['id'],'title':group['title'],'menus':[]})
    target['menus'].extend(menus)
GROUPS=tuple(_group_map.values())
_routes_by_menu={}

def owner(operation):
    for group in GROUPS:
        for menu in group['menus']:
            if any(operation==pattern or pattern.endswith('/') and operation.startswith(pattern) for pattern in menu['operations']):
                return group['id'],menu['id']
    return 'platform','system'

def bind(routes):
    """Bind existing handlers once without moving state/model ownership."""
    _routes_by_menu.clear()
    for route in routes:
        if not hasattr(route,'endpoint') or not route.path.startswith('/api/'):continue
        operation=route.path.removeprefix('/api/')
        menus={owner(operation)[1]}
        for group in GROUPS:
            for menu in group['menus']:
                if any(not pattern.endswith('/') and route.path_regex.fullmatch('/api/'+pattern) for pattern in menu['operations']):menus.add(menu['id'])
        for menu in menus:_routes_by_menu.setdefault(menu,[]).append(route)

def dispatch(scope,parameters):
    from starlette.routing import Match
    operation=scope['path'].removeprefix('/api/')
    menu=owner(operation)[1]
    for route in _routes_by_menu.get(menu,()):
        match,child=route.matches(scope)
        if match==Match.FULL:return route,{**scope,**child}
    return None

def catalog(routes):
    from pydantic import TypeAdapter
    actions=[action for _,entry in MODULE_ENTRIES for action in (entry.actions() if hasattr(entry,'actions') else [])]
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
    """Collect small-menu routers through the finance and REA coordinators."""
    for _,entry in MODULE_ENTRIES:
        routers=getattr(entry,'ROUTERS',None) or (entry.router,)
        for router in routers:
            api.include_router(router)
            app.router.on_startup.extend(router.on_startup)
            app.router.on_shutdown.extend(router.on_shutdown)

    @api.get('/api/platform/modules')
    def modules():
        return {'items':[{'id':item['id'],'group':item['group'],'program':str(item['folder']),
            'data':[str(ROOT/path) for path in item.get('data',[])],
            'legacy_shared_code':item.get('legacy_shared_code',False),
            'resources':{name:(ROOT/path).is_file() for name,path in item.get('resources',{}).items()}}
            for item,_ in MODULE_ENTRIES]}

    @api.post('/api/platform/modules/prepare-detach')
    def prepare_detach(request:dict):
        from fastapi import HTTPException
        found=next((entry for item,entry in MODULE_ENTRIES if item['id']==request.get('id')),None)
        if found is None:raise HTTPException(404,'등록된 모듈이 없습니다.')
        if callback:=getattr(found,'busy_reason',None):
            if reason:=callback():raise HTTPException(409,reason)
        if callback:=getattr(found,'reserve_restart',None):callback()
        if callback:=getattr(found,'close',None):callback()
        return {'ready':True}
    bind(api.routes)
