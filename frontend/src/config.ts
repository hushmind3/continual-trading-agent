import {Activity,BrainCircuit,FlaskConical,GraduationCap,Layers,Settings2,SlidersHorizontal,Terminal,Trophy} from 'lucide-react';
export const destinations=[
  {name:'운영 · 계좌',hash:'control',icon:SlidersHorizontal},
  {name:'자동매매',hash:'trading-moe',icon:BrainCircuit},
  {name:'시장 · 판단',hash:'markets',icon:Activity},
  {name:'전문가',hash:'experts',icon:Layers},
  {name:'경험 학습',hash:'learning',icon:GraduationCap},
  {name:'승급전',hash:'promotionTrial',icon:Trophy},
  {name:'조립 · 자동실험',hash:'assembly',icon:FlaskConical},
  {name:'연결 설정',hash:'connection',icon:Settings2},
  {name:'상세 · 기록',hash:'system',icon:Terminal},
];
export const modelDefinitions=[
  {name:'Champion',role:'champion' as const,caption:'운영 기준',icon:Trophy,accent:'text-sky-300',surface:'bg-sky-400/10'},
  {name:'Candidate',role:'candidate' as const,caption:'비교 · 평가',icon:FlaskConical,accent:'text-violet-300',surface:'bg-violet-400/10'},
  {name:'TradingMoE',role:'trading-moe' as const,caption:'독립 자동매매',icon:BrainCircuit,accent:'text-teal-300',surface:'bg-teal-400/10'},
];
