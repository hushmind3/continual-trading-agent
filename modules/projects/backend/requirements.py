"""Recognize concrete non-web requirements instead of reporting a model error."""
import json
import re
from .store import owned


class RequirementError(ValueError):
    def __init__(self, message, stage='needs_adapter'):
        super().__init__(message)
        self.stage = stage


def check(source):
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
