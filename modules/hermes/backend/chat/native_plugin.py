"""Organization tools hosted by the original Hermes plugin runtime, using its actual parent agent."""
import copy
import json
import threading
from pathlib import Path
from types import SimpleNamespace

from ai_agent.Hermes.chat import company, meetings, project_commands
from ai_agent.Hermes.chat.prompt_profiles import staff_delegation, system_instructions


def install(home,db=None):
    """Install this adapter in the native loader's source boundary so its normal reload replaces the code."""
    folder=Path(home)/'plugins'/'platform-organization'
    folder.mkdir(parents=True,exist_ok=True)
    changed=False
    files={
        'plugin.yaml': 'name: platform-organization\nversion: 1.0.0\ndescription: 플랫폼 조직·직원·회의 도구\nprovides_tools: [company_records, company_recall, team_meeting, project_npm, delegate_staff]\n',
        '__init__.py': '''# Managed by Project Platform; implementation stays in the registered Hermes module.
import sys
from pathlib import Path
from hermes_constants import get_default_hermes_root
root=Path(get_default_hermes_root()).parents[2]
sys.path.insert(0,str(root/'backend'))
from platform_modules import mount_namespaces
mount_namespaces()
'''+Path(__file__).read_text(encoding='utf-8'),
    }
    for name,value in files.items():
        target=folder/name
        if target.is_file() and target.read_text(encoding='utf-8')==value:continue
        temporary=target.with_suffix(target.suffix+'.tmp')
        temporary.write_text(value,encoding='utf-8');temporary.replace(target)
        changed=True
    if db is not None and not db.get_meta('platform.organization-plugin.v1'):
        from hermes_cli.plugins_cmd import dashboard_set_agent_plugin_enabled
        result=dashboard_set_agent_plugin_enabled('platform-organization',enabled=True)
        if not result.get('ok'):raise RuntimeError('공식 조직 플러그인 활성화 실패: '+str(result.get('error')))
        db.set_meta('platform.organization-plugin.v1','1')
    elif db is not None and changed:
        from hermes_cli.config import load_config
        selection=load_config().get('plugins') or {}
        if 'platform-organization' in (selection.get('enabled') or []) and 'platform-organization' not in (selection.get('disabled') or []):
            from hermes_cli.plugins_activation import activate_plugin_now
            result=activate_plugin_now('platform-organization')
            if result.get('error'):raise RuntimeError('공식 조직 플러그인 반영 실패: '+str(result['error']))


def settings(home):
    path=Path(home)/'platform-settings.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}


class OrganizationContext:
    """Domain state only; the agent, transcript, tools, interruption and approvals belong to Hermes."""
    def __init__(self,agent):
        from hermes_constants import get_hermes_home
        self.agent=agent
        self.db=agent._session_db
        if self.db is None:raise ValueError('공식 세션 DB가 없는 실행입니다.')
        home=get_hermes_home()
        self.company_links_path=Path(home)/'company-links.json'
        self.company_prompt_settings=settings(home)
        messages=getattr(agent,'_session_messages',[]) or []
        owner=next((m.get('content','') for m in reversed(messages) if m.get('role')=='user'),'')
        self.job={'session_id':agent.session_id,'owner_message':owner if isinstance(owner,str) else '',
                  'owner_request_id':str(getattr(agent,'_current_turn_id','') or getattr(agent,'_current_task_id',''))}
        self.lock=threading.RLock()
        self.company_link=company.connection(self,agent.session_id)
        self.company_visible_history=None
        self.meeting_agent=None

    @property
    def stopping(self):return bool(getattr(self.agent,'_interrupt_requested',False))

    def event(self,name,detail):
        callback=getattr(self.agent,'tool_progress_callback',None)
        if callback:callback('tool.progress','platform_company',json.dumps({'event':name,'detail':detail},ensure_ascii=False))

    def publish_meeting(self,state):
        callback=getattr(self.agent,'tool_progress_callback',None)
        if callback:callback('tool.progress','platform_company',json.dumps({'meeting':state},ensure_ascii=False))

    def approve(self,*,reason,command):
        from tools.terminal_tool import _get_approval_callback
        callback=_get_approval_callback()
        return callback(command,reason) if callback else 'deny'

    def session(self,session_id):
        row=self.db.get_session(session_id)
        if row is None:raise ValueError('대화를 찾을 수 없습니다.')
        return {'session':row,'messages':self.db.get_messages_as_conversation(session_id)}


