"""Keyless search and public page extraction in the native Hermes registry."""

from html.parser import HTMLParser


class PageText(HTMLParser):
    """Read document text without scripts, CSS or hidden template payloads."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.title, self.hidden = [], [], []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'template', 'noscript'):
            self.hidden.append(tag)
        if tag == 'title': self.in_title = True
        if tag in ('p', 'div', 'br', 'li', 'section', 'h1', 'h2', 'h3'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if self.hidden and tag == self.hidden[-1]: self.hidden.pop()
        if tag == 'title': self.in_title = False

    def handle_data(self, data):
        if self.hidden: return
        if self.in_title: self.title.append(data)
        else: self.parts.append(data)


async def extract_pages(urls, **kwargs):
    import asyncio
    import httpx
    from urllib.parse import urljoin
    from plugins.web._common import document, page_error
    from tools.url_safety import async_is_safe_url

    async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
        async def read(url):
            try:
                target = url
                for _ in range(6):
                    if not await async_is_safe_url(target):
                        raise ValueError('접근할 수 없는 공개 웹 주소입니다.')
                    async with client.stream('GET', target) as response:
                        if response.is_redirect:
                            target = urljoin(target, response.headers['location'])
                            continue
                        response.raise_for_status()
                        content_type = response.headers.get('content-type', '').lower()
                        if not any(kind in content_type for kind in ('html', 'text/', 'json', 'xml')):
                            raise ValueError('문서 본문을 읽을 수 없는 파일 형식입니다.')
                        chunks, size = [], 0
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > 2 * 1024 * 1024:
                                raise ValueError('본문이 너무 큽니다. 브라우저로 필요한 부분을 확인하세요.')
                            chunks.append(chunk)
                        text = b''.join(chunks).decode(response.encoding or 'utf-8', errors='replace')
                        title = target
                        if 'html' in content_type:
                            parser = PageText()
                            parser.feed(text)
                            title = ''.join(parser.title).strip() or target
                            text = '\n'.join(' '.join(line.split()) for line in ''.join(parser.parts).splitlines() if line.strip())
                        if not text.strip():
                            raise ValueError('읽을 본문이 없습니다. 동적 페이지는 브라우저 도구로 확인하세요.')
                        return document(url, title, text, source_url=target)
                raise ValueError('웹 주소 이동이 너무 많습니다.')
            except Exception as exc:
                return page_error(url, '본문 읽기 실패: ' + str(exc)[:250])
        return await asyncio.gather(*(read(url) for url in urls))

def register():
    from agent.web_search_registry import get_provider, register_provider
    from agent.web_search_provider import WebSearchProvider
    if get_provider('ddgs') is not None: return
    class DDGSSearch(WebSearchProvider):
        name = 'ddgs'
        def is_available(self):
            try:
                import ddgs
                return True
            except ImportError:
                return False
        def supports_extract(self): return True
        async def extract(self, urls, **kwargs):
            return await extract_pages(urls, **kwargs)
        def search(self, query, limit=5):
            from ddgs import DDGS
            from plugins.web._common import search_ok, search_fail, title_hit
            try:
                rows=DDGS(timeout=10).text(query,max_results=limit)
                hits=[title_hit(r.get('title',''),r.get('href') or r.get('url',''),r.get('body') or r.get('description',''),i+1) for i,r in enumerate(rows)]
                return search_ok(hits) if hits else search_fail('검색 결과가 없습니다. 검색어를 바꾸거나 브라우저로 확인하세요.')
            except Exception as exc:
                return search_fail('웹 검색 실패: '+str(exc)[:350])
    register_provider(DDGSSearch())
