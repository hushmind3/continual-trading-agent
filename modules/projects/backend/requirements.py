"""Recognize concrete non-web requirements instead of reporting a model error."""
import json
import re
from .store import owned


class RequirementError(ValueError):
    def __init__(self, message, stage='needs_adapter'):
        super().__init__(message)
        self.stage = stage


def check(source):
    # Documentation/research repositories are not broken applications. Do not
    # offer model conversion as though the original program were included.
    manifests=('package.json','pyproject.toml','Cargo.toml','go.mod','CMakeLists.txt','Makefile')
    folders=('src','app','backend','frontend','bin')
    code=('*.py','*.js','*.ts','*.cpp','*.c','*.cs','*.rs','*.exe','*.sln','*.html')
    has_tools=any(any((source/folder).glob(pattern)) for folder in ('scripts','analysis','windows','tools','ghidra_scripts') for pattern in ('*.py','*.ps1','*.sh','*.java'))
    if not has_tools and (source/'docs').is_dir() and any((source/'docs').glob('*.md')) and not any((source/name).exists() for name in (*manifests,*folders)) and not any(any(source.glob(pattern)) for pattern in code):
        raise RequirementError('실행 프로그램이 포함되지 않은 문서·분석 자료 저장소입니다. 설치할 앱·화면·모델 파일은 없으며 내려받은 자료는 폴더 열기로 읽을 수 있습니다.',stage='not_app')
    for solution in source.glob('*.sln'):
        for relative in re.findall(r'"([^"\r\n]+\.csproj)"', solution.read_text(encoding='utf-8-sig')):
            project = owned(source, relative.replace('\\', '/'))
            if project.is_file() and ('<OutputType>WinExe</OutputType>' in project.read_text(encoding='utf8')):
                raise RequirementError('Windows 데스크톱 앱입니다. 현재 설치기에 .NET 데스크톱 빌드·실행 어댑터가 없어 연결하지 못했습니다. 웹앱이나 모델 오류가 아닙니다. 내려받은 원본은 보존했습니다.')
    package, example = source / 'package.json', source / 'example.json'
    if package.is_file() and example.is_file():
        data = json.loads(package.read_text(encoding='utf8'))
        config = json.loads(example.read_text(encoding='utf8'))
        if 'misskey-reversi' in data.get('dependencies', {}) and {'host', 'i'} <= config.keys():
            raise RequirementError('Misskey 계정용 봇입니다. 실제 Misskey 서버 주소(host)와 봇 토큰(i)을 config.json에 설정해야 하며 Node 상주 실행 어댑터도 필요합니다. 로컬 대화 모델로 실행하는 앱이 아닙니다. 소스는 보존했습니다.')
