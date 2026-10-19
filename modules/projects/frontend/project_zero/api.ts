import {request} from '@platform/data/api';
export class AppError extends Error {constructor(public status:number,message:string){super(message)}}
export async function invoke<T>(id:string,path:string,token='',body?:unknown,method?:string):Promise<T>{
 const result=await request<{status:number;body:string}>('projects/invoke',{id,path,method:method||(body?'POST':'GET'),headers:{'content-type':'application/json',...(token?{'X-Project-Zero-Token':token}:{})},body:body?JSON.stringify(body):''});
 const decoded=new TextDecoder().decode(Uint8Array.from(atob(result.body),c=>c.charCodeAt(0)));
 let value:unknown;try{value=JSON.parse(decoded)}catch{throw new AppError(result.status,'앱 응답을 읽지 못했습니다.')}
 if(result.status>=400)throw new AppError(result.status,String((value as {detail?:string}).detail||'앱 요청 실패'));
 return value as T;
}
