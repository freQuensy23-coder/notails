#!/usr/bin/env python3
"""notails command-block detector + hook entry point.

Decides whether a Bash command should be blocked by the NoTail hook.

Rule:
  Block when a "dangerous producer" (a script/program/network call whose
  output may contain logs or errors) is piped into a truncation/filter
  target (`tail`, `head`, `grep`). Pure file readers and text utilities
  (cat, grep, sed, sort, find, git, ...) may pipe into those targets.

The detector parses the shell command properly: it tracks quotes, braces,
and backslash escapes so that a `|` inside `"print(1 | 2)"` is not treated
as a pipe.

CLI (hook entry point):
  Reads a Claude Code PreToolUse JSON payload from stdin, extracts
  `tool_input.command`, and exits 2 (block) or 0 (allow).
"""
import json
import re
import sys

# Targets whose job is to truncate or filter input. Piping *into* these
# is what hides errors/logs. Everything else (sort, tee, sed, ...) is a
# normal pipeline stage and is ignored by the detector.
TARGETS = {"tail", "head", "grep"}

# Producers considered safe to pipe into a target: they emit already-formed
# data (file contents, text, search results, VCS read output) rather than
# program logs. Anything NOT here is treated as dangerous (fail-closed).
ALLOWED_PRODUCERS = {
    # text / file readers & filters
    "cat", "tac", "nl", "rev", "less", "more", "pr", "fmt", "fold", "expand",
    "unexpand", "column", "cut", "tr", "paste", "join", "head", "tail",
    "grep", "egrep", "fgrep", "rg", "ag", "ack", "sed", "awk", "gawk", "sort",
    "uniq", "comm", "cmp", "diff", "sdiff", "wc", "strings", "xxd", "od",
    "hexdump", "shuf", "seq", "yes", "echo", "printf", "date", "cal", "tee",
    # filesystem inspection (read-only)
    "find", "locate", "ls", "dir", "vdir", "tree", "stat", "file", "du", "df",
    "readlink", "realpath", "basename", "dirname", "whereis", "which", "type",
    "command",
    # vcs read
    "git", "svn", "hg", "bzr",
    # env / system info (read-only)
    "env", "printenv", "uname", "hostname", "id", "who", "w", "whoami",
    "groups", "uptime", "test", "true", "false",
}

BLOCK_MESSAGE = """\
NoTail blocked this command.

A program/script/network call was piped into `tail`/`head`/`grep`, which
truncates or filters its output before you can inspect it. That hides
errors and logs — especially when stderr is merged with `2>&1`.

If you need specific values, first save the full output, then filter it:
  • Run the command unmodified — large outputs are saved automatically.
  • Capture then inspect:
      <cmd> > /tmp/run.log 2>&1; echo "exit: $?"; grep PATTERN /tmp/run.log
  • If grep finds nothing, you may have the format wrong; re-read the
    full log before concluding anything.

Piping a file reader (cat, grep, sed, sort, find, git, ...) into
`tail`/`head`/`grep` is fine and is not blocked.
"""

_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# A redirect token is made only of digits, <, >, & and contains at least
# one < or > (e.g. 2>&1, 2>, >>, <, &>). This must NOT match plain words.
_REDIRECT = re.compile(r"^[\d<>&]*[<>][\d<>&]*$")


def should_block(command):
    """Return True if the command should be blocked by NoTail."""
    if not command:
        return False
    for cmd in _split_commands(command):
        stages = _split_stages(cmd)
        # need at least producer -> target
        for i in range(len(stages) - 1):
            target = _command_word(stages[i + 1])
            if target not in TARGETS:
                continue
            producer = _command_word(stages[i])
            if not producer:
                continue
            if _basename(producer) not in ALLOWED_PRODUCERS:
                return True
    return False


def _basename(word):
    """Return the final path component, so ./x.sh and /usr/bin/x normalize."""
    return word.rsplit("/", 1)[-1]


def _command_word(stage):
    """First meaningful command token of a pipeline stage.

    Skips leading env assignments (FOO=bar) and redirects (2>&1, >f, <f).
    Strips surrounding quotes from the resulting word.
    """
    for tok in _tokenize(stage):
        if _ENV_ASSIGN.match(tok):
            continue
        if _REDIRECT.match(tok):
            continue
        return _strip_quotes(tok)
    return ""


def _strip_quotes(tok):
    if len(tok) >= 2 and tok[0] in "\"'" and tok[-1] == tok[0]:
        return tok[1:-1]
    return tok


