export function apiUrl(operation:string,payload:Record<string,unknown>={}) {
  return '/api?'+new URLSearchParams({operation,payload:JSON.stringify(payload)}).toString();
}
export const REQUEST_TIMEOUT_MS = 60_000;
export async function request<T>(path: string, body?: unknown, method: 'GET'|'POST' = 'POST', timeoutMs = path === 'champions/create' ? 1_800_000 : REQUEST_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
  const response = await fetch(method==='GET'?apiUrl(path,(body??{}) as Record<string,unknown>):'/api', {
    method,
    signal: controller.signal,
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...(method==='POST'?{body:JSON.stringify({operation:path,payload:body??{}})}:{}),
  });
  let data;
  try { data = await response.json(); }
  catch (error) {
    if (controller.signal.aborted) throw error;
    throw new Error(`서버의 JSON 응답을 읽을 수 없습니다. (HTTP ${response.status})`);
  }
  if (!response.ok && Array.isArray(data.detail)) {
    const errors=data.detail.filter((issue:unknown):issue is {loc?:unknown[];msg:string;type?:string}=>!!issue&&typeof issue==='object'&&typeof (issue as {msg?:unknown}).msg==='string').map((issue:{loc?:unknown[];msg:string;type?:string})=>{
      const field=issue.loc?.filter(part=>!['body','query','path'].includes(String(part))).join('.')||'입력값';
      const message=['int_type','int_parsing','int_from_float'].includes(issue.type??'')?'정수를 입력하세요.':issue.msg;
      return (field==='quantity'?'수량':field)+': '+message;
    });
    throw new Error(errors.join(' · ')||`요청 실패 (${response.status})`);
  }
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `요청 실패 (${response.status})`,
    );
  return data;
  } catch (error) {
    if (controller.signal.aborted) throw new Error('서버 응답 대기 시간이 초과됐습니다. 다음 상태 조회에서 다시 연결합니다.');
    throw error;
  } finally { clearTimeout(timer); }
}
