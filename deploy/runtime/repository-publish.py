"""Root-owned publication broker: fixed repositories, reviewed files, no token output.

Requests arrive as JSON on stdin. The operator installs credentials outside Git.
Agent workspaces contain sources only; authenticated Git processes and their
repositories run as root, with hooks disabled and no agent-supplied Git config.
"""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

CONFIG = Path('/etc/alfred/publication-runtime.json')
STATE = Path('/var/lib/alfred/publication')
ROOTS = {'platform': {'docs', 'config', 'examples', 'profiles', 'skills', 'tools', 'bootstrap', 'deploy', '.github'},
         'instance': {'docs', 'profiles', 'skills', 'tools', '.github'}}
ROOT_FILES = {'platform': {'README.md', 'AGENTS.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', '.gitignore', '.gitattributes'},
              'instance': {'README.md', 'AGENTS.md', '.gitignore', '.gitattributes', 'instance.json', 'publication.json', 'platform.lock.json'}}
FORBIDDEN_SUFFIXES = {'.key', '.pem', '.p12', '.pfx', '.ppk', '.db', '.sqlite', '.aes', '.age'}

def validate_relative(scope, name):
    path = Path(name)
    if not name or path.is_absolute() or '..' in path.parts or '\\' in name or re.search(r'[\x00-\x1f\x7f]', name):
        raise ValueError('invalid_source_path')
    if (len(path.parts) == 1 and name not in ROOT_FILES[scope]) or (len(path.parts) > 1 and path.parts[0] not in ROOTS[scope]):
        raise ValueError('path_outside_configured_scope')
    if any(p in {'.git', 'sessions', 'cache', 'logs', 'credentials', 'node_modules', '__pycache__'} or p.startswith('.env') for p in path.parts):
        raise ValueError('operational_or_credential_path')
    if path.suffix in FORBIDDEN_SUFFIXES or path.name in {'auth.json', 'credentials.json'}:
        raise ValueError('credential_or_data_file')
    if scope == 'platform' and path.name in {'USER.md', 'MEMORY.md', 'PROFESSIONAL.md'}:
        raise ValueError('personal_memory_in_public_scope')
    return path

def source_bytes(workspace, relative):
    directory = directory_fd(workspace / relative.parent)
    try:
        fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, 'rb') as source:
            metadata = os.fstat(source.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 1_000_000:
                raise ValueError('missing_or_oversized_source')
            content = source.read(1_000_001)
            if len(content) > 1_000_000:
                raise ValueError('oversized_source')
            return content
    finally:
        os.close(directory)

def directory_fd(path, create=False, account=None):
    """Walk every absolute directory with openat/O_NOFOLLOW, including parents."""
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('absolute_workspace_required')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            try:
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, 0o700, dir_fd=fd)
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                if account:
                    os.fchown(next_fd, account.pw_uid, account.pw_gid)
            os.close(fd)
            fd = next_fd
        return fd
    except Exception:
        os.close(fd)
        raise

def git(repo, token, *arguments):
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(STATE), 'LANG': 'C.UTF-8',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
           'GIT_TERMINAL_PROMPT': '0', 'GIT_ASKPASS': '/usr/local/lib/alfred/github-askpass.py',
           'ALFRED_GIT_TOKEN': token}
    process = subprocess.run(['git', '-c', 'core.hooksPath=/usr/local/lib/alfred/no-hooks',
                              '-c', 'credential.helper=', '-C', str(repo), *arguments],
                             env=env, capture_output=True, timeout=90)
    if process.returncode:
        raise RuntimeError('git_operation_failed_' + str(process.returncode))
    return process.stdout.decode('utf-8').strip()

def repository(config, scope):
    item = config['repositories'][scope]
    if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.git', item['url']):
        raise ValueError('invalid_fixed_repository_url')
    credential = Path(item['credential_file'])
    if credential.stat().st_uid != 0 or credential.stat().st_mode & 0o077:
        raise ValueError('credential_permissions')
    token = json.loads(credential.read_text())['token']
    repo = STATE / 'repositories' / scope
    if not repo.exists():
        repo.mkdir(mode=0o700, parents=True)
        git(repo, token, 'init', '-b', 'main')
        git(repo, token, 'remote', 'add', 'origin', item['url'])
        git(repo, token, 'fetch', '--quiet', 'origin', 'main')
        git(repo, token, 'reset', '--hard', 'origin/main')
    if git(repo, token, 'remote', 'get-url', 'origin') != item['url']:
        raise ValueError('repository_destination_changed')
    git(repo, token, 'config', 'user.name', 'Alfred Documentaliste')
    git(repo, token, 'config', 'user.email', 'documentaliste@users.noreply.github.com')
    return repo, token, Path(item['workspace'])

