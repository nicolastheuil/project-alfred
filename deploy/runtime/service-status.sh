#!/bin/bash
set -euo pipefail
exec /usr/bin/python3 -I /usr/local/lib/alfred/service-monitor.py --status
