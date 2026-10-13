import json
import unittest
from urllib.parse import urlencode
from fastapi import APIRouter,FastAPI,HTTPException,Request
from fastapi.testclient import TestClient
from starlette.routing import Match,Route
from api_transport import FiniteJSONResponse
from api_transport import UnifiedAPI


class HTTPTransportTests(unittest.TestCase):
 def setUp(self):
  app=FastAPI();internal=APIRouter(default_response_class=FiniteJSONResponse)
  @internal.get('/api/state')
  def state(symbol:str=''):
   return {'symbol':symbol,'nested':[float('nan'),float('inf'),-float('inf'),1.5]}
  @internal.post('/api/echo')
  async def echo(request:Request):return await request.json()
  @internal.post('/api/blocked')
  def blocked():raise HTTPException(409,'실행 중인 작업 보존')
  app.router.routes.append(Route('/api',UnifiedAPI(),methods=['GET','POST']))
  @app.middleware('http')
  async def dispatch(request,call_next):
   envelope=await request.json();operation=envelope['operation'];parameters=envelope.get('payload',{})
   method='GET' if operation=='state' else 'POST'
   forwarded={**request.scope,'path':'/api/'+operation,'raw_path':('/api/'+operation).encode(),'method':method,
              'query_string':urlencode(parameters).encode() if method=='GET' else b''}
   for route in internal.routes:
    match,scope=route.matches(forwarded)
    if match==Match.FULL:
     forwarded.update(scope);request.state.api_dispatch=(route,forwarded,json.dumps(parameters,ensure_ascii=False).encode());break
   return await call_next(request)
  self.client=TestClient(app)
 def tearDown(self):self.client.close()
 def test_forwarded_query_and_non_finite_numbers_are_valid_json(self):
  response=self.client.post('/api',json={'operation':'state','payload':{'symbol':'^GSPC/한국'}})
  self.assertEqual(response.status_code,200)
  self.assertEqual(response.json(),{'symbol':'^GSPC/한국','nested':[None,None,None,1.5]})
  json.dumps(response.json(),allow_nan=False)
 def test_forwarded_json_body_preserves_nested_values(self):
  payload={'symbols':['AAPL','MSFT'],'options':{'enabled':True},'label':'한국'}
  response=self.client.post('/api',json={'operation':'echo','payload':payload})
  self.assertEqual(response.status_code,200);self.assertEqual(response.json(),payload)
 def test_forwarded_http_errors_keep_status_and_detail(self):
  response=self.client.post('/api',json={'operation':'blocked','payload':{}})
  self.assertEqual(response.status_code,409);self.assertEqual(response.json()['detail'],'실행 중인 작업 보존')

if __name__=='__main__':unittest.main()
