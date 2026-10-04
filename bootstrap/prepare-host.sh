#!/usr/bin/env bash
# Prepare the Debian host. This phase does not yet deploy the agent runtime.
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo 'Run with sudo bash bootstrap/prepare-host.sh' >&2
  exit 1
fi
source /etc/os-release
if [[ ${ID:-} != debian || ${VERSION_ID:-} != 12 ]]; then
  echo 'This initial host bootstrap requires Debian 12.' >&2
  exit 1
fi
platform_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
manifest_root=/var/lib/alfred
install -d -m 0700 "$manifest_root" "$manifest_root/host-originals"
export DEBIAN_FRONTEND=noninteractive
echo '[alfred] Installing Debian host prerequisites'
apt-get -q update
apt-get -q -y --no-install-recommends -o DPkg::Lock::Timeout=30 install ca-certificates curl git python3 python3-venv jq zram-tools

zram_changed=false
if ! cmp -s "$platform_root/deploy/system/zramswap.default" /etc/default/zramswap; then
  zram_changed=true
  if awk 'NR > 1 && $1 ~ /zram/ && $4 > 0 {used=1} END {exit used ? 0 : 1}' /proc/swaps; then
    echo 'Active zram contains swapped pages; schedule a maintenance phase before changing its layout.' >&2
    exit 1
  fi
  if [[ ! -e "$manifest_root/host-originals/zramswap.default" ]]; then
    cp -p /etc/default/zramswap "$manifest_root/host-originals/zramswap.default"
  fi
  install -m 0644 "$platform_root/deploy/system/zramswap.default" /etc/default/zramswap
fi
install -m 0644 "$platform_root/deploy/system/99-alfred-memory.conf" /etc/sysctl.d/99-alfred-memory.conf
sysctl -q -w vm.swappiness=100
systemctl enable zramswap.service
if [[ $zram_changed == true ]]; then
  systemctl restart zramswap.service
elif ! systemctl is-active --quiet zramswap.service; then
  systemctl start zramswap.service
fi
systemctl is-active --quiet zramswap.service

python3 - "$platform_root" "$manifest_root" <<'PY'
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root, destination = map(Path, sys.argv[1:])
packages = ['ca-certificates', 'curl', 'git', 'python3', 'python3-venv', 'jq', 'zram-tools']
versions = subprocess.check_output(['dpkg-query', '-W', '-f=${Package}\t${Version}\t${Architecture}\n', *packages], text=True).splitlines()
report = {
    'phase': 'host_prerequisites_ready',
    'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
    'packages': versions,
    'architecture': subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip(),
    'zram_unit_enabled': subprocess.check_output(['systemctl', 'is-enabled', 'zramswap.service'], text=True).strip(),
    'zram_unit_active': subprocess.check_output(['systemctl', 'is-active', 'zramswap.service'], text=True).strip(),
    'swap': Path('/proc/swaps').read_text(),
    'swappiness': Path('/proc/sys/vm/swappiness').read_text().strip(),
    'source_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'bootstrap/prepare-host.sh', root/'deploy/system/zramswap.default', root/'deploy/system/99-alfred-memory.conf']},
    'agent_runtime_deployed': False,
    'reboot_tested': False,
}
(destination/'host-manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print('[alfred] Host prerequisites ready; manifest: /var/lib/alfred/host-manifest.json')
PY
