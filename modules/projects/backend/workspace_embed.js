// Adapt navigation only. The pinned original UI, API calls and stored records stay original.
(()=>{
 const config=window.platformWorkspace;
 let companyTeam;
 let nativeEngine;
 const annotateTeam=()=>{
  if(nativeEngine){for(const id of ['aiBadge','teamEngine','overviewModel']){const node=document.getElementById(id),text=(id==='teamEngine'?'공유 AI · ':'')+(nativeEngine.modelName||'모델 선택 전')+(id==='aiBadge'&&nativeEngine.modelState!=='ready'?' · '+({loading:'불러오는 중',failed:'연결 오류',idle:'미실행'}[nativeEngine.modelState]||'상태 확인 중'):'');if(node&&node.textContent!==text)node.textContent=text;}}
  if(!companyTeam?.staff)return;
  const names={...Object.fromEntries(companyTeam.staff.map(role=>[role.staff_id,role.name])),...(nativeEngine?.staffNames||{})};
  const rootName=document.querySelector('.org-root .role-name,.org-root strong');if(rootName&&names[companyTeam.manager_staff_id||nativeEngine?.managerId]&&rootName.textContent!==names[companyTeam.manager_staff_id||nativeEngine?.managerId])rootName.textContent=names[companyTeam.manager_staff_id||nativeEngine?.managerId];
  document.querySelectorAll('.recent-role,button[data-staff_id]:not(.team-card)').forEach(node=>{const key=node.dataset.staff_id||node.textContent.trim();if(names[key]&&node.textContent!==names[key])node.textContent=names[key]});
  document.querySelectorAll('#teamGrid .team-card').forEach(card=>{
   const role=companyTeam.staff.find(row=>row.staff_id===card.dataset.staff_id);if(!role)return;
   const heading=card.querySelector('.role-name');if(heading&&names[role.staff_id]&&heading.textContent!==names[role.staff_id])heading.textContent=names[role.staff_id];
   const title=names[role.staff_id]+' 최근 업무 보기';if(card.title!==title)card.title=title;
   const count=card.querySelector('.role-bottom b'),state=card.querySelector('.role-state');
   const countText='누적 완료 '+Number(role.completed||0).toLocaleString('ko-KR')+'건';
   if(count&&count.textContent!==countText)count.textContent=countText;
   if(state){const blocked=role.status==='failed'&&role.latest?.mode==='blocked';const text=blocked?'선행 실패로 미실행':'최근: '+({running:'실행 중',queued:'대기',completed:'완료',failed:'실패',idle:'배정 없음'}[role.status]||role.status);if(state.textContent!==text)state.textContent=text;if(blocked&&state.className!=='role-state idle')state.className='role-state idle';}
  });
  if(!document.getElementById('platform-team-state-help')){const help=document.createElement('p');help.id='platform-team-state-help';help.className='muted';help.textContent='상태는 최근 업무 기준이며, 누적 완료는 과거 업무를 포함합니다. 선행 실패로 미실행한 업무는 실제 검사 실패와 구분합니다.';document.getElementById('teamGrid')?.before(help)}
 };
 if(config.company){
  window.addEventListener('message',event=>{if(event.source===parent&&event.origin===location.origin&&event.data?.type==='hermes-engine-state'){nativeEngine=event.data;annotateTeam()}});
  const originalFetch=window.fetch;
  window.fetch=async(...args)=>{const response=await originalFetch(...args);if(String(args[0]?.url??args[0]).split('?')[0].endsWith('/api/admin/team')&&response.ok){try{companyTeam=await response.clone().json();annotateTeam()}catch{}}return response;};
  const observer=new MutationObserver(annotateTeam);const grid=document.getElementById('teamGrid');if(grid)observer.observe(grid,{childList:true,subtree:true});
 }
 const buttons=new Map(config.views.map(view=>[view,document.querySelector('[data-tab="'+view+'"]')]));
 if([...buttons.values()].some(button=>!button))throw Error('원본 화면 전환 버튼을 찾지 못했습니다.');
 const navigation=document.createElement('div');navigation.hidden=true;
 navigation.append(...buttons.values());document.body.append(navigation);
 document.querySelector('.side')?.remove();
 const shell=document.querySelector('.shell');if(shell)shell.replaceWith(...shell.childNodes);
 const notify=(type,view)=>parent.postMessage({type,view},location.origin);
 let markdownId=0;
 const renderMarkdown=()=>document.querySelectorAll('.bubble.ceo, #jobs .rowstatus').forEach(node=>{
  if(node.dataset.platformMarkdown)return;
  const copy=node.cloneNode(true);(copy.querySelector('.speaker')||copy.querySelector(':scope > b'))?.remove();copy.querySelectorAll('br').forEach(br=>br.replaceWith('\n'));
  const text=copy.textContent.trim().replace(/(^|\n)(\[[^\]\n]+\])\s+(#{1,6})\s/g,'$1$2\n\n$3 ');
  if(!/(^|\n)\s*(?:#|>|[-*+]\s|\d+\.\s)|\*\*|`|\[[^\]]+\]\([^)]+\)/.test(text))return;
  const id='platform-markdown-'+(++markdownId);node.dataset.platformMarkdown=id;
  const speaker=node.querySelector('.speaker')||node.querySelector(':scope > b');node.replaceChildren(...(speaker?[speaker]:[]));
  const output=document.createElement('div');output.id=id;output.textContent=text;node.append(output);
  parent.postMessage({type:'platform:markdown',id,text},location.origin);
 });
 const markdownObserver=new MutationObserver(renderMarkdown);markdownObserver.observe(document.body,{childList:true,subtree:true});renderMarkdown();
 let last='';
 const publish=()=>{const view=document.querySelector('.tab.on')?.id;if(config.views.includes(view)&&view!==last){last=view;notify('platform:workspace-view',view)}};
 const activate=view=>{buttons.get(view)?.click();publish()};
 document.addEventListener('click',event=>{
  if(event.target.closest?.('[data-tab="setup"]')){event.preventDefault();event.stopImmediatePropagation();notify('platform:model-settings')}
 },true);
 const observer=new MutationObserver(publish);document.querySelectorAll('.tab').forEach(node=>observer.observe(node,{attributes:true,attributeFilter:['class']}));
 window.addEventListener('message',event=>{
  if(event.origin!==location.origin||event.source!==parent)return;
  if(event.data?.type==='platform:markdown-result'&&/^platform-markdown-\d+$/.test(event.data.id)){const node=document.getElementById(event.data.id);if(node){const list=node.closest('#messages'),follow=list&&list.scrollHeight-list.scrollTop-list.clientHeight<80;node.innerHTML=event.data.html;if(follow)list.scrollTop=list.scrollHeight;}}
  if(event.data?.type==='platform:workspace-select'&&config.views.includes(event.data.view))activate(event.data.view);
 });
 notify('platform:workspace-ready');
})();
