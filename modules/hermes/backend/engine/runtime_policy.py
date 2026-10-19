"""User-controlled model settings and native tool discovery, without removing capabilities."""
def model_options(settings, native):
    from .execution import context_window
    saved=(settings.get('model_options') or {}).get(settings['model'],{})
    return {'context_length':saved.get('context_length',context_window(native,settings['model'])),
            'thinking_mode':saved.get('thinking_mode','auto')}

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
    if saved:
        if not settings.get('model'):raise ValueError('설정할 모델을 먼저 선택하세요.')
        settings['model_options']={**(settings.get('model_options') or {}),settings['model']:saved}
    if settings.get('tool_loading') not in ('native','lazy','eager'):
        raise ValueError('도구 설명 불러오기 설정을 확인하세요.')
    return settings

def configure_tools(worker, mode):
    from hermes_cli.config_defaults import DEFAULT_CONFIG
    from tools.registry import registry
    native=worker.native_config()
    search=native.setdefault('tools',{}).setdefault('tool_search',{})
    search['enabled']='off' if mode=='eager' else 'auto'
    search['defer']=sorted(registry.get_tool_to_toolset_map()) if mode=='lazy' else (
        list(DEFAULT_CONFIG['tools']['tool_search']['defer']) if mode=='native' else [])
    worker.write_config(native)

def apply_thinking(agent, options, local):
    if not local or options['thinking_mode']=='auto':return
    overrides=dict(getattr(agent,'request_overrides',{}) or {})
    extra=dict(overrides.get('extra_body') or {})
    template=dict(extra.get('chat_template_kwargs') or {})
    template['enable_thinking']=options['thinking_mode']=='on'
    extra['chat_template_kwargs']=template;overrides['extra_body']=extra
    agent.request_overrides=overrides


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
