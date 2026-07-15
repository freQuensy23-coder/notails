#!/usr/bin/env bash
# Verify the actual hook end-to-end: feed JSON payloads to block-tail.sh
# exactly like Claude Code does, and check exit codes (2 = block, 0 = allow).
set -u

HOOK="scripts/block-tail.sh"
pass=0; fail=0

check() {
    local desc="$1" cmd="$2" expect="$3"
    local payload
    payload=$(printf '{"tool_input":{"command":%s}}' "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$cmd")")
    sh "$HOOK" <<<"$payload" >/dev/null 2>&1
    local rc=$?
    if [ "$rc" = "$expect" ]; then
        pass=$((pass+1))
    else
        fail=$((fail+1))
        printf 'FAIL: %s | rc=%s expected=%s\n' "$desc" "$rc" "$expect"
    fi
}

check "py|tail  -> block"   "python script.py | tail -1" 2
check "curl|tail -> block"  "curl https://example.com | tail" 2
check "py|grep  -> block"   "python script.py | grep ERROR" 2
check "grep file -> allow"  "grep foo file.log" 0
check "cat|grep  -> allow"  "cat config.json | grep host" 0
check "git log|tail -> allow" "git log --oneline | tail -20" 0
check "tail -f file -> allow" "tail -f /var/log/system.log" 0

printf 'hook end-to-end: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = 0 ]
