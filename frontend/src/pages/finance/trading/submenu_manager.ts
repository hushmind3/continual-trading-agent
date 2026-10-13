import {lazy} from 'react';
import {Activity,Landmark} from 'lucide-react';
import type {MenuItem} from '../../../shell/menu_groups/menu_types';
export const menus:MenuItem[]=[
 {hash:'control',name:'운영 제어',group:'거래 운영',icon:Activity,component:lazy(()=>import('./control/OperationsBoard').then(m=>({default:m.OperationsBoard}))),required:['operations','resources','job','capabilities']},
 {hash:'paper',name:'가상계좌 · 주문',group:'거래 운영',icon:Landmark,component:lazy(()=>import('./paper_account/PaperWorkspace').then(m=>({default:m.PaperWorkspace}))),required:['operations']},
];
