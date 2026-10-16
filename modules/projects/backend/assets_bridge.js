// Original application fetch calls use the host's existing single API gateway.
(()=>{const project=__PROJECT_ID__,original=window.fetch.bind(window);
 window.__platformFetch=original;
 window.fetch=async(input,init={})=>{
  const request=new Request(input,init),url=new URL(request.url,location.href);
  if(url.origin!==location.origin||url.pathname.startsWith('/assets/'))return original(request);
  const method=request.method,body=['GET','HEAD'].includes(method)?'':await request.text();
  const response=await original('/api',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({operation:'projects/invoke',payload:{id:project,path:url.pathname,
    query:url.search.slice(1),method,body,headers:Object.fromEntries(request.headers)}}),signal:request.signal});
  const result=await response.json();if(!response.ok)throw Error(result.detail||'프로젝트 API 연결 실패');
  const bytes=Uint8Array.from(atob(result.body),c=>c.charCodeAt(0));
  return new Response([204,205,304].includes(result.status)?null:bytes,{status:result.status,headers:result.headers});
 };
})();
