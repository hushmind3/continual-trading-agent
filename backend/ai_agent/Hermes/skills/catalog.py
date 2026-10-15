"""Native skill catalog, activation and editor operations."""
def execute(worker,operation,payload):
    from tools.skills_tool import _find_all_skills
    from hermes_cli.skills_config import get_disabled_skills,save_disabled_skills
    from agent.skill_utils import ESSENTIAL_SKILLS
    if operation=='skills':
        disabled=get_disabled_skills(worker.native_config())
        rows=_find_all_skills(skip_disabled=True)
        return {'skills':[{**row,'enabled':row['name'] not in disabled,'essential':row['name'] in ESSENTIAL_SKILLS} for row in rows]}
    if operation=='skill/toggle':
        worker.idle_required()
        name=str(payload.get('name') or '')
        if name not in {r['name'] for r in _find_all_skills(skip_disabled=True)}:raise ValueError('스킬을 찾을 수 없습니다.')
        cfg=worker.native_config();disabled=get_disabled_skills(cfg)
        if payload.get('enabled'):disabled.discard(name)
        else:disabled.add(name)
        save_disabled_skills(cfg,disabled)
        return execute(worker,'skills',{})
    if operation=='skill/save':
        worker.idle_required()
        from tools.skill_manager_tool import _create_skill,_edit_skill
        name=str(payload.get('name') or '')
        content=str(payload.get('content') or '')
        result=_create_skill(name,content,payload.get('category') or None) if payload.get('create') else _edit_skill(name,content)
        if not result.get('success'):raise ValueError(str(result.get('error') or '스킬을 저장하지 못했습니다.'))
        return result
    if operation=='skill/content':
        from tools.skill_manager_tool import _find_skill
        found=_find_skill(str(payload.get('name') or ''))
        if not found:raise ValueError('스킬을 찾을 수 없습니다.')
        return {'content':(found['path']/'SKILL.md').read_text(encoding='utf-8-sig')}
    raise ValueError('지원하지 않는 스킬 작업입니다.')
