# NoTail

A Claude Code plugin that blocks piping a script/program/network call's output into `tail`, `head`, or `grep` so Claude can't silently truncate or filter errors before reading them. Plain file readers and text utilities (cat, grep, sed, sort, find, git, …) may still pipe into those.

## Why

Claude sometimes wraps long-running commands like `npm test`, `mvn install`, or `ninja` with `| tail -N` to "save context." If the failure lands above the truncation window, Claude reads the clean tail and reports success — even when the command actually crashed. This is well-documented as a recurring failure mode (see [anthropics/claude-code#39945](https://github.com/anthropics/claude-code/issues/39945)).

The Claude Code Bash tool already persists large outputs to a file, so up-front truncation isn't needed for context reasons. NoTail enforces that.

## What it blocks

A command is blocked only when a **dangerous producer** (a script, program, or network call whose output may contain errors or logs) is piped into `tail`, `head`, or `grep`. Piping a **safe reader** (cat, grep, sed, sort, find, git, tee, …) into those is allowed. Anything not on the safe list is treated as dangerous (fail-closed).

| Command | Blocked? | Why |
| --- | --- | --- |
| `npm test \| tail -20` | yes | program output truncated |
| `python script.py \| grep ERROR` | yes | program output filtered |
| `curl https://x.com \| tail` | yes | network output truncated |
| `./build.sh \| head` | yes | script output truncated |
| `cat config.json \| grep host` | no | file reader -> grep |
| `git log --oneline \| tail -20` | no | VCS read -> tail |
| `find . -name "*.py" \| head` | no | filesystem read -> head |
| `tail -f /var/log/foo` | no | not a pipe at all |
| `head README.md` | no | legitimate file read |

When blocked, the hook exits with code 2 and prints a stderr message suggesting the capture-then-inspect pattern.

## Install (Claude Code marketplace)

```text
/plugin marketplace add freQuensy23-coder/notails
/plugin install notail@notails
```

After install the hook activates automatically — no `settings.json` edits needed.

## Install (manual, single machine)

If you don't want a marketplace install, copy the hook directly into your user settings:

```jsonc
// ~/.claude/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "/absolute/path/to/notails/scripts/block-tail.sh" }
        ]
      }
    ]
  }
}
```

## Requirements

- `python3` on `PATH`. If it's missing, the hook fails open (allows the command) and prints a one-line warning so it never blocks Bash entirely.

## License

MIT
