"""Check effective tool selection and discovery with the installed Hermes, no model call.

Run as the service account with HERMES_HOME set to the profile being checked.
--context7-live performs public documentation requests and tests an HTTP failure.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--hermes-source', default='/opt/alfred/current')
parser.add_argument('--context7-live', action='store_true')
args = parser.parse_args()
sys.path.insert(0, args.hermes_source)
from hermes_cli.tools_config import _get_platform_tools
import model_tools
from tools.mcp_tool_discovery import discover_mcp_tools
from tools.mcp_tool_lifecycle import shutdown_mcp_servers
from tools.registry import registry
from tools.tool_search import dispatch_tool_search

home = Path(os.environ['HERMES_HOME'])
config = json.loads((home / 'config.yaml').read_text())
if args.context7_live:
    assert 'context7' in config.get('mcp_servers', {})
    discover_mcp_tools(['context7'])
sets = _get_platform_tools(config, 'cli')
raw = model_tools.get_tool_definitions(enabled_toolsets=sorted(sets),
    disabled_toolsets=config['agent']['disabled_toolsets'], quiet_mode=True,
    skip_tool_search_assembly=True)
wire = model_tools.get_tool_definitions(enabled_toolsets=sorted(sets),
    disabled_toolsets=config['agent']['disabled_toolsets'], quiet_mode=True)
names = [item['function']['name'] for item in raw]
assert 'delegate_task' not in names and 'execute_code' not in names
searches = {}
for query in ('kanban_create', 'kanban_complete', 'process_manage'):
    if query not in names:
        continue
    value = dispatch_tool_search({'queries': [query], 'limit': 5}, current_tool_defs=raw)
    text = value if isinstance(value, str) else json.dumps(value)
    parsed = json.loads(text)
    assert 'error' not in parsed and query in text, 'Native discovery lost a required tool'
    searches[query] = True
report = {'profile': home.name, 'raw_tools': len(raw), 'wire_tools': len(wire),
          'raw_schema_chars': len(json.dumps(raw)), 'wire_schema_chars': len(json.dumps(wire)),
          'recursive_delegation_available': False, 'discovery': searches,
          'model_calls': 0}
if args.context7_live:
    resolve = registry.dispatch('mcp__context7__resolve_library_id',
        {'libraryName': 'Python', 'query': 'Python 3.11 asyncio.TaskGroup version documentation'})
    resolved = json.loads(resolve) if isinstance(resolve, str) else resolve
    assert 'error' not in resolved and '/python/cpython' in str(resolved)
    docs = registry.dispatch('mcp__context7__query_docs',
        {'libraryId': '/python/cpython/v3.11.14', 'query': 'asyncio.TaskGroup create_task signature'})
    docs = json.loads(docs) if isinstance(docs, str) else docs
    assert 'error' not in docs and 'blob/v3.11.14/' in str(docs)
    async def unavailable():
        from mcp.client.streamable_http import streamable_http_client
        from mcp import ClientSession
        try:
            async with streamable_http_client('http://127.0.0.1:1/mcp') as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    return False
        except Exception:
            return True
    failed = asyncio.run(asyncio.wait_for(unavailable(), timeout=5))
    assert failed
    with urllib.request.urlopen('https://docs.python.org/3.11/library/asyncio-task.html', timeout=20) as response:
        official = response.read()
    assert b'asyncio.TaskGroup' in official
    report['context7'] = {'resolver': True, 'versioned_reference': True,
                          'unavailable_endpoint_detected': failed, 'official_fallback_reachable': True,
                          'autonomous_fallback_mission_tested': False}
shutdown_mcp_servers()
print(json.dumps(report))