def context(agent):
    if agent is None:
        from agent.subagent_lifecycle import get_active_subagent_parent
        agent=get_active_subagent_parent()
    if agent is None:raise ValueError('실행 중인 공식 부모 에이전트가 필요합니다.')
    current=getattr(agent,'_platform_worker',None)
    if current is not None and current.agent is agent:return current
    key=(agent.session_id,getattr(agent,'_current_turn_id',None),getattr(agent,'_current_task_id',None))
    cached=getattr(agent,'_platform_organization_context',None)
    if cached is None or cached[0]!=key:
        cached=(key,OrganizationContext(agent));agent._platform_organization_context=cached
    return cached[1]


def register(sdk):
    from hermes_constants import get_hermes_home
    from hermes_state import SessionDB
    from tools.registry import registry
    # Register native delegation before reading its schema, without replacing its implementation.
    from tools import delegate_tool  # noqa: F401
    home=Path(get_hermes_home())
    reader=None

    def prompt(info):
        nonlocal reader
        if info.get('platform') in ('platform','application','subagent'):return ''
        if reader is None:
            if not (home/'state.db').is_file():return ''
            reader=SessionDB(db_path=home/'state.db',read_only=True)
        row=reader.get_session(info['session_id']) or {}
        if row.get('source')=='subagent':return ''
        cfg=settings(home)
        current=SimpleNamespace(db=reader,company_links_path=home/'company-links.json')
        return company.prepare(current,cfg,info['session_id'],delegation_tool='delegate_staff')

    def common_prompt(info):
        return '' if info.get('platform') in ('platform','application','subagent') else system_instructions(settings(home))

    sdk.register_system_prompt_section('platform.common',common_prompt)
    sdk.register_system_prompt_section('platform.organization',prompt)
    sdk.on_unload(lambda:reader.close() if reader is not None else None)

    def records(args,parent_agent=None,**kwargs):
        current=context(parent_agent)
        return company.execute(args,worker=current,parent_agent=current.agent,**kwargs)

    def recall(args,parent_agent=None,**kwargs):
        return company.recall_for_staff(args,worker=context(parent_agent))

    def meeting(args,parent_agent=None,session_id=None,**kwargs):
        current=context(parent_agent)
        return meetings.run(current,{**args,'_parent_agent':current.agent,'_caller_session':session_id or current.agent.session_id})

    def npm(args,parent_agent=None,**kwargs):
        current=context(parent_agent)
        if getattr(current.agent,'_platform_meeting_review',False):
            return json.dumps({'error':'회의 중에는 명령을 실행하지 않습니다.'},ensure_ascii=False)
        return project_commands.run(current,args)

    def delegate(args,parent_agent=None,**kwargs):
        current=context(parent_agent)
        parent_agent=current.agent
        if not current.company_link:return json.dumps({'error':'이 대화에 연결된 조직이 없습니다.'},ensure_ascii=False)
        if getattr(parent_agent,'_platform_meeting_review',False):
            return json.dumps({'error':'회의 직원은 총괄에게 실행 위임을 요청하세요.'},ensure_ascii=False)
        # The existing platform caller is retired with owner adoption; preserve its current binding meanwhile.
        if getattr(parent_agent._dispatch_delegate_task,'_platform_staff_bound',False):
            return parent_agent._dispatch_delegate_task(args)
        try:prepared=staff_delegation(args,current.company_prompt_settings)
        except ValueError as exc:return json.dumps({'error':str(exc)},ensure_ascii=False)
        return parent_agent._dispatch_delegate_task(prepared)

    recall_schema={'name':'company_recall','description':'조직의 관련 결정·경험만 읽습니다. 실행·회의·승인은 수행하지 않습니다.',
        'parameters':{'type':'object','properties':{key:value for key,value in company.SCHEMA['parameters']['properties'].items() if key in ('query','scope','kind','venture_id')},'additionalProperties':False}}
    schema=copy.deepcopy(registry.get_entry('delegate_task').schema)
    schema.update(name='delegate_staff',description='등록된 staff_id의 전문성·실행 지침을 적용해 원본 Hermes 자식 에이전트에게 위임합니다. 원본 목록·추가 지시·중지·백그라운드 실행 인수를 유지합니다.')
    identity={'type':'string','description':'company_records가 반환한 직원 고유 식별자'}
    schema['parameters']['properties']['staff_id']=identity
    schema['parameters']['properties']['tasks']['items']['properties']['staff_id']=identity
    for name,toolset,definition,handler in (
        ('company_records','platform_company',company.SCHEMA,records),
        ('company_recall','platform_company_recall',recall_schema,recall),
        ('team_meeting','platform_company',meetings.SCHEMA,meeting),
        ('project_npm','platform_company',project_commands.SCHEMA,npm),
        ('delegate_staff','delegation',schema,delegate),
    ):sdk.register_tool(name,toolset,definition,handler)
