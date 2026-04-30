#!/usr/bin/env bash
# NoTail PreToolUse hook: blocks `... | tail` and `... | head` in Bash commands.
#
# Why: piping through tail/head before the output is read silently discards
# errors (especially when combined with `2>&1`). The Bash tool already
# persists large outputs to a file, so truncation up front is never needed.

set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
    # Fail open: a missing jq shouldn't break every Bash call.
    echo "NoTail: jq not found in PATH; allowing command (install jq to enable this hook)" >&2
    exit 0
fi

cmd=$(jq -r '.tool_input.command // empty' 2>/dev/null || true)
[ -z "${cmd:-}" ] && exit 0

# Match `| tail` or `| head` followed by a word boundary (space, end-of-line,
# `;`, `&`, or another pipe). Bare `tail file.log` and `tail -f log` are
# allowed — only the pipe-truncation antipattern is blocked.
if printf '%s\n' "$cmd" | grep -qE '\|[[:space:]]*(tail|head)([[:space:]]|$|;|&|\|)'; then
    cat >&2 <<'MSG'
NoTail blocked this command.

Piping into `tail`/`head` discards output before it can be inspected, which
hides errors — especially when stderr is merged in with `2>&1`. The Bash tool
already persists large outputs to a file, so up-front truncation is unnecessary.

Try instead:
  • Run the command unmodified — large outputs are saved automatically.
  • Redirect, then inspect:
      <cmd> > /tmp/run.log 2>&1; echo "exit: $?"; tail /tmp/run.log
  • Use `grep` for specific patterns rather than blind truncation.
MSG
    exit 2
fi

exit 0
