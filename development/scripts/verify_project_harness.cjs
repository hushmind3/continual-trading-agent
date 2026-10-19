// Compatibility entry point: exercise the original planner/employee workflow.
const {spawnSync}=require('node:child_process');
const path=require('node:path');
if(!process.argv.includes('--allow-local-model')){
 console.error('실제 모델·원본 앱 기록을 사용하는 검사입니다. --allow-local-model로 명시하세요.');process.exit(1);
}
for(const file of ['verify_project_zero_live.cjs','verify_project_zero_task.cjs']){
 const result=spawnSync(process.execPath,[path.join(__dirname,file),'--allow-local-model'],{stdio:'inherit'});
 if(result.status!==0){process.exitCode=result.status||1;break}
}
