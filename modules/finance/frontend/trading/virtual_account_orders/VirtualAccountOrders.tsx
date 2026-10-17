import {useState} from 'react';
import {PaperAccounts} from './PaperAccounts';
import {Tabs,Status} from '@platform/ui/Primitives';
import {useOperations} from '@platform/data/Operations';
import type {Currency} from '@platform/data/types';
export function VirtualAccountOrders(){
 const {state}=useOperations();
 const [currency,setCurrency]=useState<Currency>(()=>{try{const saved=sessionStorage.getItem('account_currency');if(saved==='KRW'||saved==='USD')return saved}catch{}const currencies=Object.keys(state?.operations?.policies??{});return currencies.length===1&&currencies[0]==='KRW'?'KRW':'USD'});
 const choose=(value:string)=>{setCurrency(value as Currency);try{sessionStorage.setItem('account_currency',value)}catch{}};
 return <div className="account-workspace space-y-6"><div className="account-currency-bar"><Tabs value={currency} onChange={choose} items={[{id:'USD',label:'미국주식 · USD'},{id:'KRW',label:'국내주식 · KRW'}]}/><Status tone={state?.operations?.controls.paper?'good':'idle'}>{state?.operations?state.operations.controls.paper?'가상매매 활성':'가상매매 중지':'계좌 상태 조회 중'}</Status></div><PaperAccounts key={currency} currency={currency}/></div>;
}
