#!/bin/bash
set -euo pipefail
[[ $# == 2 && $1 == restart ]] || { echo 'Usage: alfred-service-control restart UNIT' >&2; exit 2; }
exec /usr/bin/python3 -I /usr/local/lib/alfred/service-monitor.py --restart "$2"
