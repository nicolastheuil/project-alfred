#!/usr/bin/env bash
set -euo pipefail
if [[ $(id -un) != alfred ]]; then
  echo 'Run this installation as the alfred service account: sudo -u alfred hermes ...' >&2
  exit 1
fi
export HERMES_HOME="${HERMES_HOME:-/var/lib/alfred-agent/.hermes}"
export HERMES_INSTALL_DIR=/opt/alfred/current
export PYTHONDONTWRITEBYTECODE=1
exec /opt/alfred/current/venv/bin/hermes "$@"
