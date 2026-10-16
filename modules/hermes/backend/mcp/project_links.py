"""Merge platform-installed project servers into the original Hermes MCP registry."""
import re


def synchronize(worker, request):
    key = str(request.get('id', ''))
    if not re.fullmatch(r'p_[a-z0-9_-]{1,98}', key): raise ValueError('설치된 프로젝트 ID가 올바르지 않습니다.')
    name = 'platform_' + key
    config = worker.native_config()
    servers = dict(config.get('mcp_servers', {}))
    removing = bool(request.get('remove'))
    if removing:
        if name not in servers: return {'name': name, 'connected': False, 'tools': 0}
        worker.idle_required(); servers.pop(name)
    else:
        server = request.get('server')
        if not isinstance(server, dict) or not server.get('command') or not isinstance(server.get('args'), list):
            raise ValueError('프로젝트 MCP 실행 설정이 없습니다.')
        from tools import mcp_tool
        count = sum(value == name for value in mcp_tool._mcp_tool_server_names.values())
        if servers.get(name) == server and count:
            return {'name': name, 'connected': True, 'tools': count, 'tool_names': sorted(tool for tool, owner in mcp_tool._mcp_tool_server_names.items() if owner == name)}
        worker.idle_required(); servers[name] = server
    worker.mcp_save({'servers': servers})
    if removing: return {'name': name, 'connected': False, 'tools': 0}
    from tools.mcp_tool_discovery import discover_mcp_tools
    from tools import mcp_tool
    discover_mcp_tools()
    count = sum(value == name for value in mcp_tool._mcp_tool_server_names.values())
    if not count: raise ValueError('프로젝트 MCP를 Hermes에 연결했지만 사용 가능한 도구를 발견하지 못했습니다.')
    return {'name': name, 'connected': True, 'tools': count, 'tool_names': sorted(tool for tool, owner in mcp_tool._mcp_tool_server_names.items() if owner == name)}
