// Adapt navigation only. The pinned original UI, API calls and stored records stay original.
(()=>{
 const config=window.platformWorkspace;
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
