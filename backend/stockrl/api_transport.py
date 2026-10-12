"""JSON rendering and forwarding for the existing single HTTP gateway."""
import math
from fastapi.responses import JSONResponse


def finite_json(value):
    if isinstance(value,float) and not math.isfinite(value):return None
    if isinstance(value,dict):return {key:finite_json(item) for key,item in value.items()}
    if isinstance(value,(list,tuple)):return [finite_json(item) for item in value]
    return value


class FiniteJSONResponse(JSONResponse):
    def render(self,content):
        return super().render(finite_json(content))


class UnifiedAPI:
    async def __call__(self,scope,receive,send):
        route,forwarded,body=scope['state']['api_dispatch']
        received=False
        async def payload():
            nonlocal received
            if received:return await receive()
            received=True
            return {'type':'http.request','body':body,'more_body':False}
        await route.handle(forwarded,payload,send)
