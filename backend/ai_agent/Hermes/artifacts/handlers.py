"""Preview local text reports through the Hermes submenu, never execute them."""
import json
from pathlib import Path
from urllib.parse import unquote,urlsplit
from fastapi import APIRouter,HTTPException
from stockrl import ROOT

router=APIRouter(prefix='/api/ai_agent/Hermes')
HOME=ROOT/'runtime/ai_agent/Hermes'
TEXT=frozenset({'.md','.txt','.json','.csv','.log','.py','.ts','.tsx','.js','.jsx','.yaml','.yml','.toml','.html','.css'})
LIMIT=1024*1024


def preview(path,workspace):
    raw=unquote(str(path))
    if raw.startswith(('\\\\','//')):raise ValueError('네트워크 경로는 문서 미리보기 대상이 아닙니다.')
    if raw.startswith('file:'):
        parsed=urlsplit(raw)
        if parsed.netloc and parsed.netloc!='localhost':raise ValueError('로컬 문서만 열 수 있습니다.')
        raw=parsed.path
        if len(raw)>2 and raw[0]=='/' and raw[2]==':':raw=raw[1:]
    root=Path(workspace).resolve();file=Path(raw).expanduser()
    file=(file if file.is_absolute() else root/file).resolve()
    artifact_root=(HOME/'artifacts').resolve()
    if not file.is_relative_to(root) and not file.is_relative_to(artifact_root):raise ValueError('작업 폴더 밖의 문서는 열 수 없습니다.')
    lowered=[part.lower() for part in file.parts]
    if any(part in ('.git','.venv','node_modules') for part in lowered) or file.name.lower() in ('platform-settings.json','credentials.json','auth.json','config.yaml') or any(left=='configs' and right=='local' for left,right in zip(lowered,lowered[1:])):
        raise ValueError('설치·인증·개인 설정 파일은 문서 미리보기 대상이 아닙니다.')
    if file.suffix.lower() not in TEXT:raise ValueError('텍스트·Markdown 문서를 선택하세요.')
    if not file.is_file():raise FileNotFoundError('문서 파일이 없습니다.')
    size=file.stat().st_size
    with file.open('rb') as stream:content=stream.read(LIMIT+1)
    return {'path':str(file),'name':file.name,'format':file.suffix.lower(),'bytes':size,
        'content':content[:LIMIT].decode('utf-8-sig',errors='replace'),'truncated':len(content)>LIMIT}


@router.get('/artifact')
def artifact(path:str):
    try:
        settings=HOME/'platform-settings.json'
        cfg=json.loads(settings.read_text(encoding='utf8')) if settings.exists() else {}
        return preview(path,cfg.get('workspace') or ROOT)
    except FileNotFoundError as exc:raise HTTPException(404,str(exc)) from exc
    except (ValueError,OSError) as exc:raise HTTPException(400,str(exc)) from exc


UPLOADS=HOME/'artifacts'/'uploads'
UPLOAD_LIMIT=8*1024*1024

def uploaded_paths(values):
    if not isinstance(values,list) or len(values)>8:raise ValueError('첨부 파일은 최대 8개입니다.')
    paths=[]
    for value in values:
        file=Path(str(value)).resolve()
        if not file.is_relative_to(UPLOADS.resolve()) or not file.is_file():raise ValueError('등록되지 않았거나 없는 첨부 파일입니다.')
        paths.append(str(file))
    return paths

@router.post('/artifact/upload')
def upload(request:dict):
    import base64,binascii,uuid
    name=str(request.get('name') or '').replace('\\','/').rsplit('/',1)[-1]
    if not name or name in ('.','..') or any(c in name for c in '<>:"|?*') or any(ord(c)<32 for c in name):raise HTTPException(400,'올바른 파일 이름을 선택하세요.')
    content=request.get('content')
    if not isinstance(content,str) or len(content)>((UPLOAD_LIMIT+2)//3)*4:raise HTTPException(413,'파일당 최대 8 MiB까지 첨부할 수 있습니다.')
    try:data=base64.b64decode(content,validate=True)
    except (ValueError,binascii.Error) as exc:raise HTTPException(400,'파일 데이터를 읽을 수 없습니다.') from exc
    if len(data)>UPLOAD_LIMIT:raise HTTPException(413,'파일당 최대 8 MiB까지 첨부할 수 있습니다.')
    folder=UPLOADS/uuid.uuid4().hex
    folder.mkdir(parents=True)
    file=folder/name
    try:file.write_bytes(data)
    except OSError as exc:raise HTTPException(400,'첨부 파일을 저장하지 못했습니다.') from exc
    return {'name':name,'path':str(file.resolve()),'bytes':len(data)}
