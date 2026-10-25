"""User-controlled model settings and native tool discovery, without removing capabilities."""
def model_options(settings, native):
    from .execution import context_window
    saved=(settings.get('model_options') or {}).get(settings['model'],{})
    agent=native.get('agent') or {}
    effort=agent.get('reasoning_effort') or saved.get('reasoning_effort','auto')
    thinking=saved.get('thinking_mode','auto')
    if 'reasoning_effort' in agent:
        thinking='off' if effort in ('none','off') else 'auto' if effort=='auto' else 'on'
    return {'context_length':saved.get('context_length',context_window(native,settings['model'])),
            'thinking_mode':thinking,
            'max_output_tokens':saved.get('max_output_tokens',0),
            'reasoning_effort':effort}

def save_options(settings, request):
    saved=dict((settings.get('model_options') or {}).get(settings['model'],{}))
    if 'context_length' in request:
        value=request['context_length']
        if type(value) is not int or value!=0 and not 512<=value<=2097152:
            raise ValueError('문맥 한도는 0(모델 기본값) 또는 512~2,097,152 정수로 입력하세요.')
        saved['context_length']=value
    if 'thinking_mode' in request:
        if request['thinking_mode'] not in ('auto','on','off'):raise ValueError('Thinking 설정을 확인하세요.')
        saved['thinking_mode']=request['thinking_mode']
    if 'reasoning_effort' in request:
        value=request['reasoning_effort']
        if not isinstance(value,str) or not value or len(value)>40:
            raise ValueError('추론 수준을 확인하세요.')
        saved['reasoning_effort']=value
    if 'max_output_tokens' in request:
        value=request['max_output_tokens']
        if type(value) is not int or value!=0 and not 256<=value<=131072:
            raise ValueError('요청별 출력 한도는 0(원본 기본값) 또는 256~131,072 정수입니다.')
        saved['max_output_tokens']=value
    if saved:
        if not settings.get('model'):raise ValueError('설정할 모델을 먼저 선택하세요.')
        settings['model_options']={**(settings.get('model_options') or {}),settings['model']:saved}
    if settings.get('tool_loading') not in ('native','lazy','eager'):
        raise ValueError('도구 설명 불러오기 설정을 확인하세요.')
    return settings

def configure_tools(worker, mode, *, direct_surfaces=True, direct_tools=()):
    from hermes_cli.config_defaults import DEFAULT_CONFIG
    from tools.registry import registry
    from tools.tool_search import _DIRECT_SURFACE_TOOLSETS
    from copy import deepcopy
    native=worker.native_config()
    before=deepcopy(native)
    search=native.setdefault('tools',{}).setdefault('tool_search',{})
    search['enabled']='off' if mode=='eager' else 'auto'
    # Explicitly direct surfaces remain callable without discovery round trips.
    search['defer']=sorted(name for name, toolset in registry.get_tool_to_toolset_map().items()
                           if name not in direct_tools and (not direct_surfaces or toolset not in _DIRECT_SURFACE_TOOLSETS)) if mode=='lazy' else (
        [name for name in DEFAULT_CONFIG['tools']['tool_search']['defer'] if name not in direct_tools] if mode=='native' else [])
    if native!=before:
        worker.write_config(native)

def apply_thinking(agent, options, local):
    if not local or options['thinking_mode']=='auto':return
    overrides=dict(getattr(agent,'request_overrides',{}) or {})
    extra=dict(overrides.get('extra_body') or {})
    template=dict(extra.get('chat_template_kwargs') or {})
    template['enable_thinking']=options['thinking_mode']=='on'
    extra['chat_template_kwargs']=template;overrides['extra_body']=extra
    agent.request_overrides=overrides


def auxiliary_thinking(native, cfg, options):
    """Share an explicit local Thinking choice through native aux configuration.

    Auto restores the prior native value; differently routed aux models keep
    their own settings. No auxiliary feature or summary output is disabled.
    """
    from copy import deepcopy
    before=deepcopy(native)
    auxiliary=native.get('auxiliary') or {}
    owned=native.get('_platform_aux_thinking',{})
    for task in ('compression','goal_judge'):
        section=auxiliary.get(task) or {}
        extra=section.get('extra_body') or {}
        template=extra.get('chat_template_kwargs') or {}
        saved=owned.get(task)
        shared=(section.get('model') in (None,'','auto',cfg['model'])
                and section.get('base_url') in (None,'',cfg['base_url'])
                and section.get('provider') in (None,'','auto','custom'))
        if cfg.get('local_model') and options['thinking_mode']!='auto' and shared:
            if saved is None:
                saved=owned[task]={'present':'enable_thinking' in template,'value':template.get('enable_thinking')}
            saved['applied']=options['thinking_mode']=='on'
            template['enable_thinking']=saved['applied']
            extra['chat_template_kwargs']=template;section['extra_body']=extra;auxiliary[task]=section
        elif saved is not None:
            if template.get('enable_thinking')==saved['applied']:
                if saved['present']:template['enable_thinking']=saved['value']
                else:template.pop('enable_thinking',None)
                if not template:extra.pop('chat_template_kwargs',None)
                if not extra:section.pop('extra_body',None)
                if not section:auxiliary.pop(task,None)
            owned.pop(task)
    if auxiliary:native['auxiliary']=auxiliary
    elif 'auxiliary' not in before:native.pop('auxiliary',None)
    if owned:native['_platform_aux_thinking']=owned
    else:native.pop('_platform_aux_thinking',None)
    return native!=before


