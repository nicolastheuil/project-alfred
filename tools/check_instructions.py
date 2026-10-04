"""Run the pinned structural linter on every maintained instruction source."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import yaml

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument('--executable', default='lintlang')
args = parser.parse_args()
root = args.root.resolve()
files = [p for p in root.rglob('*.md') if p.name in {'AGENTS.md', 'SOUL.md', 'SKILL.md'}
         and '.git' not in p.parts and not p.is_symlink()]
if not files:
    raise SystemExit('No instruction sources found')
for path in files:
    if path.name != 'SKILL.md':
        continue
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        raise SystemExit(f'Skill frontmatter missing: {path}')
    try:
        metadata = yaml.safe_load(text.split('---', 2)[1])
    except yaml.YAMLError:
        raise SystemExit(f'Invalid skill YAML frontmatter: {path}')
    if not isinstance(metadata, dict) or metadata.get('name') != path.parent.name or not metadata.get('description'):
        raise SystemExit(f'Skill name and trigger description required: {path}')
result = subprocess.run([args.executable, 'scan', *[str(p) for p in sorted(files)],
                         '--format', 'json', '--fail-on', 'fail'], capture_output=True, text=True)
if result.stdout:
    # Output comes from source files; never include runtime configurations or memories.
    print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
