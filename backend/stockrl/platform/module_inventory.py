"""Installed source inventory and static module details; never import listed modules."""
import ast
import hashlib
import importlib.metadata
import os
import tokenize
from functools import lru_cache
from pathlib import Path


def source_definition(path, framework, module):
    item={'id':framework+':'+module,'path':framework+'/'+module.replace('.','/')+'.py',
          'framework':framework,'source_path':str(path),'functions':[],'signatures':{},
          'parameters':{},'keyword_contracts':{},'imports':[],'calls':[]}
    try:
        with tokenize.open(path) as stream:tree=ast.parse(stream.read())
    except (UnicodeError,SyntaxError) as exc:
        item['description']=str(exc);return item
    item['description']=ast.get_docstring(tree)
    def arguments(node, name):
        item['keyword_contracts'][name]={'variadic':node.args.kwarg is not None,
            'positional_only':[arg.arg for arg in node.args.posonlyargs if arg.arg not in ('self','cls')],
            'instance':bool(node.args.args and node.args.args[0].arg=='self')}
        positional=[*node.args.posonlyargs,*node.args.args]
        defaults=[None]*(len(positional)-len(node.args.defaults))+node.args.defaults
        return [{'name':arg.arg,'annotation':ast.unparse(arg.annotation) if arg.annotation else None,
                 'required':default is None,'default':ast.unparse(default) if default is not None else None}
                for arg,default in [*zip(positional,defaults),*zip(node.args.kwonlyargs,node.args.kw_defaults)]
                if arg.arg not in ('self','cls')]
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom):item['imports'].append('.'*node.level+(node.module or ''))
        elif isinstance(node,ast.Import):item['imports'].extend(alias.name for alias in node.names)
        elif isinstance(node,ast.Call):
            item['calls'].append(ast.unparse(node.func))
            if isinstance(node.func,ast.Name) and node.func.id in ('finrlx','finrl_file') and node.args and isinstance(node.args[0],ast.Constant):
                item['imports'].append(('src.' if node.func.id=='finrlx' else 'finrl.')+str(node.args[0].value).removesuffix('.py').replace('/','.'))
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            item['functions'].append(node.name);item['signatures'][node.name]=ast.unparse(node.args)
            item['parameters'][node.name]=arguments(node,node.name)
        elif isinstance(node,ast.ClassDef):
            item['functions'].append(node.name)
            for child in node.body:
                if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    name=node.name+'.'+child.name;item['functions'].append(name)
                    item['signatures'][name]=ast.unparse(child.args);item['parameters'][name]=arguments(child,name)
    item['imports']=sorted(set(item['imports']));item['calls']=sorted(set(item['calls']))
    return item


@lru_cache(maxsize=1)
def module_inventory():
    from .framework_operations import source_catalog
    rows={};paths=set()
    def path_key(path):return os.path.normcase(os.path.abspath(path))
    for item in source_catalog():
        name=item['id'].split(':',1)[1];framework=item['framework']
        group='finrl' if framework in ('FinRL','SB3','SB3-Contrib') else 'finrl_trading' if framework=='FinRL-X' else 'extensions'
        if framework=='stockrl':
            group=next((value for prefix,value in [('finrl.','finrl'),('finrl_trading.','finrl_trading'),('trading.','trading'),('management.','management')] if name.startswith(prefix)),group)
        rows[item['id']]={'id':item['id'],'name':name,'framework':framework,'group':group,'source_path':item['source_path'],'package':framework}
        paths.add(path_key(item['source_path']))
    for distribution in importlib.metadata.distributions():
        metadata=distribution.metadata;package=metadata.get('Name','');version=metadata.get('Version','')
        summary=metadata.get('Summary','');requires=metadata.get_all('Requires-Dist') or []
        family=package.lower().replace('_','-')
        group='finrl' if family in ('finrl','stable-baselines3','sb3-contrib') else 'finrl_trading' if family=='finrl-trading' else 'management'
        for file in distribution.files or ():
            if '..' in file.parts or file.suffix not in ('.py','.pyd','.so'):continue
            path=distribution.locate_file(file);key=path_key(path)
            if key in paths:continue
            paths.add(key)
            parts=list(file.parts);parts[-1]=parts[-1].split('.')[0]
            if parts[-1]=='__init__':parts.pop()
            name='.'.join(parts)
            ident='Python:'+name+':'+hashlib.sha256(key.encode()).hexdigest()[:12]
            rows[ident]={'id':ident,'name':name,'framework':'Python','group':group,
                'source_path':str(path),'package':package,'version':version,
                'description':summary,'requires':requires}
    return rows


def module_menus():
    return [{key:row[key] for key in ('id','name','framework','group','package')} for row in module_inventory().values()]


def module_source_path(ident):
    return Path(module_inventory()[ident]['source_path'])


def module_info(ident):
    row=module_inventory()[ident];path=Path(row['source_path'])
    if row['framework']!='Python':
        from .framework_operations import catalog
        item=next(item for item in catalog()['items'] if item['id']==ident)
    elif path.is_file() and path.suffix=='.py':
        item=source_definition(path,'Python',row['name'])
        item.update(status='미연결',reason='설치된 소스 목록입니다. 공개 실행 API와 실행 성공은 확인하지 않았습니다.',dependencies=item['imports'],actions=[],verified_functions=[])
    else:
        item={'functions':[],'signatures':{},'parameters':{},'dependencies':[],'calls':[],
              'actions':[],'verified_functions':[],'status':'미연결',
              'reason':'컴파일된 모듈 또는 설치 기록의 파일입니다. 실행 검증은 하지 않았습니다.'}
    return {**item,**row,'description':item.get('description') or row.get('description'),'file_exists':path.is_file()}
