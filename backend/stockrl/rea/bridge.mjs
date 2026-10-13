import {Client} from '@modelcontextprotocol/client';
import {StdioClientTransport} from '@modelcontextprotocol/client/stdio';
import {createInterface} from 'node:readline';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('.',import.meta.url));
const client=new Client({name:'stockrl-rea',version:'0.1.0'});
const transport=new StdioClientTransport({command:process.execPath,args:[resolve(root,'node_modules/rea-agents/scripts/rea.mjs'),'--mcp'],cwd:process.cwd(),env:{...process.env,NO_COLOR:'1'},stderr:'inherit'});
try {
 await client.connect(transport);
 for await(const line of createInterface({input:process.stdin})){
  try {
   const request=JSON.parse(line);let result;
   if(request.operation==='close')break;
   if(request.operation==='tools'){const tools=[];let cursor;do{const page=await client.listTools(cursor?{cursor}:undefined);tools.push(...page.tools);cursor=page.nextCursor;}while(cursor);result={tools};}
   else if(request.operation==='call')result=await client.callTool({name:request.tool,arguments:request.arguments??{}},{timeout:600000});
   else throw new Error('지원하지 않는 REA 요청입니다.');
   process.stdout.write(JSON.stringify({result})+'\n');
  }catch(error){process.stdout.write(JSON.stringify({error:String(error?.message??error)})+'\n');}
 }
} finally {await client.close();}
