#!/bin/bash
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo 'Run as root' >&2; exit 1; }
platform_root="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
install -d -m 0755 /etc/alfred /usr/local/lib/alfred
install -d -m 0700 /var/lib/alfred/monitor
chgrp alfred /var/lib/alfred
chmod 0750 /var/lib/alfred
install -m 0644 "$platform_root/deploy/runtime/service-monitor.py" /usr/local/lib/alfred/service-monitor.py
install -m 0755 "$platform_root/deploy/runtime/service-control.sh" /usr/local/sbin/alfred-service-control
install -m 0755 "$platform_root/deploy/runtime/repair-client.sh" /usr/local/bin/alfred-repair
install -m 0755 "$platform_root/deploy/runtime/service-status.sh" /usr/local/bin/alfred-service-status
install -m 0644 "$platform_root"/deploy/system/alfred-{runtime.slice,gateway.service,monitor.service,monitor.timer,recovery.service} /etc/systemd/system/
/opt/alfred/current/venv/bin/python - "$platform_root/config/service-inventory.json" <<'PY'
import json, pathlib, yaml
source = pathlib.Path(__import__('sys').argv[1])
inventory = json.loads(source.read_text())
config_path = pathlib.Path('/var/lib/alfred-agent/.hermes/profiles/alfred/config.yaml')
config = json.loads(config_path.read_text())
host_path = config_path.parents[2] / 'config.yaml'
host = yaml.safe_load(host_path.read_text()) if host_path.exists() else {}
host.setdefault('gateway', {}).update(systemd_watchdog_seconds=120, loop_watchdog=True, multiplex_profiles=True)
host['kanban'] = config['kanban']
host_path.write_text(json.dumps(host, ensure_ascii=False, indent=2) + '\n')
gateway = inventory['services'][0]
gateway['probes'] = [gateway['probes'][0]]
platforms = config.get('platforms', {})
if platforms.get('whatsapp', {}).get('enabled') or host.get('platforms', {}).get('whatsapp', {}).get('enabled'):
    gateway['probes'].append({'kind': 'http_json', 'url': 'http://127.0.0.1:3000/health', 'field': 'status', 'expected': 'connected'})
if platforms.get('teams', {}).get('enabled') or host.get('platforms', {}).get('teams', {}).get('enabled'):
    gateway['probes'].append({'kind': 'tcp', 'host': '127.0.0.1', 'port': 8645})
pathlib.Path('/etc/alfred/service-inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
PY
printf '%s\n' 'alfred ALL=(root) NOPASSWD: /usr/local/sbin/alfred-service-control restart alfred-gateway.service, /usr/local/sbin/alfred-service-control restart zramswap.service' > /etc/sudoers.d/alfred-service-control
chmod 0440 /etc/sudoers.d/alfred-service-control
visudo -cf /etc/sudoers.d/alfred-service-control
systemd-analyze verify /etc/systemd/system/alfred-{gateway.service,monitor.service,monitor.timer,recovery.service,runtime.slice}
systemctl daemon-reload
systemctl enable alfred-gateway.service alfred-monitor.timer
systemctl start --no-block alfred-gateway.service
systemctl start alfred-monitor.timer
