"""REA-owned finite JSON response handling."""
import math
from fastapi.responses import JSONResponse
def finite(value):
 if isinstance(value,float) and not math.isfinite(value):return None
 if isinstance(value,dict):return {k:finite(v) for k,v in value.items()}
 if isinstance(value,(list,tuple)):return [finite(v) for v in value]
 return value
class FiniteJSONResponse(JSONResponse):
 def render(self,content):return super().render(finite(content))


from fastapi.responses import FileResponse as StarletteFileResponse
from starlette.datastructures import Headers
import asyncio,os,stat
class FileResponse(StarletteFileResponse):
 """Transfer stable files by path inside IPC; retain the library's range/background behavior."""
 async def __call__(self,scope,receive,send):
  if 'http.response.pathsend' not in scope.get('extensions',{}) or Headers(scope=scope).get('range') or self.background is not None:
   return await super().__call__(scope,receive,send)
  info=self.stat_result or await asyncio.to_thread(os.stat,self.path)
  if not stat.S_ISREG(info.st_mode):raise RuntimeError('응답 경로가 파일이 아닙니다.')
  self.set_stat_headers(info)
  await send({'type':'http.response.start','status':self.status_code,'headers':self.raw_headers})
  if scope['method'].upper()=='HEAD':await send({'type':'http.response.body','body':b''})
  else:await send({'type':'http.response.pathsend','path':str(self.path)})
