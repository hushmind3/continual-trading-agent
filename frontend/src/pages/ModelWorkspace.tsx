import {OperationsControls} from '../ui/OperationsControls';
import {useCallback,useState} from 'react';
import {Layers3} from 'lucide-react';
import {useOperations} from '../data/Operations';
import {Skeleton} from '../ui/Primitives';
import {Panel,KeyValues} from '../ui/Panel';
import {number} from '../ui/format';
import {ExpertLibraryPanel} from './model/ExpertLibraryPanel';
import {ExpertInspector} from './model/ExpertInspector';
import {ExpertComparison} from './model/ExpertComparison';
import {ModelGuide} from './model/ModelGuide';
import {ModelFolderPanel} from './model/ModelFolderPanel';
export function ModelWorkspace(){const {state:s}=useOperations();const [inspect,setInspect]=useState<string|null>(null);const close=useCallback(()=>setInspect(null),[]);if(!s)return <Skeleton/>;
 return <div className="space-y-6"><header className="rounded-2xl bg-[#202e4a] px-6 py-6 text-white"><p className="mb-2 flex items-center gap-2 text-xs text-blue-200"><Layers3 size={15}/>공식 SAC · 동결 Expert</p><h2 className="text-2xl font-bold">Expert 슬롯 관리</h2><p className="mt-3 text-sm text-slate-300">운영 구성 {s.experts.active.length}개 · 등록 {s.experts.items.length}개 · 저장 정책 업데이트 {number(s.model.updates,0)}회</p><p className="mt-2 text-xs text-slate-400">원본·양자화 패키지를 선택·교체합니다. Expert 가중치는 학습하지 않습니다.</p></header>
 <OperationsControls/><ModelGuide/><Panel title="SAC 정책망 · Expert 관측 연결" description="원본 정책에 ObservationWrapper로 연결"><KeyValues items={[['Actor',s.settings.policy.actor_arch.join(' → ')],['Critic',s.settings.policy.n_critics+' × '+s.settings.policy.critic_arch.join(' → ')],['추가 관측',s.experts.observation_connection.size+'값'],['입력 경로',s.experts.observation_connection.configured?'ExpertObservation 구성됨':'미구성'],['마지막 시장 Expert 성공 수',s.experts.observation_connection.recorded?s.experts.observation_connection.last_success.market:'미기록'],['마지막 매매 Expert 성공 수',s.experts.observation_connection.recorded?s.experts.observation_connection.last_success.action:'미기록']]}/></Panel>
 <ExpertLibraryPanel onInspect={setInspect}/><ModelFolderPanel/><ExpertComparison/><ExpertInspector expert={s.experts.items.find(e=>e.id===inspect)||null} close={close}/>
 </div>;
}
