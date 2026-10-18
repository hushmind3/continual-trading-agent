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
