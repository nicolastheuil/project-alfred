"""Run the pinned structural linter on every maintained instruction source."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--executable', default='lintlang')
args = parser.parse_args()
root = args.root.resolve()
files = [p for p in root.rglob('*.md') if p.name in {'AGENTS.md', 'SOUL.md', 'SKILL.md'}
         and '.git' not in p.parts and not p.is_symlink()]
if not files:
    raise SystemExit('No instruction sources found')
result = subprocess.run([args.executable, 'scan', *[str(p) for p in sorted(files)],
                         '--format', 'json', '--fail-on', 'fail'], capture_output=True, text=True)
if result.stdout:
    # Output comes from source files; never include runtime configurations or memories.
    print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
