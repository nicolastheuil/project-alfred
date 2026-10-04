#!/bin/bash
set -euo pipefail
[[ $# == 2 && $1 == restart ]] || { echo 'Usage: alfred-repair restart UNIT' >&2; exit 2; }
exec /usr/bin/sudo -n /usr/local/sbin/alfred-service-control restart "$2"
