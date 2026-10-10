import {Link2,KeyRound,RefreshCw} from 'lucide-react';
import {useEndpoint} from '../data/useEndpoint';
import {useOperations} from '../data/Operations';
import type {Connections} from '../data/types';
import {Panel,KeyValues} from '../ui/Panel';
import {Button,ErrorMessage,Skeleton,Status,inputClass} from '../ui/Primitives';
import {Capability} from '../ui/Capability';
export function ConnectionSettings(){const {state:s}=useOperations();const connection=useEndpoint<Connections>('connections');if(!s)return <Skeleton/>;
 return <div className="grid items-start gap-6 lg:grid-cols-2"><Panel title="연결 상태" description="현재 API·원격 데이터 공급원 · 인증 값은 응답에 포함하지 않습니다." actions={<Button busy={connection.loading} onClick={()=>void connection.refresh()}><RefreshCw size={14}/>연결 확인</Button>}><ErrorMessage message={connection.error}/><div className="flex items-center gap-2 text-sm font-bold"><Link2 size={17} className="text-blue-500"/>로컬 SAC API <Status tone={connection.data?'good':'idle'}>{connection.data?'응답 확인':'확인 중'}</Status></div><KeyValues items={[['API 주소',new URL('/api',location.origin).href],['현재 가격 DB',s.data.path],['원격 공급원',connection.data?.data.source||'미설정'],['사용 가능한 원격 공급원',connection.data?.data.available_sources.join(', ')||'없음'],['원격 상태',connection.data?.data.status]]}/>{connection.data?.data.reason&&<p className="mt-4 rounded-xl bg-amber-50 p-4 text-xs leading-6 text-amber-800">{connection.data.data.reason}</p>}<p className="mt-5 text-xs leading-6 text-slate-500"><KeyRound size={13} className="mr-1 inline"/>FMP 인증은 공식 FinRL-X 설정 모듈에서 읽습니다. 현재 웹에서 인증을 저장하는 API는 제공하지 않습니다.</p><input aria-label="API 인증 관리" className={inputClass+' mt-3'} placeholder="현재 웹 인증 편집 미제공" disabled/></Panel>
 <div className="space-y-6"><Panel title="증권사 연결" description="과거 화면과 현재 실행 경로의 연결 상태"><div className="space-y-4"><Capability name="kiwoom" label="키움 시세·주문 연결"/><Capability name="alpaca" label="Alpaca 주문 연결"/><Capability name="live_feed" label="실시간 입력"/></div></Panel><Panel title="적용 설정" description="원본 설정과 라이브러리 기본값 확인"><KeyValues items={[['학습 설정 출처',s.settings.parameter_source],['환경 설정 출처',s.settings.environment_source],['실행 단계',s.settings.steps_per_run]]}/><Capability name="settings_edit" label="웹 학습 설정 편집"/></Panel></div>
 </div>;
}