def _tokenize(stage):
    """Split a stage into whitespace-separated tokens at top level.

    Quotes and escapes are preserved on the token (so FOO="a b" stays one
    token); only top-level whitespace splits.
    """
    tokens = []
    cur = []
    i, n = 0, len(stage)
    quote = None
    depth = 0
    while i < n:
        c = stage[i]
        if quote:
            cur.append(c)
            if c == quote:
                quote = None
            elif c == "\\" and quote == '"' and i + 1 < n:
                cur.append(stage[i + 1]); i += 2; continue
        else:
            if c in "\"'":
                quote = c; cur.append(c)
            elif c in "({[":
                depth += 1; cur.append(c)
            elif c in ")}]":
                depth = max(0, depth - 1); cur.append(c)
            elif c == "\\" and i + 1 < n:
                cur.append(stage[i + 1]); i += 2; continue
            elif depth == 0 and c in " \t\n":
                if cur:
                    tokens.append("".join(cur)); cur = []
            else:
                cur.append(c)
        i += 1
    if cur:
        tokens.append("".join(cur))
    return tokens


def _split_commands(s):
    """Split into top-level commands. Separators: ;, &&, ||, &, newline.

    A single `|` (pipe) stays inside a command — it separates pipeline
    stages, not commands. `||` is a command separator (logical OR).
    """
    commands = []
    cur = []
    i, n = 0, len(s)
    quote = None
    depth = 0
    while i < n:
        c = s[i]
        nxt = s[i + 1] if i + 1 < n else ""
        if quote:
            cur.append(c)
            if c == quote:
                quote = None
            elif c == "\\" and quote == '"' and i + 1 < n:
                cur.append(s[i + 1]); i += 2; continue
        else:
            if c in "\"'":
                quote = c; cur.append(c)
            elif c in "({[":
                depth += 1; cur.append(c)
            elif c in ")}]":
                depth = max(0, depth - 1); cur.append(c)
            elif c == "\\" and i + 1 < n:
                cur.append(s[i + 1]); i += 2; continue
            elif depth == 0 and c == "&" and nxt == "&":
                commands.append("".join(cur)); cur = []; i += 2; continue
            elif depth == 0 and c == "|" and nxt == "|":
                commands.append("".join(cur)); cur = []; i += 2; continue
            elif depth == 0 and c == "&" and nxt != "&":
                # '&' may be part of a redirect (>&, <&, &>) rather than the
                # background operator; only split when it is a real operator.
                prev = cur[-1] if cur else ""
                if prev in "<>" or nxt == ">":
                    cur.append(c); i += 1; continue
                commands.append("".join(cur)); cur = []; i += 1; continue
            elif depth == 0 and c in ";\n":
                commands.append("".join(cur)); cur = []; i += 1; continue
            else:
                cur.append(c)
        i += 1
    commands.append("".join(cur))
    return [c.strip() for c in commands if c.strip()]


def _split_stages(cmd):
    """Split a command into pipeline stages by a single top-level `|`."""
    stages = []
    cur = []
    i, n = 0, len(cmd)
    quote = None
    depth = 0
    while i < n:
        c = cmd[i]
        nxt = cmd[i + 1] if i + 1 < n else ""
        if quote:
            cur.append(c)
            if c == quote:
                quote = None
            elif c == "\\" and quote == '"' and i + 1 < n:
                cur.append(cmd[i + 1]); i += 2; continue
        else:
            if c in "\"'":
                quote = c; cur.append(c)
            elif c in "({[":
                depth += 1; cur.append(c)
            elif c in ")}]":
                depth = max(0, depth - 1); cur.append(c)
            elif c == "\\" and i + 1 < n:
                cur.append(cmd[i + 1]); i += 2; continue
            elif depth == 0 and c == "|" and nxt != "|":
                stages.append("".join(cur)); cur = []; i += 1; continue
            else:
                cur.append(c)
        i += 1
    stages.append("".join(cur))
    return [s.strip() for s in stages if s.strip()]


def _payload_command(payload):
    """Extract tool_input.command from a Claude Code hook payload."""
    if not isinstance(payload, dict):
        return ""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    return tool_input.get("command") or ""


def main(argv=None):
    """Hook entry point: read JSON payload from stdin, decide block/allow."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # Fail open on bad/missing JSON so Bash is never locked out.
        return 0
    if should_block(_payload_command(payload)):
        sys.stderr.write(BLOCK_MESSAGE)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
