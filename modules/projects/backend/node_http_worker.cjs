// Original Node HTTP app over private named-pipe IPC; no additional TCP port.
const http=require('node:http'),path=require('node:path'),os=require('node:os');
const {pathToFileURL}=require('node:url'),{syncBuiltinESMExports}=require('node:module');
const readline=require('node:readline'),crypto=require('node:crypto');
const write=process.stdout.write.bind(process.stdout);
process.stdout.write=process.stderr.write.bind(process.stderr);
let server,logicalHost;
const contexts=new Map(),listen=http.Server.prototype.listen;
const socketPath=process.platform==='win32'?'\\\\.\\pipe\\platform-node-'+process.pid:path.join(os.tmpdir(),'platform-node-'+process.pid+'.sock');
let readyResolve,readyReject;
const ready=new Promise((resolve,reject)=>{readyResolve=resolve;readyReject=reject});
http.Server.prototype.listen=function(...args){
 if(server)throw Error('한 앱에서 여러 HTTP 수신기를 시작할 수 없습니다.');
 server=this;
 const options=typeof args[0]==='object'?args[0]:{port:args[0]};
 if(!Number.isInteger(Number(options.port)))throw Error('Node HTTP 포트 설정을 확인할 수 없습니다.');
 logicalHost='127.0.0.1:'+options.port;
 this.prependListener('request',(req)=>{
  const key=req.headers['x-platform-ipc-request'],context=contexts.get(key);
  delete req.headers['x-platform-ipc-request'];
  if(!context){req.destroy();return;}
  contexts.delete(key);
  // Preserve the actual host client; remote platform clients never become local admins.
  Object.defineProperty(req.socket,'remoteAddress',{value:context.client,configurable:true});
 });
 this.once('error',readyReject);this.once('listening',readyResolve);
 const callback=typeof args.at(-1)==='function'?args.at(-1):undefined;
 return listen.call(this,socketPath,...(callback?[callback]:[]));
};
syncBuiltinESMExports();
async function call(message){
 await Promise.race([ready,new Promise((_,reject)=>setTimeout(()=>reject(Error('Node HTTP 서버 시작 시간이 초과됐습니다.')),30000).unref())]);
 const target=message.path||'/';
 if(!target.startsWith('/')||target.startsWith('//')||target.includes('?'))throw Error('올바르지 않은 앱 요청 경로입니다.');
 const key=crypto.randomUUID(),headers={};
 for(const [name,value] of Object.entries(message.headers||{}))if(!['host','connection','content-length','transfer-encoding','x-platform-ipc-request'].includes(name.toLowerCase()))headers[name.toLowerCase()]=String(value);
 // Translate only same-host origins to the app's original local origin.
 if(headers.origin&&message._host){try{const origin=new URL(headers.origin);if(origin.host===message._host)headers.origin='http://'+logicalHost;}catch{}}
 headers.host=logicalHost;headers.connection='close';headers['x-platform-ipc-request']=key;
 const body=String(message.body||'');
 if(Buffer.byteLength(body)>8*1024*1024)throw Error('앱 요청이 8 MiB를 초과합니다.');
 if(body)headers['content-length']=Buffer.byteLength(body);
 contexts.set(key,{client:message._client?.[0]||'127.0.0.1'});
 try{return await new Promise((resolve,reject)=>{
  const request=http.request({socketPath,path:target+(message.query?'?'+message.query:''),method:message.method||'GET',headers},response=>{
   const parts=[];let size=0;
   response.on('data',chunk=>{size+=chunk.length;if(size>8*1024*1024)response.destroy(Error('앱 응답이 8 MiB를 초과합니다.'));else parts.push(chunk)});
   response.on('error',reject);response.on('end',()=>{
    // Cookie authentication cannot be represented faithfully by the JSON fetch bridge.
    if(response.headers['set-cookie'])return reject(Error('쿠키 세션 앱은 인증 어댑터가 필요합니다.'));
    const resultHeaders={};for(const [name,value]of Object.entries(response.headers))if(!['content-length','transfer-encoding','connection'].includes(name))resultHeaders[name]=Array.isArray(value)?value.join(', '):value;
    resolve({status:response.statusCode,headers:resultHeaders,body:Buffer.concat(parts).toString('base64')});
   });
  });
  request.setTimeout(60000,()=>request.destroy(Error('Node 앱 응답 시간이 초과됐습니다.')));request.on('error',reject);request.end(body);
 });}finally{contexts.delete(key)}
}
async function main(){
 const folder=path.resolve(process.argv[2]),entry=path.resolve(folder,process.argv[3]);
 if(!entry.startsWith(folder+path.sep))throw Error('프로젝트 밖의 Node 진입점입니다.');
 process.chdir(folder);await import(pathToFileURL(entry).href);
 if(!server)throw Error('원본 Node 앱이 HTTP 서버를 시작하지 않았습니다.');
 const input=readline.createInterface({input:process.stdin});
 for await(const line of input){try{write(JSON.stringify(await call(JSON.parse(line)))+'\n')}catch(error){write(JSON.stringify({error:error.message})+'\n')}}
 server.close();process.exit(0);
}
main().catch(error=>{write(JSON.stringify({error:error.message})+'\n');process.exit(1)});
