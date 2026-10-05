export async function request<T>(path:string,body?:unknown,signal?:AbortSignal):Promise<T> {
  const timeout=AbortSignal.timeout(body===undefined?12000:30000);
  const response=await fetch(path,{method:body===undefined?'GET':'POST',cache:'no-store',signal:signal?AbortSignal.any([signal,timeout]):timeout,
    ...(body===undefined?{}:{headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})});
  const text=await response.text();
  let value:Record<string,unknown>;
  try {value=JSON.parse(text);} catch {throw new Error(`서버 응답을 읽을 수 없습니다 (${response.status})`);}
  if(!response.ok||value.ok===false||typeof value.error==='string'&&value.error) throw new Error(String(value.error??value.message??`요청 실패 (${response.status})`));
  return value as T;
}
