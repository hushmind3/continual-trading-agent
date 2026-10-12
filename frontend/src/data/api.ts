export function apiUrl(operation:string,payload:Record<string,unknown>={}) {
  return '/api?'+new URLSearchParams({operation,payload:JSON.stringify(payload)}).toString();
}
export async function request<T>(path: string, body?: unknown, method: 'GET'|'POST' = 'POST'): Promise<T> {
  const response = await fetch(method==='GET'?apiUrl(path,(body??{}) as Record<string,unknown>):'/api', {
    method,
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...(method==='POST'?{body:JSON.stringify({operation:path,payload:body??{}})}:{}),
  });
  const data = await response
    .json()
    .catch(() => ({ detail: "서버 응답을 읽을 수 없습니다." }));
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `요청 실패 (${response.status})`,
    );
  return data;
}
