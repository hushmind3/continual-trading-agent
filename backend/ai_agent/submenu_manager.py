from platform_modules import registrations
_entries=[entry for item,entry in registrations() if item['group']['id']=='ai_agent']
MENUS=tuple(entry.MENU for entry in _entries)
ROUTERS=tuple(entry.router for entry in _entries)
