"""Public GitHub repository discovery. No shell interpolation or embedded tokens."""
import json
import re
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def repository(value):
    value = str(value).strip().rstrip('/').removesuffix('.git')
    if value.startswith('https://'):
        parsed = urlsplit(value)
        if parsed.netloc.lower() != 'github.com' or parsed.query or parsed.fragment:
            raise ValueError('https://github.com/소유자/저장소 주소를 입력하세요.')
        value = parsed.path.strip('/')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value):
        raise ValueError('GitHub 저장소 주소 또는 소유자/저장소를 입력하세요.')
    if any(part in ('.', '..') for part in value.split('/')):
        raise ValueError('잘못된 저장소 주소입니다.')
    return value


def github(path):
    request = Request('https://api.github.com/' + path, headers={
        'Accept': 'application/vnd.github+json', 'User-Agent': 'Local-Project-Platform'})
    try:
        with urlopen(request, timeout=25) as response:
            return json.load(response)
    except HTTPError as exc:
        if exc.code in (403, 429):
            raise ValueError('GitHub 검색 한도에 도달했습니다. 잠시 뒤 다시 시도하거나 주소로 등록하세요.') from exc
        raise ValueError(f'GitHub 요청 실패 (HTTP {exc.code}). 공개 저장소 주소를 확인하세요.') from exc
    except URLError as exc:
        raise ValueError('GitHub에 연결하지 못했습니다. 인터넷 연결을 확인하세요.') from exc


def search(query, page=1):
    query = str(query).strip()
    if not query or len(query) > 256:
        raise ValueError('검색어를 1~256자로 입력하세요.')
    result = github('search/repositories?' + urlencode({'q': query, 'per_page': 12, 'page': max(1, min(10, int(page)))}))
    return {'total': result['total_count'], 'incomplete': result.get('incomplete_results', False),
        'items': [{'repository': item['full_name'], 'url': item['html_url'], 'description': item.get('description') or '',
                   'stars': item['stargazers_count'], 'language': item.get('language') or '',
                   'updated_at': item['updated_at']} for item in result['items']]}
