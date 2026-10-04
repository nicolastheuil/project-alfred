"""Root-only Desktop password recovery; secrets never appear in stdout or argv."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess

LOGIN = Path('/var/lib/alfred/credentials/desktop-login.json')
ENV = Path('/etc/alfred/desktop-https.env')
REFERENCE = Path('/var/lib/alfred/credentials/desktop-vault-reference.json')
TOKEN = Path('/var/lib/alfred/credentials/op-service-account.json')


def secure_read(path):
    st = path.lstat()
    if path.is_symlink() or not path.is_file() or st.st_uid != os.geteuid() or st.st_mode & 0o077:
        raise ValueError('Unsafe recovery file')
    return path.read_text()


def write_private(path, value):
    temporary = path.with_suffix(path.suffix + '.recovery')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as f:
        os.fchmod(f.fileno(), 0o600)
        f.write(value)
    os.replace(temporary, path)


def hash_password(value):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(value.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return 'scrypt$16384$8$1$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(digest).decode()


def vault_get():
    ref = json.loads(secure_read(REFERENCE))
    token = json.loads(secure_read(TOKEN))['OP_SERVICE_ACCOUNT_TOKEN']
    env = dict(os.environ, OP_SERVICE_ACCOUNT_TOKEN=token, HOME=str(TOKEN.parent))
    args = ['/usr/bin/op', 'item', 'get', ref['item_id'], '--vault', ref['vault'], '--format', 'json']
    r = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
    if r.returncode:
        raise RuntimeError('Vault read failed')
    return json.loads(r.stdout), ref, env


def vault_put(item, ref, env):
    r = subprocess.run(['/usr/bin/op', 'item', 'edit', ref['item_id'], '--vault', ref['vault'], '--format', 'json'],
        input=json.dumps(item), env=env, capture_output=True, text=True, timeout=30)
    if r.returncode:
        raise RuntimeError('Vault update failed')


def restart():
    subprocess.run(['systemctl', 'restart', 'alfred-desktop.service'], check=True, capture_output=True, timeout=60)


def rotate(local_only=False):
    old_login, old_env = secure_read(LOGIN), secure_read(ENV)
    if 'HERMES_DASHBOARD_BASIC_AUTH_USERNAME=' not in old_env or 'HERMES_DASHBOARD_OAUTH_CLIENT_ID=' in old_env:
        raise ValueError('Local account is not the active provider')
    login = json.loads(old_login)
    login['password'], login['signing_secret'] = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    replacements = {'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH': hash_password(login['password']),
        'HERMES_DASHBOARD_BASIC_AUTH_SECRET': login['signing_secret']}
    lines = []
    for line in old_env.splitlines():
        key = line.partition('=')[0]
        lines.append(key + '=' + replacements.pop(key) if key in replacements else line)
    if replacements:
        raise ValueError('Incomplete auth environment')
    old_item = ref = vault_env = None
    if not local_only:
        old_item, ref, vault_env = vault_get()
        new_item = json.loads(json.dumps(old_item))
        fields = {f.get('id'): f for f in new_item['fields']}
        if 'password' not in fields or fields.get('username', {}).get('value') != login['username']:
            raise ValueError('Vault login identity mismatch')
        fields['password']['value'] = login['password']
        vault_put(new_item, ref, vault_env)  # No VM mutation if the vault cannot accept it.
    try:
        write_private(LOGIN, json.dumps(login))
        write_private(ENV, '\n'.join(lines) + '\n')
        restart()
    except Exception:
        write_private(LOGIN, old_login)
        write_private(ENV, old_env)
        if old_item is not None:
            vault_put(old_item, ref, vault_env)
        restart()
        raise
    return {'password_reset': True, 'sessions_invalidated': True, 'vault_updated': not local_only,
        'credentials_path': str(LOGIN), 'username': login['username']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rotate', action='store_true')
    parser.add_argument('--local-only', action='store_true')
    args = parser.parse_args()
    assert os.geteuid() == 0, 'Administrator root access required'
    if args.rotate:
        result = rotate(args.local_only)
    else:
        item, _, _ = vault_get()
        login = json.loads(secure_read(LOGIN))
        fields = {f.get('id'): f for f in item['fields']}
        result = {'vault_matches_local_login': fields.get('password', {}).get('value') == login['password']
            and fields.get('username', {}).get('value') == login['username'], 'password_reset': False}
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'recovery_failed': True, 'error_class': type(exc).__name__}))
        raise SystemExit(1)
