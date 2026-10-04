"""Enable the user manager required by native Hermes restart-safe worker scopes."""
import json
import os
from pathlib import Path
import pwd
import subprocess

def main():
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    account = pwd.getpwnam('alfred')
    subprocess.run(['apt-get', 'install', '-y', 'dbus-user-session'], check=True)
    directory = Path(f'/etc/systemd/system/user@{account.pw_uid}.service.d')
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'alfred.conf').write_text('[Service]\nSlice=alfred-runtime.slice\n')
    gateway = Path('/etc/systemd/system/alfred-gateway.service.d')
    gateway.mkdir(parents=True, exist_ok=True)
    (gateway / 'workers.conf').write_text(f'[Unit]\nWants=user@{account.pw_uid}.service\nAfter=user@{account.pw_uid}.service\n\n[Service]\nProtectHome=tmpfs\nBindReadOnlyPaths=/run/user/{account.pw_uid}\n')
    monitor = Path('/etc/systemd/system/alfred-monitor.service.d')
    monitor.mkdir(parents=True, exist_ok=True)
    (monitor / 'workers.conf').write_text(f'[Service]\nProtectHome=tmpfs\nBindReadOnlyPaths=/run/user/{account.pw_uid}\n')
    subprocess.run(['loginctl', 'enable-linger', account.pw_name], check=True)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'start', f'user@{account.pw_uid}.service'], check=True)
    env = dict(os.environ, XDG_RUNTIME_DIR=f'/run/user/{account.pw_uid}',
               DBUS_SESSION_BUS_ADDRESS=f'unix:path=/run/user/{account.pw_uid}/bus')
    subprocess.run(['runuser', '-u', account.pw_name, '--', 'systemd-run', '--user', '--scope', '--quiet',
                    '--collect', '--unit=alfred-bootstrap-worker-probe', '/bin/true'], env=env, check=True)
    extension = Path('/etc/alfred/service-inventory.d/workers.json')
    extension.parent.mkdir(parents=True, exist_ok=True)
    extension.write_text(json.dumps({'services': [{'unit': f'user@{account.pw_uid}.service',
        'auto_restart': True, 'probes': [{'kind': 'unix_socket', 'path': f'/run/user/{account.pw_uid}/bus'}]}]}, indent=2) + '\n')
    print(json.dumps({'worker_scope_probe': True, 'linger': True, 'shared_resource_slice': 'alfred-runtime.slice'}))

if __name__ == '__main__':
    main()
