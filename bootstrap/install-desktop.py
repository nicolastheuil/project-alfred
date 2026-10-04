"""Install a supervised, loopback-only Desktop endpoint without model calls."""
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess


def main():
    assert os.geteuid() == 0, 'root required'
    source = Path(__file__).resolve().parents[1]
    assert Path('/var/lib/alfred-agent/.hermes/profiles/alfred/config.yaml').exists(), 'compose Alfred profile first'
    token = Path('/etc/alfred/desktop.env')
    if not token.exists():
        fd = os.open(token, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write('HERMES_DASHBOARD_SESSION_TOKEN=' + secrets.token_urlsafe(48) + '\n')
    assert not token.is_symlink() and token.stat().st_uid == 0 and not token.stat().st_mode & 0o077, 'unsafe token file'
    shutil.copyfile(source / 'deploy/system/alfred-desktop.service', '/etc/systemd/system/alfred-desktop.service')
    runtime = json.loads((source / 'config/runtime.lock.json').read_text())
    inventory = Path('/etc/alfred/service-inventory.d')
    inventory.mkdir(mode=0o755, exist_ok=True)
    (inventory / 'desktop.json').write_text(json.dumps({'services': [
        {'unit': 'alfred-desktop.service', 'grace_seconds': 90, 'probes': [
            {'kind': 'http_json', 'url': 'http://127.0.0.1:9119/api/status', 'field': 'version',
             'expected': runtime['hermes']['version']}]}]}, indent=2) + '\n')
    rule = Path('/etc/sudoers.d/alfred-desktop')
    rule.write_text('alfred ALL=(root) NOPASSWD: /usr/local/sbin/alfred-service-control restart alfred-desktop.service\n')
    rule.chmod(0o440)
    subprocess.run(['visudo', '-cf', str(rule)], check=True)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'alfred-desktop.service'], check=True)
    print('Desktop backend installed on 127.0.0.1:9119. The session token stays outside Git.')


if __name__ == '__main__':
    main()
