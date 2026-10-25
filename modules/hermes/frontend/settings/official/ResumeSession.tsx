import {lazy,Suspense,useEffect,useRef} from 'react';
import {useLocation,useNavigate} from 'react-router';
import {request} from '@platform/data/api';
import {navigateAgent} from '../../agent_navigation';
import {prefix,type SessionDetail} from '../../types';

const ProfileChat=lazy(()=>import('@hermes-official/pages/ChatPage'));

/** Default-profile history resumes in the existing chat, never in a second copy. */
export function ResumeSession(){
 const {search}=useLocation(),navigate=useNavigate(),started=useRef(false);
 const query=new URLSearchParams(search),profile=query.get('profile')||'default';
 useEffect(()=>{
  if(profile!=='default'||started.current)return;
  started.current=true;
  void (async()=>{
   let id=query.get('resume')||query.get('session')||'';
   if(!id)id=(await request<SessionDetail>(prefix+'session/create',{title:'새 대화'})).session.id;
   window.dispatchEvent(new CustomEvent('hermes:resume-session',{detail:{id}}));
   navigate('/sessions',{replace:true});
   navigateAgent('chat');
  })();
 },[profile,search]);
 return profile==='default'?<p role="status">기존 대화로 이동하고 있습니다.</p>:<Suspense fallback={<p role="status">프로필 대화를 불러오고 있습니다.</p>}><ProfileChat/></Suspense>;
}
