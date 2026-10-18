"""Build executable UI schemas from original argparse source without importing it."""
import ast
from pathlib import Path
import re
from .store import owned


def literal(node,default=None):
    try:return ast.literal_eval(node)
    except (ValueError,TypeError):return default


def parse(file):
    tree=ast.parse(file.read_text(encoding='utf-8-sig'));owners={};commands={};fields=[]
    parser_names={'ArgumentParser'}
    for item in ast.walk(tree):
        if isinstance(item,ast.ImportFrom) and item.module=='argparse':
            parser_names.update(alias.asname or alias.name for alias in item.names if alias.name=='ArgumentParser')
    nodes=sorted(ast.walk(tree),key=lambda node:getattr(node,'lineno',0))
    def owner(node):return owners.get(node.id) if isinstance(node,ast.Name) else None
    for node in nodes:
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Call):
            call=node.value;function=call.func;name=node.targets[0].id if isinstance(node.targets[0],ast.Name) else None
            if not name:continue
            if isinstance(function,(ast.Name,ast.Attribute)) and getattr(function,'attr',getattr(function,'id','')) in parser_names:
                owners[name]=();commands[()]=literal(next((item.value for item in call.keywords if item.arg=='description'),None),'실행')
            elif isinstance(function,ast.Attribute) and owner(function.value) is not None:
                parent=owner(function.value)
                if function.attr in ('add_subparsers','add_argument_group','add_mutually_exclusive_group'):owners[name]=parent
                elif function.attr=='add_parser' and call.args and isinstance(literal(call.args[0]),str):
                    path=(*parent,literal(call.args[0]));owners[name]=path;commands[path]=literal(next((item.value for item in call.keywords if item.arg=='help'),None),' '.join(path))
        if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Attribute) or node.func.attr!='add_argument':continue
        path=owner(node.func.value)
        if path is None:continue
        names=[literal(item) for item in node.args]
        if not names or any(not isinstance(item,str) for item in names):continue
        options={item.arg:item.value for item in node.keywords};action=literal(options.get('action'),'store')
        if action not in ('store','store_true','store_false','append'):continue
        positional=not names[0].startswith('-');flag=next((name for name in names if name.startswith('--')),names[0])
        key=literal(options.get('dest'),flag.lstrip('-').replace('-','_'))
        nargs=literal(options.get('nargs'));array=action=='append' or nargs in ('+','*') or isinstance(nargs,int) and nargs>1
        numeric=isinstance(options.get('type'),ast.Name) and options['type'].id in ('int','float')
        kind='boolean' if action in ('store_true','store_false') else 'array' if array else 'number' if numeric else 'text'
        choices=literal(options.get('choices'),[])
        if not isinstance(choices,(list,tuple)):choices=[]
        fields.append({'key':key,'flag':flag,'path':list(path),'positional':positional,'kind':kind,'integer':numeric and options['type'].id=='int','action':action,'nargs':nargs,
            'required':positional and nargs not in ('?','*') or bool(literal(options.get('required'),False)),
            'default':literal(options.get('default'),action=='store_false' if kind=='boolean' else None),
            'choices':list(choices),'description':literal(options.get('help'),'')})
    leaves=[path for path in commands if not any(len(other)>len(path) and other[:len(path)]==path for other in commands)]
    return [{'path':list(path),'title':commands[path] or ' '.join(path) or '실행','fields':[field for field in fields if tuple(field['path'])==path[:len(field['path'])]]} for path in leaves]


def candidates(source,spec=None):
    result=[]
    if spec and spec.get('script'):result.append(owned(source,spec['script']))
    if spec and spec.get('entry'):
        module=spec['entry'].split(':')[0].replace('.','/')
        for root in (source,source/'src'):
            result.extend((root/(module+'.py'),root/module/'__init__.py'))
    result.extend(source/name for name in ('main.py','cli.py','__main__.py','app.py'))
    readme=next((path for path in (source/'README.md',source/'readme.md') if path.is_file()),None)
    if readme:
        for relative in re.findall(r'(?<![\w/])([\w.-]+(?:/[\w.-]+)*\.py)\b',readme.read_text(encoding='utf8',errors='replace'))[:32]:
            try:result.append(owned(source,relative))
            except ValueError:continue
    seen=set()
    for file in result:
        if file.is_file() and file.resolve().is_relative_to(source.resolve()) and file.stat().st_size<512000 and file.resolve() not in seen:
            seen.add(file.resolve());yield file


