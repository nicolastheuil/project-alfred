#!/usr/bin/env bash
# Install a locked Hermes engine. No model request or messaging service is started.
set -euo pipefail
if [[ $(id -u) -ne 0 ]]; then
  echo 'Run with sudo bash bootstrap/install-hermes.sh' >&2
  exit 1
fi
platform_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
lock="$platform_root/config/runtime.lock.json"
source /etc/os-release
if [[ ${ID:-} != debian || ${VERSION_ID:-} != 12 || $(dpkg --print-architecture) != arm64 ]]; then
  echo 'This initial runtime installer requires Debian 12 ARM64.' >&2
  exit 1
fi
revision=$(jq -er '.hermes.revision' "$lock")
tag=$(jq -er '.hermes.tag' "$lock")
repository=$(jq -er '.hermes.repository' "$lock")
uv_url=$(jq -er '.uv.url' "$lock")
uv_sha=$(jq -er '.uv.sha256' "$lock")
uv_lock_sha=$(jq -er '.hermes.uv_lock_sha256' "$lock")
python_url=$(jq -er '.python.url' "$lock")
python_sha=$(jq -er '.python.sha256' "$lock")
python_executable=$(jq -er '.python.executable' "$lock")
python_root=$(dirname -- "$(dirname -- "$python_executable")")
release="/opt/alfred/releases/hermes-$revision"
service_home=/var/lib/alfred-agent
data_home="$service_home/.hermes"
if ! getent passwd alfred >/dev/null; then
  useradd --system --user-group --home-dir "$service_home" --create-home --shell /usr/sbin/nologin alfred
fi
if [[ $(getent passwd alfred | cut -d: -f6) != "$service_home" || $(id -u alfred) == 0 ]]; then
  echo 'Existing alfred account has an unexpected home or UID.' >&2
  exit 1
fi
if pgrep -u alfred >/dev/null; then
  echo 'Stop the running Alfred services and workers before applying runtime maintenance.' >&2
  exit 1
fi
install -d -m 0700 -o alfred -g alfred "$service_home" "$data_home"
install -d -m 0755 /opt/alfred/releases /opt/alfred/tools
install -d -m 0700 /var/lib/alfred /var/cache/alfred
scratch=$(mktemp -d /var/cache/alfred/runtime-install.XXXXXX)
trap 'rm -f "$scratch/uv.tar.gz" "$scratch/python.tar.gz"' EXIT
curl --fail --location --retry 3 --output "$scratch/uv.tar.gz" "$uv_url"
printf '%s  %s\n' "$uv_sha" "$scratch/uv.tar.gz" | sha256sum --check
tar -xzf "$scratch/uv.tar.gz" -C "$scratch"
install -m 0755 "$scratch/uv-aarch64-unknown-linux-gnu/uv" /opt/alfred/tools/uv
if [[ ! -x "$python_executable" ]]; then
  curl --fail --location --retry 3 --output "$scratch/python.tar.gz" "$python_url"
  printf '%s  %s\n' "$python_sha" "$scratch/python.tar.gz" | sha256sum --check
  tar --no-same-owner -xzf "$scratch/python.tar.gz" -C "$scratch"
  if [[ -e "$python_root" ]]; then
    echo 'Python destination exists without an executable; inspect before retrying.' >&2
    exit 1
  fi
  mv "$scratch/python" "$python_root"
fi
"$python_executable" - "$lock" <<'PY'
import json, platform, sqlite3, sys
from pathlib import Path
expected = json.loads(Path(sys.argv[1]).read_text())['python']
assert platform.python_version() == expected['version'], 'Python version differs from runtime lock'
minimum = tuple(map(int, expected['minimum_sqlite_version'].split('.')))
assert sqlite3.sqlite_version_info >= minimum, 'SQLite must include the WAL-reset correction'
print('[alfred] Python', platform.python_version(), '; SQLite', sqlite3.sqlite_version)
PY

if [[ ! -d "$release/.git" ]]; then
  if [[ -e "$release" ]]; then
    echo 'Runtime destination exists without a valid checkout; inspect before retrying.' >&2
    exit 1
  fi
  git clone --depth 1 --branch "$tag" "$repository" "$release"
