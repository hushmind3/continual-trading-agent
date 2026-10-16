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