def discover(source):
    for file in candidates(source):
        try:commands=parse(file)
        except (SyntaxError,UnicodeError):continue
        tree=ast.parse(file.read_text(encoding='utf-8-sig'))
        runnable=any(isinstance(item,ast.If) and isinstance(item.test,ast.Compare) and isinstance(item.test.left,ast.Name) and item.test.left.id=='__name__' for item in tree.body) or any(isinstance(item,ast.Expr) and isinstance(item.value,ast.Call) for item in tree.body)
        if commands and runnable:return {'kind':'python-cli','directory':'.','script':file.relative_to(source).as_posix()}


def describe(record):
    source=Path(record['active_source']);spec=record['adapter'];result=[]
    for file in candidates(source,spec if spec['kind']=='python-cli' else None):
        try:commands=parse(file)
        except (SyntaxError,UnicodeError):continue
        relative=file.relative_to(source).as_posix()
        for command in commands:
            item={**command,'title':file.stem+(' · '+command['title'] if command['title']!='실행' else ''),'id':relative+'::'+'/'.join(command['path']),'script':relative}
            module=spec.get('entry','').split(':')[0].replace('.','/')
            if spec['kind']=='python-cli' and module and relative in (module+'.py',module+'/__init__.py','src/'+module+'.py','src/'+module+'/__init__.py'):
                item.update(entry=spec['entry'],directory=spec.get('directory','.'))
            result.append(item)
    return {'commands':result,'source':'original-argparse','generated':True}


def arguments(command,values):
    if not isinstance(values,dict):raise ValueError('입력 항목을 확인하세요.')
    fields=command['fields'];known={item['key'] for item in fields}
    if set(values)-known:raise ValueError('원본 프로그램에 없는 입력 항목입니다.')
    arguments=[]
    for depth in range(len(command['path'])+1):
        group=[item for item in fields if len(item['path'])==depth]
        for field in sorted(group,key=lambda item:item['positional']):
            value=values.get(field['key'],field['default']);flag=field['flag']
            if field['kind']=='boolean':
                if not isinstance(value,bool):raise ValueError(field['key']+' 값은 켜기/끄기입니다.')
                if value==(field['action']=='store_true'):arguments.append(flag)
                continue
            if value is None or value=='' or value==[]:
                if field['required']:raise ValueError(field['key']+' 항목을 입력하세요.')
                continue
            items=value if field['kind']=='array' else [value]
            if not isinstance(items,list) or len(items)>128:raise ValueError(field['key']+' 목록이 올바르지 않습니다.')
            if isinstance(field['nargs'],int) and len(items)!=field['nargs']:raise ValueError(field['key']+' 항목 수를 확인하세요.')
            for item in items:
                if not isinstance(item,(str,int,float)) or isinstance(item,bool):raise ValueError('문자 또는 숫자를 입력하세요.')
                if field['integer']:
                    try:
                        if str(int(item))!=str(item):raise ValueError()
                    except (ValueError,TypeError):raise ValueError(field['key']+' 항목에 정수를 입력하세요.') from None
                elif field['kind']=='number':
                    try:float(item)
                    except (ValueError,TypeError):raise ValueError(field['key']+' 항목에 숫자를 입력하세요.') from None
                if field['choices'] and str(item) not in [str(choice) for choice in field['choices']]:raise ValueError(field['key']+' 선택 값을 확인하세요.')
                if field['positional'] and str(item).startswith('-'):raise ValueError('위치 인수는 대시로 시작할 수 없습니다.')
            if not field['positional']:
                if field['action']=='append':
                    for item in items:arguments.extend([flag,str(item)])
                    continue
                if len(items)==1:arguments.append(flag+'='+str(items[0]));continue
                arguments.append(flag)
            arguments.extend(str(item) for item in items)
        if depth<len(command['path']):arguments.append(command['path'][depth])
    return arguments


def execute(record,command_id,values):
    command=next((item for item in describe(record)['commands'] if item['id']==command_id),None)
    if not command:raise ValueError('자동 탐지한 실행 기능이 아닙니다.')
    from .runtime import run_cli
    spec={'kind':'python-cli','directory':command.get('directory','.') }
    spec.update({'entry':command['entry']} if command.get('entry') else {'script':command['script']})
    return run_cli({**record,'adapter':spec},arguments(command,values))
