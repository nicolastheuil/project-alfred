"""Transparent local capture of each git invocation made by the explicit RTK launcher."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

os.umask(0o077)
folder = Path(os.environ['ALFRED_RTK_CAPTURE_DIR'])
if folder.is_symlink() or not folder.resolve().is_relative_to(Path('/var/lib/alfred-agent/.hermes')):
    raise SystemExit('Unsafe evidence directory')
name = uuid.uuid4().hex
out, err = folder / (name + '.stdout'), folder / (name + '.stderr')
with out.open('xb') as stdout, err.open('xb') as stderr:
    process = subprocess.Popen(['/usr/bin/git', *sys.argv[1:]], stdout=stdout, stderr=stderr)
    try:
        code = process.wait(timeout=120)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        code = 124
        stderr.write(b'Git command exceeded the 120 second limit\n')
(folder / (name + '.json')).write_text(json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd(), 'exit_code': code}))
with out.open('rb') as stream:
    shutil.copyfileobj(stream, sys.stdout.buffer)
with err.open('rb') as stream:
    shutil.copyfileobj(stream, sys.stderr.buffer)
raise SystemExit(code if code >= 0 else 128 - code)
