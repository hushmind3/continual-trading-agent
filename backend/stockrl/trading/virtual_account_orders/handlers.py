"""가상계좌 · 주문 — existing API handlers."""
from __future__ import annotations
from api_context import APIRouter
from api_context import BaseModel
from api_context import Field
from api_context import FiniteJSONResponse
from api_context import HTTPException
from api_context import Literal
from api_context import runtime

router=APIRouter(default_response_class=FiniteJSONResponse)

class OrderRequest(BaseModel):
    currency:Literal["KRW","USD"]
    symbol:str
    action:Literal["BUY","SELL"]
    quantity:int=Field(gt=0,strict=True)


@router.post("/api/orders")
def paper_order(request:OrderRequest):
    try:return runtime.manual_order(request.symbol,request.currency,request.action,request.quantity)
    except (ValueError,RuntimeError) as exc:raise HTTPException(400,str(exc))

