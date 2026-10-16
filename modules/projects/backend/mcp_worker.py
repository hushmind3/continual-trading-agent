"""Private JSON-line MCP client; no extra HTTP listener and no model dependency."""
import asyncio
from contextlib import AsyncExitStack
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    command = json.loads(sys.argv[1])
    async with AsyncExitStack() as stack:
        incoming, outgoing = await stack.enter_async_context(stdio_client(StdioServerParameters(
            command=command[0], args=command[1:], cwd=str(Path.cwd()), env=dict(os.environ))))
        client = await stack.enter_async_context(ClientSession(incoming, outgoing))
        await asyncio.wait_for(client.initialize(), 60)
        while line := await asyncio.to_thread(sys.stdin.readline):
            try:
                request = json.loads(line)
                if request.get('operation') == 'list':
                    result = await asyncio.wait_for(client.list_tools(), 60)
                elif request.get('operation') == 'call':
                    result = await asyncio.wait_for(client.call_tool(request['name'], request.get('arguments', {})), 60)
                else: raise ValueError('지원하지 않는 MCP 요청입니다.')
                response = result.model_dump(mode='json', by_alias=True)
            except Exception as exc: response = {'error': str(exc)}
            print(json.dumps(response, ensure_ascii=False), flush=True)


try: asyncio.run(main())
except Exception as exc:
    print(json.dumps({'error': str(exc)}, ensure_ascii=False), flush=True)
    sys.exit(1)
