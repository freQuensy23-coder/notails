# NoTail

A Claude Code plugin that blocks `... | tail` and `... | head` in Bash commands so Claude can't silently truncate errors before reading them.

## Why

Claude sometimes wraps long-running commands like `npm test`, `mvn install`, or `ninja` with `| tail -N` to "save context." If the failure lands above the truncation window, Claude reads the clean tail and reports success — even when the command actually crashed. This is well-documented as a recurring failure mode (see [anthropics/claude-code#39945](https://github.com/anthropics/claude-code/issues/39945)).

The Claude Code Bash tool already persists large outputs to a file, so up-front truncation isn't needed for context reasons. NoTail enforces that.

## What it blocks

Only the pipe form is blocked:

| Command | Blocked? |
| --- | --- |
| `npm test \| tail -20` | yes |
| `mvn install 2>&1 \| head -50` | yes |
| `tail -f /var/log/foo` | no — legitimate streaming |
| `head README.md` | no — legitimate file read |
| `tail /tmp/build.log` | no — reading a file is fine |

When blocked, the hook exits with code 2 and prints a stderr message suggesting the redirect-then-inspect pattern.

## Install (Claude Code marketplace)

```text
/plugin marketplace add freQuensy23-coder/notails
/plugin install notail
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

- `jq` on `PATH`. If it's missing, the hook fails open (allows the command) and prints a one-line warning so it never blocks Bash entirely.

## License

MIT
