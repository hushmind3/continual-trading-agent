import {lazy} from 'react';
import {Activity,Landmark} from 'lucide-react';
import type {MenuItem} from '../../../shell/menu_groups/menu_types';
export const menus:MenuItem[]=[
 {hash:'finance/operation_control',name:'운영 제어',group:'거래 운영',icon:Activity,component:lazy(()=>import('./operation_control/OperationControl').then(m=>({default:m.OperationControl}))),required:['operations','resources','job','capabilities']},
 {hash:'finance/virtual_account_orders',name:'가상계좌 · 주문',group:'거래 운영',icon:Landmark,component:lazy(()=>import('./virtual_account_orders/VirtualAccountOrders').then(m=>({default:m.VirtualAccountOrders}))),required:['operations']},
];
