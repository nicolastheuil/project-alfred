"""Bounded service recovery. Root-owned code/config; no shell or model on healthy ticks."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import pwd
import re
import socket
import ssl
import uuid
import subprocess
import time
from datetime import datetime, timezone
from urllib.request import urlopen

HOME = Path('/var/lib/alfred-agent/.hermes')
STATE = Path('/var/lib/alfred/monitor')
INVENTORY = Path('/etc/alfred/service-inventory.json')
EXTENSIONS = Path('/etc/alfred/service-inventory.d')
INCIDENTS = HOME / 'shared/missions/platform-incidents'


def run(argv, timeout=20, check=False):
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                          check=check, env={'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8'})


def write_json(path, data, agent=False):
    # Agent-writable evidence directories must never redirect root writes through symlinks.
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.absolute().parent.parts[1:]:
            try:
                os.mkdir(part, 0o700, dir_fd=directory)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        temp_name = path.name + '.new'
        fd = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            if agent:
                account = pwd.getpwnam('alfred')
                os.fchown(stream.fileno(), account.pw_uid, account.pw_gid)
                os.fchown(directory, account.pw_uid, account.pw_gid)
            stream.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path.name, src_dir_fd=directory, dst_dir_fd=directory)
    finally:
        os.close(directory)


def load(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default


def load_inventory():
    inventory = load(INVENTORY, {})
    services = list(inventory.get('services', []))
    units = {item['unit'] for item in services}
    for path in sorted(EXTENSIONS.glob('*.json')):
        for item in load(path, {}).get('services', []):
            if item['unit'] in units:
                raise ValueError('Duplicate extension unit')
            units.add(item['unit'])
            services.append(item)
    inventory['services'] = services
    return inventory


def properties(unit):
    output = run(['systemctl', 'show', unit, '--property=LoadState,ActiveState,SubState,Result,NRestarts,ActiveEnterTimestampMonotonic']).stdout
    return dict(line.split('=', 1) for line in output.splitlines() if '=' in line)


def probe(item):
    kind = item['kind']
    if kind == 'heartbeat':
        value = load(Path(item['path']), {})
        stamp = datetime.fromisoformat(value[item.get('timestamp_field', 'updated_at')].replace('Z', '+00:00')).timestamp()
        if not -10 <= time.time() - stamp <= item['max_age']:
            raise ValueError('heartbeat stale')
    elif kind == 'http_json':
        with urlopen(item['url'], timeout=4) as response:
            value = json.load(response)
        if value.get(item['field']) != item['expected']:
            raise ValueError('channel disconnected')
    elif kind == 'tcp':
        with socket.create_connection((item['host'], item['port']), timeout=4):
            pass
    elif kind == 'unix_socket':
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(4)
            connection.connect(item['path'])
    elif kind == 'tls':
        context = ssl.create_default_context()
        with socket.create_connection((item['host'], item['port']), timeout=4) as connection:
            with context.wrap_socket(connection, server_hostname=item['server_name']) as secured:
                remaining = ssl.cert_time_to_seconds(secured.getpeercert()['notAfter']) - time.time()
                if remaining < item.get('min_validity_seconds', 1209600):
                    raise ValueError('TLS certificate renewal required')
    elif kind == 'zram':
        if '/dev/zram0' not in Path('/proc/swaps').read_text():
            raise ValueError('zram swap missing')
    else:
        raise ValueError('unknown health probe')


def health(service):
    prop = properties(service['unit'])
    if service.get('kind') == 'job' and prop.get('LoadState') == 'loaded':
        return (prop.get('Result') in ('success', ''), 'job_' + prop.get('Result', 'unknown'), prop)
    if prop.get('LoadState') != 'loaded' or prop.get('ActiveState') != 'active':
        return False, 'service_inactive', prop
    entered = int(prop.get('ActiveEnterTimestampMonotonic') or 0) / 1_000_000
    if entered and time.monotonic() - entered < service.get('grace_seconds', 0):
        return True, 'startup_grace', prop
    for number, item in enumerate(service.get('probes', [])):
        try:
            probe(item)
        except Exception:
            # Never persist HTTP responses or exception strings: these can contain credentials.
            return False, f'probe_{number}_{item["kind"]}_failed', prop
    return True, 'healthy', prop


def bounded_restart(unit, history, limit, now):
    attempts = [stamp for stamp in history.get('restarts', []) if now - stamp < 3600]
    history['restarts'] = attempts
    if len(attempts) >= limit:
        return False
    attempts.append(now)  # Account for failed commands too.
    run(['systemctl', 'reset-failed', unit])
    result = run(['systemctl', 'restart', '--no-block', unit])
    return result.returncode == 0


def queue_incident(service, history, reason, prop, gateway_healthy):
    episode = history.setdefault('episode', f'inc-{uuid.uuid4().hex[:12]}-{service["unit"]}')
    folder = INCIDENTS / episode
    path = folder / 'incident.json'
    incident = {'id': episode, 'unit': service['unit'], 'reason': reason,
                'status': 'open', 'at': datetime.now(timezone.utc).isoformat(),
                'restart_attempts': history.get('restarts', []), 'systemd': prop,
                'folder': str(folder), 'task_id': history.get('task_id')}
    if history.get('test_context'):
        incident['test_context'] = history['test_context']
    write_json(path, incident, agent=True)
    # Task body is evidence, not authorization for arbitrary privileged commands.
    if not history.get('task_id'):
        result = run(['/usr/sbin/runuser', '-u', 'alfred', '--', '/usr/local/bin/hermes',
                      '-p', 'platform-engineer', 'kanban', '--board', 'default', 'create',
                      f'Incident plateforme : {service["unit"]}', '--assignee', 'platform-engineer',
                      '--created-by', 'service-monitor', '--body',
                      f'Incident {episode}. Lire {path}. Diagnostiquer, reparer dans les droits effectifs, '
                      'verifier la sante puis transmettre les preuves a Alfred. Bloquer si intervention humaine requise.',
                      '--priority', '100', '--max-runtime', '240', '--max-retries', '1',
                      '--initial-status', 'running' if gateway_healthy else 'blocked',
                      '--idempotency-key', f'platform-incident:{episode}', '--json'], timeout=30)
        if result.returncode == 0:
            history['task_id'] = json.loads(result.stdout)['id']
            incident['task_id'] = history['task_id']
            write_json(path, incident, agent=True)
    write_json(INCIDENTS / 'latest.json', incident, agent=True)
    if history.get('task_id') and not gateway_healthy and not history.get('fallback_dispatched'):
        # The gateway cannot be the sole path to repair its own failure.
        history['fallback_pending'] = True


def safe_queue_incident(service, history, reason, prop, gateway_healthy):
    try:
        queue_incident(service, history, reason, prop, gateway_healthy)
        history.pop('queue_error', None)
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError):
        # Preserve the episode for the next tick. Never store exception payloads.
        history['queue_error'] = 'incident_delivery_failed'


def tick(inventory, state):
    now = time.time()
    checks = {service['unit']: health(service) for service in inventory['services']}
    gateway_healthy = checks.get('alfred-gateway.service', (False,))[0]
    report = []
    for service in inventory['services']:
        unit = service['unit']
        ok, reason, prop = checks[unit]
        history = state.setdefault(unit, {'strikes': 0, 'restarts': []})
        if ok:
            if reason in ('healthy', 'job_success') and history.get('episode'):
                episode = history['episode']
                incident_path = INCIDENTS / episode / 'incident.json'
                incident = {'id': episode, 'unit': unit, 'task_id': history.get('task_id'),
                            'status': 'recovered', 'recovered_at': datetime.now(timezone.utc).isoformat()}
                write_json(incident_path, incident, agent=True)
                history['last_episode'] = episode
                for key in ('episode', 'task_id', 'fallback_dispatched'):
                    history.pop(key, None)
            history['strikes'] = 0
        else:
            history['strikes'] += 1
            if history['strikes'] >= inventory['failure_threshold']:
                cooldown = history.get('restarts', [0])[-1] if history.get('restarts') else 0
                if now - cooldown >= 180:
                    attempted = service.get('auto_restart', True) and bounded_restart(unit, history, inventory['restart_limit_per_hour'], now)
                    if not attempted:
                        safe_queue_incident(service, history, reason, prop, gateway_healthy)
        # Catch repeated native restarts even when the probe happens to sample a healthy interval.
        native = int(prop.get('NRestarts') or 0)
        window = history.setdefault('native_window', {'at': now, 'baseline': native})
        if now - window['at'] >= 3600 or native < window['baseline']:
            window.update(at=now, baseline=native)
        if native - window['baseline'] >= 3 and native > history.get('native_escalated', -1):
            safe_queue_incident(service, history, 'repeated_native_restarts', prop, gateway_healthy)
            history['native_escalated'] = native
        history.update(last_check=now, healthy=ok, reason=reason)
        report.append({'unit': unit, 'healthy': ok, 'reason': reason,
                       'strikes': history['strikes'], 'task_id': history.get('task_id')})
    write_json(STATE / 'state.json', state)
    write_json(STATE / 'health.json', {'at': datetime.now(timezone.utc).isoformat(), 'services': report})
    write_json(INCIDENTS / 'pending.json', {'incidents': [
        {'unit': unit, 'id': item['episode'], 'task_id': item.get('task_id'),
         'folder': str(INCIDENTS / item['episode'])}
        for unit, item in state.items() if item.get('episode')
    ]}, agent=True)
    pending = [item for item in state.values() if item.get('fallback_pending') and not item.get('fallback_dispatched')]
    if pending and properties('alfred-recovery.service').get('ActiveState') not in ('active', 'activating'):
        result = run(['systemctl', 'start', '--no-block', 'alfred-recovery.service'])
        if result.returncode == 0:
            for item in pending:
                item['fallback_dispatched'] = True
                item.pop('fallback_pending', None)
            write_json(STATE / 'state.json', state)
    print(json.dumps(report))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--restart', metavar='UNIT')
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()
    if args.status:
        inventory = load_inventory()
        for service in inventory['services']:
            ok, reason, prop = health(service)
            print(json.dumps({'at': datetime.now(timezone.utc).isoformat(), 'unit': service['unit'],
                              'healthy': ok, 'reason': reason, 'systemd': prop,
                              'checked_probes': [item['kind'] for item in service.get('probes', [])]}))
        return
    if os.geteuid() != 0:
        raise SystemExit('Root required; agents must use the restricted service-control wrapper')
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    inventory = load_inventory()
    units = {item['unit'] for item in inventory['services']}
    if any(not re.fullmatch(r'[a-zA-Z0-9_.@-]+\.(service|timer)', unit) for unit in units):
        raise SystemExit('Invalid unit inventory')
    with (STATE / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load(STATE / 'state.json', {})
        if args.restart:
            if args.restart not in units or args.restart == 'alfred-monitor.timer':
                raise SystemExit('Unit not authorized for agent restart')
            history = state.setdefault(args.restart, {'strikes': 0, 'restarts': []})
            ok = bounded_restart(args.restart, history, inventory['restart_limit_per_hour'], time.time())
            write_json(STATE / 'state.json', state)
            print('Restart requested' if ok else 'Restart budget exhausted')
            raise SystemExit(0 if ok else 1)
        tick(inventory, state)
        account = pwd.getpwnam('alfred')
        os.chown(STATE, 0, account.pw_gid)
        STATE.chmod(0o750)
        os.chown(STATE / 'health.json', 0, account.pw_gid)
        (STATE / 'health.json').chmod(0o640)


if __name__ == '__main__':
    main()
