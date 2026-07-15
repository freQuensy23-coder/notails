"""End-to-end tests for the hook CLI (scripts/detector.py).

These feed a real Claude Code PreToolUse JSON payload to the detector via
stdin, exactly as block-tail.sh invokes it, and assert on the exit code.
"""
import json
import os
import subprocess
import sys

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "detector.py")


def _run(command):
    payload = json.dumps({"tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, SCRIPT],
        input=payload,
        capture_output=True,
        text=True,
    )


def test_cli_blocks_script_piped_to_tail():
    proc = _run("python script.py | tail -1")
    assert proc.returncode == 2
    assert "NoTail" in proc.stderr


def test_cli_allows_plain_grep():
    proc = _run("grep foo file.log")
    assert proc.returncode == 0


def test_cli_allows_cat_piped_to_tail():
    proc = _run("cat config.json | tail -5")
    assert proc.returncode == 0


def test_cli_bad_json_fails_open():
    proc = subprocess.run(
        [sys.executable, SCRIPT],
        input="not json",
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0


def test_cli_missing_command_fails_open():
    proc = subprocess.run(
        [sys.executable, SCRIPT],
        input=json.dumps({}),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
