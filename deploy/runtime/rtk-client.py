"""Explicit RTK invocation, private per-profile state, no init/hooks or telemetry."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

base = Path('/var/lib/alfred-agent/.hermes')
candidate = Path(os.environ.get('HERMES_HOME', str(base)))
home = candidate.resolve()
if candidate.is_symlink() or not home.is_relative_to(base.resolve()):
    raise SystemExit('RTK state must belong to an Alfred profile')
os.umask(0o077)
state = home / 'state' / 'rtk'
if state.is_symlink() or not state.resolve().is_relative_to(home):
    raise SystemExit('Unsafe RTK state directory')
config_dir = state / 'config' / 'rtk'
config_dir.mkdir(parents=True, exist_ok=True)
data = state / 'data'
data.mkdir(parents=True, exist_ok=True)
config = config_dir / 'config.toml'
if config.is_symlink():
    raise SystemExit('Symlink RTK config refused')
config.write_text('[telemetry]\nenabled = false\n[tracking]\nenabled = false\n'
                  '[retriever]\nmode = "disabled"\n')
arguments = sys.argv[1:]
if arguments == ['--version']:
    os.execv('/opt/alfred/tools/rtk-0.51.0/rtk', ['rtk', '--version'])
if len(arguments) < 2 or arguments[0] != 'git' or arguments[1] not in ('status', 'log', 'diff', 'show'):
    raise SystemExit('Supported explicit commands: git status, log, diff, show; use the normal terminal for other commands')
archive = state / 'raw'
if archive.is_symlink() or not archive.resolve().is_relative_to(home):
    raise SystemExit('Unsafe RTK archive directory')
archive.mkdir(parents=True, exist_ok=True)
entries = sorted((p for p in archive.iterdir() if p.is_dir() and not p.is_symlink()), key=lambda p: p.stat().st_mtime, reverse=True)
for index, entry in enumerate(entries):
    if index >= 49 or time.time() - entry.stat().st_mtime > 7 * 86400:
        shutil.rmtree(entry)
run = archive / uuid.uuid4().hex
run.mkdir(mode=0o700)
os.environ['XDG_CONFIG_HOME'] = str(state / 'config')
os.environ['XDG_DATA_HOME'] = str(data)
os.environ['ALFRED_RTK_CAPTURE_DIR'] = str(run)
os.environ['PATH'] = '/opt/alfred/tools/rtk-0.51.0/capture-bin:' + os.environ.get('PATH', '/usr/bin:/bin')
os.environ['GIT_PAGER'] = 'cat'
result = subprocess.run(['/opt/alfred/tools/rtk-0.51.0/rtk', *arguments])
print('RTK raw command evidence: ' + str(run), file=sys.stderr)
raise SystemExit(result.returncode)
