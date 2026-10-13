import {useState} from 'react';
import {apiUrl} from '../../../../data/api';
import {useSystemState,useOperations} from '../../../../data/Operations';
import {Panel,KeyValues} from '../../../../ui/Panel';
import {Button,Empty,ErrorMessage,Status,inputClass} from '../../../../ui/Primitives';
import {bytes,date,number} from '../../../../ui/format';
import {ChampionSpec} from '../../../../ui/ChampionSpec';
import type {Champion} from '../../../../data/library';
export function CheckpointPanel(){
 const {state:s,execute,pending}=useOperations(),champions=useSystemState<{items:Champion[]}>('champions');
 const [path,setPath]=useState(''),[error,setError]=useState(''),[message,setMessage]=useState('');
 if(!s)return null;
 const chosen=s.checkpoints.find(item=>item.path===path),model=champions.data?.items.find(item=>item.checkpoint===path);
 const loaded=chosen?Object.values(s.operations?.policies??{}).find(item=>item.path===chosen.path):undefined;
 const load=async()=>{if(!chosen)return;setError('');setMessage('');try{await execute('checkpoints/restore',{path:chosen.path});setMessage('모델을 메모리에 로드했습니다.')}catch(e){setError(e instanceof Error?e.message:'모델 로딩 실패')}};
 return <Panel title="저장 모델" description="FinRL · SB3 학습 결과를 선택해 로드하고 이후 실행에 사용합니다.">
 {s.checkpoints.length?<><div className="flex flex-wrap items-center gap-2"><select aria-label="저장 모델 선택" className={inputClass+' min-w-0 flex-1'} value={chosen?.path??''} onChange={e=>{setPath(e.target.value);setMessage('');setError('')}}><option value="">저장 모델 선택</option>{s.checkpoints.map(item=><option key={item.path} value={item.path}>{item.name} · {String(item.identity.algorithm??'').toUpperCase()} · {item.num_timesteps===0?'미학습':number(item.num_timesteps,0)+'단계'}{item.compatible?'':' · 환경 미호환'}</option>)}</select><Button tone="primary" disabled={!chosen||!chosen.compatible||s.job.running} busy={pending.has('checkpoints/restore')} onClick={()=>void load()}>모델 로드</Button>{chosen&&<a className="text-xs font-semibold text-blue-600" href={apiUrl('checkpoint',{path:chosen.path})} download>모델 다운로드</a>}</div>
 {chosen&&<div className="mt-3"><Status tone={loaded?.loaded?'good':chosen.compatible?'idle':'warn'}>{loaded?.loaded?'로드됨 · '+loaded.device:chosen.compatible?'로드 확인 없음':'현재 환경과 미호환'}</Status><KeyValues items={[['모델 파일',chosen.path],['저장 시각',date(chosen.file.modified)],['모델 크기',bytes(chosen.file.bytes)],['학습 알고리즘',String(chosen.identity.algorithm??'').toUpperCase()],['학습 단계',number(chosen.num_timesteps,0)],['가중치 업데이트',number(chosen.updates,0)]]}/>{model&&<details className="mt-3"><summary className="cursor-pointer text-xs text-blue-600">모델 세부 구조</summary><div className="mt-3"><ChampionSpec model={model}/></div></details>}</div>}</>:<Empty title="저장된 학습 모델이 없습니다."/>}
 <ErrorMessage message={error}/>{message&&<p className="mt-3 text-xs text-emerald-700">{message}</p>}
 </Panel>;
}
