"""Collect Certbot DNS challenges for an operator-managed DNS zone.

Root-only state outside Git. The operator confirms after publishing both TXT records.
"""
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time

ROOT = Path('/var/lib/alfred/acme-manual')
STATE = ROOT / 'challenges.json'
CONFIRM = ROOT / 'confirmed'


def write_state(value):
    fd = os.open(STATE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(value, f, indent=2)


def main():
    assert os.geteuid() == 0, 'root required'
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert not ROOT.is_symlink() and ROOT.stat().st_uid == 0 and not ROOT.stat().st_mode & 0o077
    action = sys.argv[1] if len(sys.argv) > 1 else 'hook'
    if action == 'begin':
        if CONFIRM.exists():
            CONFIRM.unlink()
        write_state({'run_id': secrets.token_hex(16), 'started_at': time.time(), 'records': {}, 'awaiting_dns': False})
        return
    value = json.loads(STATE.read_text())
    if action == 'finish':
        value['completed'] = True
        value['awaiting_dns'] = False
        write_state(value)
        if CONFIRM.exists():
            CONFIRM.unlink()
        return
    if action == 'confirm':
        assert value['awaiting_dns'] and value['records'], 'No pending challenge'
        fd = os.open(CONFIRM, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(value['run_id'])
        return
    if action == 'hook':
        assert not value.get('completed') and time.time() - value['started_at'] < 3600, 'Begin a fresh operator-managed challenge first'
        domain = os.environ['CERTBOT_DOMAIN']
        token = os.environ['CERTBOT_VALIDATION']
        assert re.fullmatch(r'[A-Za-z0-9.-]{1,253}', domain)
        assert re.fullmatch(r'[A-Za-z0-9_-]{20,256}', token)
        value['records']['_acme-challenge.' + domain] = token
        value['awaiting_dns'] = os.environ.get('CERTBOT_REMAINING_CHALLENGES', '0') == '0'
        write_state(value)
        if value['awaiting_dns']:
            deadline = time.monotonic() + 1800
            while time.monotonic() < deadline:
                if CONFIRM.exists() and CONFIRM.read_text() == value['run_id']:
                    return
                time.sleep(2)
            raise RuntimeError('Operator DNS confirmation timed out')
        return
    raise ValueError('Unsupported action')


if __name__ == '__main__':
    main()
