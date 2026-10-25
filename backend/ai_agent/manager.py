"""Collect original application middle menus for the AI Agent large menu."""
from importlib import import_module

_MANAGERS = {'hermes_original': 'HermesOriginal', 'openclaw_original': 'OpenClawOriginal',
             'token_optimizer': 'TokenOptimizer'}

def __getattr__(name):
    if name not in _MANAGERS:
        raise AttributeError(name)
    return import_module('.' + _MANAGERS[name] + '.manager', __package__)
