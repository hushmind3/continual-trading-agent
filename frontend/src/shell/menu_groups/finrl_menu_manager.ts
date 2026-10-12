import {lazy} from 'react';
import {ChartNoAxesCombined,Database,GraduationCap,Workflow} from 'lucide-react';
import {actionMenus,moduleMenus,type MenuItem} from './menu_types';
import type {BackendAction,SourceModule} from '../../data/menu_types';
const reference=lazy(()=>import('../../pages/finrl/ReferenceWorkspace').then(m=>({default:m.ReferenceWorkspace})));
const source=lazy(()=>import('../../pages/frameworks/SourceModuleWorkspace').then(m=>({default:m.SourceModuleWorkspace})));
const feature=lazy(()=>import('../../pages/frameworks/FeatureWorkspace').then(m=>({default:m.FeatureWorkspace})));
export const menus:MenuItem[]=[
 {hash:'learning',name:'정책 학습',group:'FinRL · 메인 실행',icon:GraduationCap,component:lazy(()=>import('../../pages/training/TrainingWorkspace').then(m=>({default:m.TrainingWorkspace}))),required:['settings','model','data','experts','job','checkpoints','resources']},
 {hash:'portfolio',name:'정책 평가 · 백테스트',group:'FinRL · 메인 실행',icon:ChartNoAxesCombined,component:lazy(()=>import('../../pages/portfolio/PortfolioWorkspace').then(m=>({default:m.PortfolioWorkspace}))),required:['settings','model','evaluation','job','checkpoints']},
 {hash:'finrl',name:'주식거래 데이터 준비',group:'FinRL · 메인 실행',icon:Database,component:reference,required:['job']},
 {hash:'stock-training',name:'주식거래 알고리즘 학습',group:'FinRL · 메인 실행',icon:GraduationCap,component:reference,required:['job']},
 {hash:'backtest',name:'주식거래 백테스트',group:'FinRL · 메인 실행',icon:ChartNoAxesCombined,component:reference,required:['job']},
 {hash:'frameworks',name:'FinRL 모듈 · 도구',group:'FinRL · 메인 실행',icon:Workflow,component:lazy(()=>import('../../pages/frameworks/FrameworkWorkspace').then(m=>({default:m.FinrlToolsWorkspace}))),required:['job']},
];
export function registeredMenus(actions:BackendAction[],modules:SourceModule[]=[]){return [...menus,...actionMenus(actions,'finrl','FinRL · 메인 실행',feature,Workflow),...moduleMenus(modules,'FinRL','FinRL · 메인 소스',source,Workflow)];}
