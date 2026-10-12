import {useState} from 'react';
import {PaperAccounts} from './portfolio/PaperAccounts';
import {Tabs} from '../ui/Primitives';
import type {Currency} from '../data/types';
export function PaperWorkspace(){
 const [currency,setCurrency]=useState<Currency>('USD');
 return <div className="space-y-3"><Tabs value={currency} onChange={value=>setCurrency(value as Currency)} items={[{id:'USD',label:'미국주식 · USD'},{id:'KRW',label:'국내주식 · KRW'}]}/><PaperAccounts key={currency} currency={currency}/></div>;
}
