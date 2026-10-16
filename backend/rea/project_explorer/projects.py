"""Browse physical REA output projects; never execute extracted programs."""
from pathlib import Path
import json,os,re
from stockrl import ROOT
OUTPUT=ROOT/'runtime/rea/project_explorer/projects'

def _project(identifier):
    if not re.fullmatch(r'[a-f0-9]{32}',identifier or ''):raise ValueError('저장 프로젝트를 선택하세요.')
    for entry in catalog()['items']:
        if entry['id']==identifier:
            folder=_inside(OUTPUT,Path(entry['folder']).name)
            if folder.is_dir():return folder
    raise ValueError('저장 프로젝트가 없습니다.')


def catalog():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    records=[]
    for file in OUTPUT.glob('*/project.json'):
        try:record=json.loads(file.read_text(encoding='utf8'))
        except (OSError,ValueError):continue
        if not isinstance(record,dict) or not all(isinstance(record.get(key),str) for key in ('id','name','folder','created_at','state')):continue
        if not re.fullmatch(r'[a-f0-9]{32}',record['id']):continue
        records.append(record)
    return {'items':sorted(records,key=lambda item:item['created_at'],reverse=True)}

def _inside(folder,relative):
    if not isinstance(relative,str):raise ValueError('파일 경로를 선택하세요.')
    result=(folder/relative).resolve()
    if not result.is_relative_to(folder.resolve()):raise ValueError('프로젝트 내부 경로만 열 수 있습니다.')
    return result

def tree(identifier,path=''):
    folder=_project(identifier);directory=_inside(folder,path)
    if not directory.is_dir():raise ValueError('저장 폴더를 선택하세요.')
    items=[{'name':item.name,'path':item.relative_to(folder).as_posix(),'folder':item.is_dir(),
            'bytes':item.stat().st_size if item.is_file() else None}
           for item in directory.iterdir() if not item.is_symlink()]
    return {'items':sorted(items,key=lambda item:(not item['folder'],item['name'].lower())),'path':path}

def read_file(identifier,path):
    file=_inside(_project(identifier),path)
    if not file.is_file():raise ValueError('저장 파일을 선택하세요.')
    text=file.suffix.lower() in {'.md','.txt','.json','.js','.jsx','.mjs','.cjs','.ts','.tsx','.html','.css','.map','.c','.h','.cpp','.yaml','.yml','.xml','.svg','.ini','.toml'}
    if not text:return {'binary':True,'bytes':file.stat().st_size,'content':'바이너리 원본입니다. 저장 폴더에서 확인하세요.'}
    with file.open('rb') as stream:preview=stream.read(256*1024)
    return {'binary':False,'bytes':file.stat().st_size,'preview_bytes':len(preview),
            'truncated':file.stat().st_size>len(preview),'content':preview.decode('utf8',errors='replace')}

def open_folder(identifier):
    folder=_project(identifier)
    if os.name!='nt':raise RuntimeError('폴더 열기는 현재 Windows 로컬 환경을 사용합니다.')
    os.startfile(str(folder))
    return {'path':str(folder)}