fi
if [[ $(git -C "$release" rev-parse HEAD) != "$revision" ]]; then
  echo 'Runtime commit differs from the locked revision.' >&2
  exit 1
fi
if [[ -n $(git -C "$release" status --porcelain --untracked-files=no) ]]; then
  echo 'Runtime sources have local modifications; refusing to deploy.' >&2
  exit 1
fi
printf '%s  %s\n' "$uv_lock_sha" "$release/uv.lock" | sha256sum --check
export UV_CACHE_DIR=/var/cache/alfred/uv
export UV_PROJECT_ENVIRONMENT="$release/venv"
export UV_PYTHON_DOWNLOADS=never
export UV_CONCURRENT_DOWNLOADS=4 UV_CONCURRENT_BUILDS=1 UV_CONCURRENT_INSTALLS=2
echo '[alfred] Installing locked core dependencies, ACP and MCP'
cd "$release"
# Only verified wheels for third-party runtime dependencies. Prepare the local
# package build separately so its build tools also have pinned versions/hashes.
if ! "$release/venv/bin/python" - "$lock" >/dev/null 2>&1 <<'PY'
import importlib.metadata as metadata
import json, platform, sys
from pathlib import Path
assert platform.python_version() == json.loads(Path(sys.argv[1]).read_text())['python']['version']
assert metadata.version('setuptools') == '83.0.0'
assert metadata.version('wheel') == '0.48.0'
PY
then
  /opt/alfred/tools/uv sync --locked --no-dev --extra acp --extra mcp --python "$python_executable" \
    --no-install-project --no-build
  /opt/alfred/tools/uv pip install --python "$release/venv/bin/python" --require-hashes --no-deps \
    -r "$platform_root/deploy/runtime/build-requirements.lock"
fi
/opt/alfred/tools/uv sync --locked --no-dev --extra acp --extra mcp --python "$python_executable" \
  --no-build-isolation --inexact
# Engine and dependency installation belong to the system, not to model tool calls.
chmod -R go-w "$release"
ln -sfn "$release" /opt/alfred/current
install -m 0755 "$platform_root/deploy/runtime/hermes-launcher.sh" /usr/local/bin/hermes
install -d -m 0755 -o alfred -g alfred "$service_home/.local" "$service_home/.local/bin"
ln -sfn "$release/venv/bin/hermes" "$service_home/.local/bin/hermes"
sudo -n -u alfred env HERMES_HOME="$data_home" /usr/local/bin/hermes --version

"$release/venv/bin/python" - "$lock" "$release" <<'PY'
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sqlite3
import sys

lock_path, release = map(Path, sys.argv[1:])
manifest = {
    'phase': 'engine_installed',
    'installed_at_utc': datetime.now(timezone.utc).isoformat(),
    'lock': json.loads(lock_path.read_text()),
    'source_sha256': {str(path.relative_to(lock_path.parent.parent)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in [lock_path, lock_path.parent.parent/'bootstrap/install-hermes.sh',
                                   lock_path.parent.parent/'deploy/runtime/hermes-launcher.sh',
                                   lock_path.parent.parent/'deploy/runtime/build-requirements.lock']},
    'release_directory': str(release),
    'python_version': platform.python_version(),
    'sqlite_version': sqlite3.sqlite_version,
    'packages': sorted([{
        'name': d.metadata['Name'], 'version': d.version,
        'license_expression': d.metadata.get('License-Expression'),
        'legacy_license': d.metadata.get('License'),
        'license_classifiers': [c for c in (d.metadata.get_all('Classifier') or []) if c.startswith('License ::')],
        'project_urls': d.metadata.get_all('Project-URL') or [],
    } for d in importlib.metadata.distributions()], key=lambda d: d['name'].lower()),
    'profiles_composed': False,
    'model_request_tested': False,
    'channels_configured': False,
}
Path('/var/lib/alfred/runtime-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print('[alfred] Engine installed; manifest: /var/lib/alfred/runtime-manifest.json')
PY