def apply_response_contract(agent, mode, plan_only=False):
    """Use the native OpenAI-compatible transport's constrained JSON response option."""
    if mode == 'json_object' and agent.api_mode == 'chat_completions':
        agent.request_overrides = {**(getattr(agent, 'request_overrides', {}) or {}),
                                   'response_format': {'type': 'json_object'}}
    if plan_only and agent.api_mode == 'chat_completions':
        # Original Project Zero meetings deliberate; its separate employee jobs execute tools.
        agent.request_overrides = {**(getattr(agent, 'request_overrides', {}) or {}), 'tools': [], 'tool_choice': 'none'}


def application_generation(value):
    if not isinstance(value, dict) or set(value)-{'max_tokens','temperature'}:
        raise ValueError('앱 생성 옵션을 확인하세요.')
    if 'max_tokens' in value and (type(value['max_tokens']) is not int or not 1<=value['max_tokens']<=65536):
        raise ValueError('앱 출력 한도는 1~65,536 정수여야 합니다.')
    if 'temperature' in value and (type(value['temperature']) not in (int,float) or not 0<=value['temperature']<=2):
        raise ValueError('앱 temperature는 0~2 숫자여야 합니다.')
    return dict(value)


def apply_application_generation(agent, options):
    if 'max_tokens' in options: agent.max_tokens = options['max_tokens']
    if 'temperature' in options:
        agent.request_overrides = {**(getattr(agent,'request_overrides',{}) or {}),'temperature':options['temperature']}


def sync_tool_policy(worker, agent, cfg):
    """Refresh a native session's schema pin only when its exposure policy changes."""
    if not cfg.get('company_instructions') or cfg.get('application_request'):
        return
    import hashlib
    import json
    import sys
    from tools.mcp_tool_agent import tool_pin_version
    policy = {'platform': sys.platform, 'mode': cfg.get('tool_loading', 'native'),
              'search': worker.native_config().get('tools', {}).get('tool_search', {}),
              'enabled': sorted(agent.enabled_toolsets or []),
              'disabled': sorted(agent.disabled_toolsets or [])}
    signature = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()
    tip = worker.db.get_compression_chain(agent.session_id)[-1]
    if worker.db.get_session_model_config_value(tip, '_platform_tool_policy') == signature:
        return
    # The native conversation runner restores this pin AFTER constructing AIAgent.
    # Re-pin the freshly derived surface before it can resurrect an older eager list.
    pin = {'version': tool_pin_version(), 'tools': agent.tools or []}
    for session_id in {agent.session_id, tip}:
        worker.db.update_session_tool_names(session_id, pin)
    worker.db.update_conversation_model_config_value(agent.session_id, '_platform_tool_policy', lambda previous: signature)
    worker.event('tool_policy_updated', {'mode': policy['mode'], 'direct_tools': len(agent.tools or [])})


def platform_instructions(cfg):
    """Small platform contract; native Hermes supplies tools, memory and host context."""
    import sys
    host = ('Windows: visible apps use detached launch; Git Bash cannot reliably inspect Windows apps.'
            if sys.platform == 'win32' else
            'macOS: use native macOS tools; Windows/PowerShell commands do not apply.'
            if sys.platform == 'darwin' else
            'Use the native host tools and shell.')
    return (
        f'Working directory: {cfg["workspace"]}. Resolve relative paths here. '
        'Answer the current request; past tasks are context, not fresh instructions. '
        'Deferred tools remain available: use tool_describe for a known name, otherwise tool_search. '
        'Only claim outcomes confirmed by tool results. '
        'Link local documents with their exact Markdown path. HTML previews require static, self-contained HTML; no scripts/external assets. '
        'For web research use web_search/web_extract. Open visible apps only when requested, '
        'launch detached, verify once, then leave them open; never reopen an app the user closed. '
        'Automation browser tools do not verify a visible desktop window. '
        + host
    )


def discussion_prompt(cfg, normal):
    if cfg.get('application_context_scope') != 'focused_discussion':return normal
    return ('You are performing the supplied application role, not a repository development task. '
            'Use only the current business discussion and application evidence. Prior model claims are not verified facts. '
            'Return the requested response format. Do not execute actions during deliberation.\n'+
            cfg.get('system_prompt','')+'\n'+cfg.get('application_system_prompt',''))


def bind_discussion_context(agent, cfg):
    """Pure app deliberation has no host/repository prompt; native work is unchanged."""
    if cfg.get('application_context_scope') != 'focused_discussion': return
    from types import MethodType
    prompt = discussion_prompt(cfg, '')
    def build(instance, system_message=None):
        # Reused on compression rebuilds too: never call the native host/skill/plugin builder.
        instance._cached_system_prompt_static = prompt
        return prompt
    agent._build_system_prompt = MethodType(build, agent)
    agent._cached_system_prompt = None
    agent._cached_system_prompt_static = None
    agent.ephemeral_system_prompt = None
