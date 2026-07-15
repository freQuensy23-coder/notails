#!/usr/bin/env bash
# NoTail PreToolUse hook: blocks piping a program/script/network call's
# output into `tail`/`head`/`grep` so errors and logs can't be silently
# truncated or filtered before they are inspected.
#
# The detection logic lives in scripts/detector.py and is unit-tested.
# This script is a thin wrapper that forwards the Claude Code hook JSON
# payload (on stdin) to the Python detector.
#
# Requires python3 on PATH. If it's missing, the hook fails open (allows
# the command) and prints a one-line warning so Bash is never blocked.

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
    echo "NoTail: python3 not found in PATH; allowing command (install python3 to enable this hook)" >&2
    exit 0
fi

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$DIR/detector.py"
