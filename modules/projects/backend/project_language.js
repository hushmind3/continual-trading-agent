// Translate displayed text without rewriting the installed application's source.
(()=>{
 if(localStorage.getItem('projects.korean')!=='true')return;
 document.documentElement.lang='ko';
 const originals=new WeakMap(),translated=new Set(),cache=new Map();let timer,busy=false;
 const schedule=()=>{clearTimeout(timer);timer=setTimeout(update,800)};
 async function update(){
  if(busy)return;const nodes=[],attributes=[],texts=new Set(),walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){
   const node=walker.currentNode,parent=node.parentElement,value=node.nodeValue.trim();
   if(!parent||parent.closest('script,style,code,pre,textarea,[contenteditable]')||!parent.getClientRects().length||!value||value.length>6000||translated.has(value)||!/[A-Za-z]{3}/.test(value)||/[가-힣]/.test(value))continue;
   nodes.push(node);texts.add(value);if(texts.size>=100)break;
  }
  for(const element of document.querySelectorAll('[placeholder],[title],[aria-label]')){
   for(const name of ['placeholder','title','aria-label']){const value=element.getAttribute(name)?.trim();if(value&&value.length<=6000&&/[A-Za-z]{3}/.test(value)&&!/[가-힣]/.test(value)&&!translated.has(value)){attributes.push({element,name,value});texts.add(value)}}
   if(texts.size>=150)break;
  }
  if(!texts.size)return;busy=true;
  try{
   const response=await (window.__platformFetch||window.fetch.bind(window))('/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({operation:'projects/localize',payload:{texts:[...texts]}})});
   if(!response.ok)return;const data=await response.json();
   for(const [original,value] of Object.entries(data.translations||{})){if(original!==value){cache.set(original,value);translated.add(value)}}
   for(const node of nodes){const original=node.nodeValue.trim(),value=cache.get(original);if(value&&node.isConnected){originals.set(node,original);node.nodeValue=node.nodeValue.replace(original,value)}}
   for(const {element,name,value} of attributes){if(element.isConnected&&cache.has(value))element.setAttribute(name,cache.get(value))}
   if(data.state==='pending')timer=setTimeout(update,1500);
   if(data.state==='unavailable')document.documentElement.dataset.translationStatus='unavailable';
  }catch{}finally{busy=false}
 }
 new MutationObserver(schedule).observe(document.body,{childList:true,characterData:true,attributes:true,attributeFilter:['placeholder','title','aria-label'],subtree:true});schedule();
})();
