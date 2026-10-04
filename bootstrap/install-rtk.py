"""Build pinned RTK for Debian 12 ARM64 and install its explicit profile-aware launcher."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--use-completed-build', action='store_true')
args = parser.parse_args()
if os.geteuid() != 0:
    raise SystemExit('Root required')
if os.uname().machine != 'aarch64':
    raise SystemExit('This lock targets Debian ARM64')
source = args.source.resolve()
lock = json.loads((source / 'config/modules.lock.json').read_text())['rtk']
base = Path('/opt/alfred/build/rtk')
base.mkdir(parents=True, exist_ok=True)
code = base / ('rtk-' + lock['revision'])
rust = Path('/opt/alfred/build/rust-1.91.0')
if not args.use_completed_build:
    subprocess.run(['apt-get', 'install', '-y', '--no-install-recommends', 'build-essential', 'pkg-config'], check=True)
    for name, url, digest in [('rust.tar.xz', lock['rust_url'], lock['rust_sha256']),
                              ('source.tar.gz', lock['url'], lock['sha256'])]:
        path = base / name
        if not path.exists():
            urllib.request.urlretrieve(url, path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise SystemExit('Artifact checksum mismatch')
        with tarfile.open(path) as archive:
            archive.extractall(base, filter='data')
    subprocess.run(['bash', str(base / 'rust-1.91.0-aarch64-unknown-linux-gnu/install.sh'),
                    '--prefix=' + str(rust), '--components=rustc,cargo,rust-std-aarch64-unknown-linux-gnu',
                    '--disable-ldconfig'], check=True)
    subprocess.run(['useradd', '--system', '--create-home', '--home-dir', '/var/lib/alfred-build',
                    '--shell', '/usr/sbin/nologin', 'alfred-build'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['chown', '-R', 'alfred-build:alfred-build', str(code)], check=True)
    subprocess.run(['systemd-run', '--wait', '--pipe', '--collect', '--unit=alfred-rtk-build',
        '--property=User=alfred-build', '--property=WorkingDirectory=' + str(code),
        '--property=MemoryMax=1000M', '--property=MemorySwapMax=700M', '--property=CPUQuota=100%',
        '--property=Nice=15', '--property=TimeoutStartSec=2400',
        '--setenv=HOME=/var/lib/alfred-build', '--setenv=PATH=' + str(rust / 'bin') + ':/usr/bin:/bin',
        '--setenv=CARGO_PROFILE_RELEASE_LTO=false', '--setenv=CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16',
        '--setenv=CARGO_PROFILE_RELEASE_OPT_LEVEL=2', str(rust / 'bin/cargo'),
        'build', '--locked', '--release', '-j', '1'], check=True)
if args.use_completed_build:
    status = subprocess.run(['systemctl', 'show', 'alfred-rtk-build.service', '-p', 'ActiveState', '--value'], capture_output=True, text=True).stdout.strip()
    if status in ('active', 'activating'):
        raise SystemExit('Build still running; do not promote an unfinished artifact')
binary = code / 'target/release/rtk'
if binary.is_symlink() or not binary.is_file():
    raise SystemExit('Verified completed build required')
# Promote through a root-owned temporary file; build account cannot change the installed artifact.
target = Path('/opt/alfred/tools/rtk-' + lock['version'])
target.mkdir(parents=True, exist_ok=True)
shutil.copyfile(binary, target / 'rtk.pending')
(target / 'rtk.pending').chmod(0o755)
version = subprocess.run([str(target / 'rtk.pending'), '--version'], check=True, capture_output=True, text=True).stdout.strip()
if lock['version'] not in version:
    raise SystemExit('Unexpected RTK version')
os.replace(target / 'rtk.pending', target / 'rtk')
shutil.copyfile(code / 'LICENSE', target / 'LICENSE')
shutil.copyfile(source / 'deploy/runtime/rtk-client.py', '/usr/local/lib/alfred/rtk-client.py')
shutil.copyfile(source / 'deploy/runtime/rtk-git-capture.py', '/usr/local/lib/alfred/rtk-git-capture.py')
(target / 'capture-bin').mkdir(exist_ok=True)
(target / 'capture-bin/git').write_text('#!/bin/sh\nexec /opt/alfred/current/venv/bin/python -I /usr/local/lib/alfred/rtk-git-capture.py "$@"\n')
(target / 'capture-bin/git').chmod(0o755)
Path('/usr/local/bin/alfred-rtk').write_text('#!/bin/sh\nexec /opt/alfred/current/venv/bin/python -I /usr/local/lib/alfred/rtk-client.py "$@"\n')
Path('/usr/local/bin/alfred-rtk').chmod(0o755)
import pwd
account = pwd.getpwnam('alfred')
for name in ['dev', 'devops', 'qa', 'documentaliste', 'platform-engineer']:
    folder = Path('/var/lib/alfred-agent/.hermes/profiles') / name / 'skills/rtk-git'
    if not folder.parents[1].exists():
        continue
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / 'skills/rtk-git/SKILL.md', folder / 'SKILL.md')
    os.chown(folder.parent, account.pw_uid, account.pw_gid)
    os.chown(folder, account.pw_uid, account.pw_gid)
    os.chown(folder / 'SKILL.md', account.pw_uid, account.pw_gid)
    folder.chmod(0o700)
    (folder / 'SKILL.md').chmod(0o600)
report = {'version': version, 'revision': lock['revision'],
          'binary_sha256': hashlib.sha256((target / 'rtk').read_bytes()).hexdigest(),
          'compiler': 'Rust 1.91.0', 'source_sha256': lock['sha256'],
          'automatic_command_rewrite': False, 'telemetry': False}
Path('/var/lib/alfred/rtk-manifest.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
