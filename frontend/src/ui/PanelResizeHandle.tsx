import {useEffect,useState,type RefObject} from 'react';

interface Props {target:RefObject<HTMLElement|null>;storageKey:string;label:string;resetToken?:unknown}
export function PanelResizeHandle({target,storageKey,label,resetToken}:Props){
 const [value,setValue]=useState<number>();
 const limits=()=>{
  const style=getComputedStyle(target.current??document.documentElement);
  return {min:Number(style.getPropertyValue('--panel-min-percent')),max:Number(style.getPropertyValue('--panel-max-percent')),step:Number(style.getPropertyValue('--panel-resize-step'))};
 };
 const measure=()=>{
  const element=target.current,parent=element?.parentElement;
  if(!element||!parent||!parent.clientWidth)return;
  return element.getBoundingClientRect().width/parent.getBoundingClientRect().width*100;
 };
 const apply=(percent:number,persist=false)=>{
  if(!target.current||!Number.isFinite(percent))return;
  const {min,max}=limits(),next=Math.max(min,Math.min(max,percent));
  target.current.style.setProperty('--side-panel-width',next+'%');setValue(next);
  if(persist)try{localStorage.setItem(storageKey,String(next))}catch{/* Dragging works without storage. */}
 };
 const reset=()=>{
  target.current?.style.removeProperty('--side-panel-width');
  try{localStorage.removeItem(storageKey)}catch{/* Keep the default width. */}
  setValue(measure());
 };
 useEffect(()=>{
  let saved:string|null=null;try{saved=localStorage.getItem(storageKey)}catch{/* Optional preference. */}
  if(saved!==null)apply(Number(saved));else setValue(measure());
 },[target,storageKey,resetToken]);
 const {min,max,step}=limits();
 return <div role="separator" aria-label={label} aria-orientation="vertical" aria-valuemin={min} aria-valuemax={max} aria-valuenow={value==null?undefined:Math.round(value)} tabIndex={0} className="ui-panel-resizer" title="드래그로 너비 조절 · 방향키로 조절 · 두 번 클릭하면 기본 너비"
  onPointerDown={event=>{event.preventDefault();event.currentTarget.focus();event.currentTarget.setPointerCapture(event.pointerId)}}
  onPointerMove={event=>{if(!event.currentTarget.hasPointerCapture(event.pointerId))return;const parent=target.current?.parentElement;if(parent){const bounds=parent.getBoundingClientRect();apply((bounds.right-event.clientX)/bounds.width*100)}}}
  onPointerUp={event=>{const width=measure();if(width!=null)apply(width,true);if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId)}}
  onDoubleClick={reset}
  onKeyDown={event=>{
   if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
   event.preventDefault();const current=measure()??min;
   apply(event.key==='Home'?min:event.key==='End'?max:current+(event.key==='ArrowLeft'?step:-step),true);
  }}/>;
}
