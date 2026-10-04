"""Acceptance of installed RTK: Git output, error exits, byte-for-byte capture, no model."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

home = Path(os.environ['HERMES_HOME'])
state = home / 'state'
state.mkdir(parents=True, exist_ok=True)
reports = []
with tempfile.TemporaryDirectory(prefix='rtk-acceptance-', dir=state) as directory:
    root = Path(directory)
    repo = root / 'example'
    repo.mkdir()
    def git(*args):
        return subprocess.run(['/usr/bin/git', *args], cwd=repo, capture_output=True)
    assert git('init', '-q').returncode == 0
    git('config', 'user.name', 'module-acceptance')
    git('config', 'user.email', 'test@example.invalid')
    for number in range(30):
        (repo / f'example-{number:02}.txt').write_text(''.join(f'Initial line {i}\n' for i in range(100)))
    git('add', '.')
    git('commit', '-qm', 'Initial acceptance fixture')
    for number in range(3):
        (repo / f'example-{number:02}.txt').write_text(''.join(f'Changed line {i}\n' for i in range(300)))
    for number in range(3, 30):
        with (repo / f'example-{number:02}.txt').open('a') as stream:
            stream.write('A changed line\n')
    def compare(label, args, cwd):
        raw = subprocess.run(['/usr/bin/git', *args], cwd=cwd, capture_output=True)
        result = subprocess.run(['/usr/local/bin/alfred-rtk', 'git', *args], cwd=cwd, capture_output=True)
        assert raw.returncode == result.returncode, (label, raw.returncode, result.returncode)
        evidence = [line.split(': ', 1)[1] for line in result.stderr.decode(errors='replace').splitlines()
                    if line.startswith('RTK raw command evidence: ')]
        assert len(evidence) == 1
        folder = Path(evidence[0])
        captures = list(folder.glob('*.json'))
        assert captures, 'No raw command evidence captured'
        for item in captures:
            metadata = json.loads(item.read_text())
            replay = subprocess.run(['/usr/bin/git', *metadata['argv']], cwd=metadata['cwd'], capture_output=True)
            assert replay.stdout == item.with_suffix('.stdout').read_bytes()
            assert replay.stderr == item.with_suffix('.stderr').read_bytes()
            assert replay.returncode == metadata['exit_code']
        report = {'case': label, 'raw_bytes': len(raw.stdout) + len(raw.stderr),
                  'visible_bytes_including_evidence_path': len(result.stdout) + len(result.stderr),
                  'exit_code': result.returncode, 'raw_capture_verified': True,
                  'captured_invocations': len(captures)}
        reports.append(report)
    compare('status_30_changes', ['status'], repo)
    compare('diff_large_patch', ['diff'], repo)
    compare('outside_repository_error', ['status'], root)
    (repo / 'example-00.txt').write_text('Trailing whitespace  \n')
    compare('diff_check_failure', ['diff', '--check'], repo)
print(json.dumps({'version': '0.51.0', 'cases': reports, 'model_calls': 0, 'synthetic_fixture': True}))