def main():
    if os.geteuid() != 0:
        raise PermissionError('use_configured_sudo_broker')
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['status', 'sync', 'publish', 'retry'])
    args = parser.parse_args()
    request = json.loads(sys.stdin.read(262145) or '{}')
    config = json.loads(CONFIG.read_text())
    scope = request.get('scope', 'instance')
    if scope not in config['repositories']:
        raise ValueError('unconfigured_scope')
    os.umask(0o077)
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (STATE / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        repo, token, workspace = repository(config, scope)
        git(repo, token, 'fetch', '--quiet', 'origin', 'main')
        head, remote = git(repo, token, 'rev-parse', 'HEAD'), git(repo, token, 'rev-parse', 'origin/main')
        if args.action == 'status':
            print(json.dumps({'scope': scope, 'head': head, 'remote_head': remote, 'pending_push': head != remote,
                              'workspace': str(workspace), 'repository': config['repositories'][scope]['url'],
                              'required_files': config['repositories'][scope].get('required_files', [])}))
            return
        if args.action == 'sync':
            if head != remote:
                git(repo, token, 'merge', '--ff-only', 'origin/main')
                if git(repo, token, 'rev-parse', 'HEAD') != remote:
                    raise ValueError('pending_push_requires_retry')
            account = __import__('pwd').getpwnam(config['service_account'])
            workspace_fd = directory_fd(workspace, create=True, account=account)
            os.fchown(workspace_fd, account.pw_uid, account.pw_gid)
            os.close(workspace_fd)
            for name in git(repo, token, 'ls-files').splitlines():
                relative = validate_relative(scope, name)
                content = (repo / relative).read_bytes()
                directory = directory_fd(workspace / relative.parent, create=True, account=account)
                try:
                    try:
                        current = source_bytes(workspace, relative)
                    except FileNotFoundError:
                        current = None
                    if current is not None and current != content and not request.get('overwrite', False):
                        raise ValueError('workspace_changes_require_publication_or_review')
                    fd = os.open(relative.name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600, dir_fd=directory)
                    with os.fdopen(fd, 'wb') as destination:
                        destination.write(content)
                        os.fchown(destination.fileno(), account.pw_uid, account.pw_gid)
                finally:
                    os.close(directory)
            print(json.dumps({'scope': scope, 'synced': True, 'head': git(repo, token, 'rev-parse', 'HEAD')}))
            return
        if args.action == 'retry':
            if request.get('base_revision') != head:
                raise ValueError('stale_base_revision')
            git(repo, token, 'merge-base', '--is-ancestor', remote, head)
            git(repo, token, 'push', '--quiet', 'origin', 'HEAD:main')
            confirmed = git(repo, token, 'ls-remote', 'origin', 'refs/heads/main').split()[0] == head
            print(json.dumps({'scope': scope, 'commit': head, 'remote_confirmed': confirmed, 'retried': True}))
            return
        if request.get('classification') != scope:
            raise ValueError('classification_requires_explicit_scope')
        if request.get('base_revision') != head:
            raise ValueError('stale_base_revision')
        if head != remote:
            raise ValueError('remote_changed_or_pending_push_requires_review')
        files = request.get('files', [])
        if not isinstance(files, list) or not 0 < len(files) <= 200 or len(set(files)) != len(files):
            raise ValueError('explicit_unique_file_list_required')
        if not set(config['repositories'][scope].get('required_files', [])).issubset(files):
            raise ValueError('required_bundle_files_missing')
        message = request.get('message', '')
        if not isinstance(message, str) or not 0 < len(message) <= 250 or '\n' in message:
            raise ValueError('invalid_commit_message')
        contents = {}
        for name in files:
            relative = validate_relative(scope, name)
            content = source_bytes(workspace, relative)
            text = content.decode('utf-8')
            if token in text or any(marker in text for marker in config.get('public_private_markers', []) if scope == 'platform'):
                raise ValueError('secret_or_private_instance_content')
            if relative.suffix == '.json':
                json.loads(text)
            if relative.suffix == '.py':
                compile(text, name, 'exec')
            contents[relative] = content
        try:
            for relative, content in contents.items():
                target = repo / relative
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                target.write_bytes(content)
            scan = subprocess.run(['/usr/local/bin/gitleaks', 'dir', str(repo), '--redact', '--no-banner'], capture_output=True, timeout=60)
            if scan.returncode:
                raise ValueError('secret_scan_failed')
            git(repo, token, 'add', '--', *files)
            git(repo, token, 'diff', '--cached', '--check')
            if not git(repo, token, 'diff', '--cached', '--name-only'):
                print(json.dumps({'scope': scope, 'no_change': True, 'remote_confirmed': True, 'commit': head}))
                return
            git(repo, token, 'commit', '--quiet', '-m', message)
            commit = git(repo, token, 'rev-parse', 'HEAD')
            git(repo, token, 'push', '--quiet', 'origin', 'HEAD:main')
            confirmed = git(repo, token, 'ls-remote', 'origin', 'refs/heads/main').split()[0] == commit
            if not confirmed:
                raise RuntimeError('remote_commit_not_confirmed')
            result = {'scope': scope, 'commit': commit, 'remote_confirmed': True, 'files': files,
                      'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
            with (STATE / 'publications.jsonl').open('a') as log:
                log.write(json.dumps(result) + '\n')
            if config['repositories'][scope].pop('required_files', None) is not None:
                CONFIG.write_text(json.dumps(config, indent=2) + '\n')
            print(json.dumps(result))
        except Exception:
            # Keep committed-but-unpushed changes for explicit conflict recovery.
            if git(repo, token, 'rev-parse', 'HEAD') == head:
                git(repo, token, 'reset', '--hard', head)
            raise

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'ok': False, 'error': str(error) if isinstance(error, (ValueError, RuntimeError, PermissionError)) else type(error).__name__}))
        raise SystemExit(1)
