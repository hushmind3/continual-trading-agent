import {useState} from 'react';
import {OperationsBoard} from './OperationsBoard';
import {PaperAccounts} from './portfolio/PaperAccounts';
import {Tabs} from '../ui/Primitives';
import type {Currency} from '../data/types';
export function OperatingWorkspace(){
 const [currency,setCurrency]=useState<Currency>('USD');
 return <div className="grid items-start gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(360px,.8fr)]"><OperationsBoard/><aside className="min-w-0 space-y-3"><div className="flex items-center justify-between gap-2"><h2 className="text-sm font-bold">가상계좌</h2><Tabs value={currency} onChange={value=>setCurrency(value as Currency)} items={[{id:'USD',label:'USD'},{id:'KRW',label:'KRW'}]}/></div><PaperAccounts key={currency} currency={currency}/></aside></div>;
}
