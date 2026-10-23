"""Enforce code-analysis permissions before the original agent executes a batch."""
from pathlib import Path

ALLOWED=frozenset({'read_file','search_files'})


def bind(agent,workspace,on_denied=None,attachments=()):
    root=Path(workspace).resolve()
    attached={Path(path).resolve() for path in attachments}
    execute=agent._execute_tool_calls
    agent._read_only_denials=[]
    if isinstance(getattr(agent,'tools',None),list):
        agent.tools=[tool for tool in agent.tools if tool.get('function',{}).get('name') in ALLOWED]

    def deny(reason):
        agent._read_only_denials.append(reason)
        if on_denied:on_denied(reason)
        raise PermissionError(reason)

    def guarded(message,*args,**kwargs):
        import json
        calls=message.get('tool_calls',[]) if isinstance(message,dict) else getattr(message,'tool_calls',[]) or []
        for call in calls:
            function=call.get('function',{}) if isinstance(call,dict) else call.function
            name=function.get('name') if isinstance(function,dict) else function.name
            values=function.get('arguments',{}) if isinstance(function,dict) else function.arguments
            if name not in ALLOWED:deny('읽기 전용 분석에서는 실행할 수 없는 도구입니다: '+str(name))
            values=json.loads(values) if isinstance(values,str) else values
            if not isinstance(values,dict):raise ValueError('올바르지 않은 읽기 전용 도구 입력입니다.')
            target=Path(values.get('path') or '.')
            target=(target if target.is_absolute() else root/target).resolve()
            if not target.is_relative_to(root) and target not in attached:deny('읽기 전용 작업 폴더 밖의 경로입니다.')
        return execute(message,*args,**kwargs)

    agent._execute_tool_calls=guarded
