import {useEffect,useState} from 'react';
import {request} from '@platform/data/api';
import {Button,Input,ErrorMessage,Status} from '@platform/ui/Primitives';
import {ChatPane} from './ChatPane';
import {MeetingsPane} from './MeetingsPane';
import {JobsPane} from './JobsPane';
import {BusinessPane} from './BusinessPane';
import {useWorkspace} from './useWorkspace';
export function Workspace({projectId}:{projectId:string}){
 const {data,harness,error,busy,login,authenticate,action,refresh,reportError}=useWorkspace(projectId),[tab,setTab]=useState('chat'),[code,setCode]=useState(''),[requestId,setRequestId]=useState(''),[draft,setDraft]=useState('');
 useEffect(()=>{if(requestId&&data?.requests.some(r=>r.id===requestId&&r.status!=='working'))setRequestId('')},[data,requestId]);
 const active=['waiting','running'].includes(harness.state||''),working=!!requestId||(data?.requests.some(r=>r.status==='working')||false),meeting=data?.meetings.find(m=>m.status==='running');
 const phase=active?`${harness.phase?.role||'앱 모델'} · ${harness.state==='waiting'?'실행 차례 대기':harness.phase?.label||'모델 요청 처리'}${harness.phase?.started_at?' · '+Math.max(0,Math.floor(Date.now()/1000-harness.phase.started_at))+'초':''}`:meeting?'회의 · 다음 발언 준비 중':working?'CEO · 요청 처리 중':'요청 대기';
 const latestOwner=data?.ceo.messages.filter(m=>m.speaker==='owner').at(-1)?.body||'';
 const onDecision=(id:string,approve:boolean)=>action('/api/admin/ventures/'+encodeURIComponent(id)+'/decision',{approve});
 async function send(text:string){const result=await action<{request_id:string}>('/api/admin/ceo/chat/submit',{message:text});setRequestId(result.request_id)}
 if(login)return <section className="mx-auto flex w-full max-w-md flex-col gap-4 p-6"><h2 className="font-semibold">원본 앱 관리자 연결</h2><p className="text-sm text-slate-500">로컬 자동 로그인을 사용할 수 없어 원본 관리자 코드가 필요합니다.</p><Input aria-label="관리자 코드" type="password" value={code} onChange={e=>setCode(e.target.value)}/><Button tone="primary" onClick={()=>void authenticate(code)}>연결</Button><ErrorMessage message={error}/></section>;
 return <section className="flex min-h-0 flex-1 flex-col bg-white" aria-label="Project Zero 경영실"><nav aria-label="경영실 화면" className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-3 py-2"><div className="flex min-w-0 gap-1 overflow-x-auto">{[['chat','대화'],['meetings','회의'],['jobs','업무'],['business','사업안']].map(([id,label])=><Button key={id} variant="ghost" tone={tab===id?'primary':'neutral'} aria-current={tab===id?'page':undefined} onClick={()=>setTab(id)}>{label}{id==='meetings'&&meeting?' · 진행 중':''}</Button>)}</div><div className="flex min-w-0 items-center gap-2">{data?.model_transport==='native_api'&&<span className="text-xs text-slate-500">원본 모델 API · 텍스트 전용</span>}<Status tone={active||working||meeting?'warn':'idle'}><span role="status" className="truncate">{phase}</span></Status>{active&&<Button variant="ghost" tone="danger" onClick={()=>{void request('projects/harness',{id:projectId,action:'stop'}).then(refresh).catch(reportError)}}>현재 실행 중지</Button>}</div></nav>
 <ErrorMessage message={error||harness.error||''}/>
 {!data?<p className="p-6 text-sm text-slate-500">원본 앱의 작업 기록을 불러오는 중…</p>:<>
 {tab==='chat'&&<div className="grid min-h-0 flex-1 xl:grid-cols-4"><div className="flex min-h-0 min-w-0 flex-col xl:col-span-3"><ChatPane meetings={data.meetings} preparing={data.plan_preparing||[]} onPrepare={id=>action('/api/admin/platform/meeting-plans/'+encodeURIComponent(id)+'/prepare',{})} plans={data.plans||[]} onPlanDecision={(id,approve)=>action('/api/admin/platform/meeting-plans/'+encodeURIComponent(id)+'/decision',{approve})} draft={draft} setDraft={setDraft} messages={data.ceo.messages} working={working} busy={busy} phase={phase} onSend={send} onJobs={()=>setTab('jobs')} onMeeting={()=>setTab('meetings')}/></div><aside className="hidden min-h-0 overflow-auto border-l border-slate-200 bg-slate-50 xl:block"><BusinessPane ventures={data.ventures} active={data.active_product} busy={busy} onDecision={onDecision} compact/><div className="border-t border-slate-200 p-5"><h2 className="mb-3 text-sm font-semibold">회의 현황</h2><p className="text-xs leading-6 text-slate-500">{meeting?`${meeting.topic} · 전문가 발언 ${meeting.minutes.length}/5 저장됨`:data.meetings.length?`최근 회의 · ${data.meetings[0].status==='completed'?'종합 완료':'중단됨'}`:'아직 회의를 시작하지 않았습니다.'}</p><Button variant="ghost" onClick={()=>setTab('meetings')}>발언·결론 보기</Button></div></aside></div>}
 {tab==='meetings'&&<MeetingsPane includeEngineContext={data.include_engine_context} onContext={value=>action('/api/admin/platform/discussion-context',{include_engine_context:value})} meetings={data.meetings} harness={harness} initialTopic={data.ventures.find(v=>v.status==='pending')?.name||latestOwner} busy={busy} onStart={topic=>action('/api/admin/meetings',{topic})}/>}
 {tab==='jobs'&&<JobsPane jobs={data.jobs} team={data.team.roles} harness={harness}/>}
 {tab==='business'&&<div className="min-h-0 flex-1 overflow-auto"><div className="mx-auto max-w-3xl"><BusinessPane ventures={data.ventures} active={data.active_product} busy={busy} onDecision={onDecision}/></div></div>}
 </>}
 </section>;
}
