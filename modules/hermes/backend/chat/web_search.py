"""Keyless DDGS adapter for the existing native Hermes web provider registry."""

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
        def supports_extract(self): return False
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
