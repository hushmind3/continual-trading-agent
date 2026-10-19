"""Keep native model API policy independent from the optional Hermes transport."""
import ast
import functools
import inspect
import os


def response_timeout(config):
    import httpx
    value=os.getenv('PROJECT_ZERO_RESPONSE_TIMEOUT_SECONDS') or config().get('response_timeout_seconds',300)
    try:seconds=float(value)
    except (ValueError,TypeError):raise ValueError('모델 응답 대기 시간은 5~900초 숫자로 설정하세요.')
    if not 5<=seconds<=900:raise ValueError('모델 응답 대기 시간은 5~900초로 설정하세요.')
    return httpx.Timeout(connect=10,read=seconds,write=30,pool=30)


def install():
    import ai_provider as provider
    if getattr(provider,'platform_harness_connected',False):return
    if __package__:
        from .project_zero_roles import system_persona
        from .project_zero_business import discussion_context
    else:
        from project_zero_roles import system_persona
        from project_zero_business import discussion_context
    original=provider.compose
    if original.__module__=='ai_provider':
        tree=ast.parse(inspect.getsource(original));changed=0
        for node in ast.walk(tree):
            if isinstance(node,ast.keyword) and node.arg=='timeout' and isinstance(node.value,ast.Constant) and node.value.value==100:
                node.value=ast.parse('_platform_response_timeout()',mode='eval').body;changed+=1
        if changed!=1:raise ValueError('원본 모델 API 대기 시간 구성이 바뀌어 호환 확인이 필요합니다.')
        provider._platform_response_timeout=lambda:response_timeout(provider.runtime_config)
        exec(compile(ast.fix_missing_locations(tree),inspect.getfile(original),'exec'),provider.__dict__)
        original=provider.compose
    signature=inspect.signature(original)
    @functools.wraps(original)
    async def compose(*args,**kwargs):
        arguments=signature.bind(*args,**kwargs);arguments.apply_defaults()
        system,user=arguments.arguments['system'],arguments.arguments['user']
        scope=provider.platform_request_options(system,user)['context_scope']
        system,user=discussion_context(system_persona(system),user,scope)
        arguments.arguments.update(system=system,user=user)
        activity=getattr(provider,'platform_activity',lambda delta:None)
        activity(1)
        try:result=await original(*arguments.args,**arguments.kwargs)
        finally:activity(-1)
        if result is None:raise ValueError('설정된 모델의 응답이 없어 작업을 생성하지 않았습니다.')
        return result
    provider.compose=compose
