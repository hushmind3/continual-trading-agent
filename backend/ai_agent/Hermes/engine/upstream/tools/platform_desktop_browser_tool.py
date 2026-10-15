"""Platform extension adapter, not original Hermes source.

Use the original discovery/registration path so profile-scoped registries replay it.
"""
import os
from tools.registry import registry
from ai_agent.Hermes.chat.desktop_browser import SCHEMA, launch
registry.register(name='desktop_browser',toolset='computer_use',schema=SCHEMA,handler=launch,
    check_fn=lambda:os.name=='nt')

from toolsets import TOOLSETS, _resolve_toolset_memo
if 'desktop_browser' not in TOOLSETS['computer_use']['tools']:
    TOOLSETS['computer_use']['tools'].append('desktop_browser')
_resolve_toolset_memo.clear()
