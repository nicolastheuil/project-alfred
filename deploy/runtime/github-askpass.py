#!/usr/bin/python3
"""Git-only askpass; root publisher supplies a token in its private environment."""
import os
import sys
if os.geteuid() != 0:
    raise SystemExit(1)
print('x-access-token' if 'username' in sys.argv[-1].lower() else os.environ['ALFRED_GIT_TOKEN'])
