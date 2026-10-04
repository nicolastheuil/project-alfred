"""Install reviewed methods, isolated linter and role-scoped remote documentation.

Run after native profiles exist. Does not change credentials or model routing.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Root required for immutable tool installation')
    import yaml
    source = args.source.resolve()
    lock = json.loads((source / 'config/modules.lock.json').read_text())
    home = Path('/var/lib/alfred-agent/.hermes')
    account = pwd.getpwnam('alfred')
    lint = Path('/opt/alfred/extensions/lintlang/venv')
    if not lint.exists():
        subprocess.run(['/opt/alfred/tools/uv', 'venv', '--python', '/opt/alfred/current/venv/bin/python', str(lint)], check=True)
    subprocess.run(['/opt/alfred/tools/uv', 'pip', 'install', '--python', str(lint / 'bin/python'),
                    '--require-hashes', '--only-binary', ':all:', '-r', str(source / lock['lintlang']['requirements'])], check=True)
    launcher = Path('/usr/local/bin/alfred-lint')
    launcher.write_text('#!/bin/sh\nexec /opt/alfred/extensions/lintlang/venv/bin/lintlang "$@"\n')
    launcher.chmod(0o755)
    changes = {}
    targets = [home] + sorted(p for p in (home / 'profiles').iterdir() if p.is_dir())
    for folder in targets:
        config_path = folder / 'config.yaml'
        if folder.is_symlink() or config_path.is_symlink():
            raise SystemExit('Symlink config refused')
        config = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}
        name = folder.name if folder != home else 'default'
        selected = ['terminal', 'file', 'memory', 'skills', 'clarify'] if name in ('default', 'alfred') else ['terminal', 'file', 'memory', 'skills', 'kanban', 'web', 'todo']
        config.pop('disabled_toolsets', None)
        config.pop('toolsets', None)
        config.pop('delegation', None)
        config.setdefault('agent', {})['disabled_toolsets'] = lock['excluded_toolsets']
        config.setdefault('tools', {})['tool_search'] = {'enabled': 'off' if name in ('default', 'alfred') else 'on', 'defer': lock['native_tool_search_defer'], 'listing': 'on', 'listing_max_tokens': 1500}
        config['platform_toolsets'] = {platform: selected for platform in ('cli', 'whatsapp', 'teams', 'acp')}
        methods = []
        if name not in ('alfred', 'default'):
            methods = list(lock['ecc']['skills'])
        if name in lock['context7']['profiles']:
            config.setdefault('mcp_servers', {})['context7'] = {
                'url': lock['context7']['endpoint'], 'lazy': True, 'trust': 'full',
                'tools': {'include': lock['context7']['tools'], 'resources': False, 'prompts': False}}
            methods.append('context7-documentation')
        if name in ('qa', 'documentaliste'):
            methods.append('configuration-lint')
        # Preserve private, reviewed local MCP servers, but remove a non-existent option.
        for server in config.get('mcp_servers', {}).values():
            server.pop('trusted', None)
        for skill in methods:
            src = source / 'skills' / skill
            destination = folder / 'skills' / skill
            if destination.is_symlink():
                raise SystemExit('Symlink skill refused')
            destination.mkdir(parents=True, exist_ok=True)
            for item in src.iterdir():
                if item.is_symlink() or not item.is_file():
                    raise SystemExit('Only regular reviewed skill files are accepted')
                target = destination / item.name
                if target.is_symlink():
                    raise SystemExit('Symlink skill file refused')
                shutil.copyfile(item, target)
                os.chown(target, account.pw_uid, account.pw_gid)
                target.chmod(0o600)
            os.chown(destination.parent, account.pw_uid, account.pw_gid)
            os.chown(destination, account.pw_uid, account.pw_gid)
            destination.chmod(0o700)
        if config_path.exists():
            backup = Path('/var/lib/alfred/module-config-backups')
            backup.mkdir(mode=0o700, parents=True, exist_ok=True)
            digest = hashlib.sha256(config_path.read_bytes()).hexdigest()
            saved = backup / (name + '-' + digest[:12] + '.yaml')
            if not saved.exists():
                saved.write_bytes(config_path.read_bytes())
                saved.chmod(0o600)
        with tempfile.NamedTemporaryFile(dir=folder, delete=False) as output:
            output.write((json.dumps(config, indent=2, ensure_ascii=False) + '\n').encode())
            temporary = Path(output.name)
        os.chown(temporary, account.pw_uid, account.pw_gid)
        temporary.chmod(0o600)
        os.replace(temporary, config_path)
        changes[name] = {'toolsets': selected, 'skills': methods,
                         'mcp_servers': sorted(config.get('mcp_servers', {}))}
    report = {'schema_version': 1, 'lintlang': lock['lintlang']['version'], 'profiles': changes,
              'resident_services_added': 0, 'filesystem_isolation': False}
    Path('/var/lib/alfred/modules-manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
