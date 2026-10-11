export async function request<T>(path: string, body?: unknown): Promise<T> {
  if(body===undefined&&!/^state(?:\?|$)/.test(path))throw new Error('상태 조회는 통합 상태 선택자를 사용하세요.');
  const response = await fetch(`/api/${path}`, {
    method: body === undefined ? "GET" : "POST",
    cache: "no-store",
    headers:
      body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
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
