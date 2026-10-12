import {FinrlWorkspace} from './FinrlWorkspace';
import {Tabs} from '../../ui/Primitives';
export function ReferenceWorkspace(){
 const requested=new URLSearchParams(location.hash.split('?')[1]||'').get('ref');
 const step:'data'|'train'|'backtest'=requested==='train'||location.hash.startsWith('#stock-training')?'train':requested==='backtest'||location.hash.startsWith('#backtest')?'backtest':'data';
 const setStep=(next:'data'|'train'|'backtest')=>{location.hash='workspace?tab=examples&ref='+next};
 return <div className="space-y-3"><Tabs value={step} onChange={value=>setStep(value as typeof step)} items={[{id:'data',label:'1 · 데이터 준비'},{id:'train',label:'2 · 예제 학습'},{id:'backtest',label:'3 · 예제 평가'}]}/><FinrlWorkspace stage={step} onStageChange={setStep}/></div>;
}
