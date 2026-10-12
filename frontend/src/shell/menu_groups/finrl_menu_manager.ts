import {lazy} from 'react';
import {ChartNoAxesCombined,Database,GraduationCap,Workflow} from 'lucide-react';
import type {MenuItem} from './menu_types';
const reference=lazy(()=>import('../../pages/finrl/ReferenceWorkspace').then(m=>({default:m.ReferenceWorkspace})));
export const menus:MenuItem[]=[
 {hash:'learning',name:'정책 학습',group:'FinRL · 메인',icon:GraduationCap,component:lazy(()=>import('../../pages/training/TrainingWorkspace').then(m=>({default:m.TrainingWorkspace}))),required:['settings','model','data','experts','job','checkpoints','resources']},
 {hash:'portfolio',name:'정책 평가 · 백테스트',group:'FinRL · 메인',icon:ChartNoAxesCombined,component:lazy(()=>import('../../pages/portfolio/PortfolioWorkspace').then(m=>({default:m.PortfolioWorkspace}))),required:['settings','model','evaluation','job','checkpoints']},
 {hash:'finrl',name:'주식거래 데이터 준비',group:'FinRL · 메인',icon:Database,component:reference,required:['job']},
 {hash:'stock-training',name:'주식거래 알고리즘 학습',group:'FinRL · 메인',icon:GraduationCap,component:reference,required:['job']},
 {hash:'backtest',name:'주식거래 백테스트',group:'FinRL · 메인',icon:ChartNoAxesCombined,component:reference,required:['job']},
 {hash:'frameworks',name:'FinRL 모듈 · 도구',group:'FinRL · 메인',icon:Workflow,component:lazy(()=>import('../../pages/frameworks/FrameworkWorkspace').then(m=>({default:m.FinrlToolsWorkspace}))),required:['job']},
];
