"""Tests for the notails command-block detector (TDD red phase).

The detector is not implemented yet, so every case fails with
"detector not implemented yet". Once `detector.py` exists with
`should_block(command: str) -> bool`, the suite turns green.

Spec encoded here:
  Block (True)  = a script/program/network output is piped into
                  `tail`/`head`/`grep` (truncation or filtering
                  that can hide errors/logs).
  Allow (False) = plain file reading, or output captured to a file
                  first, or no truncation target at all.
"""
import pytest

try:
    from detector import should_block
except ImportError:  # red phase: module not implemented yet
    should_block = None


# (id, command, expected_blocked)
# expected True  -> command is BANNED
# expected False -> command is ALLOWED
CASES = [
    # ---------------- user cases ----------------
    # BLOCKED: run a script/program/network and truncate or filter its output.
    ("u_py_tail",
     "python script.py | tail -1",                                True),
    ("u_curl_tail",
     "curl https://example.com | tail",                           True),
    ("u_wget_tail",
     "wget https://example.com/file | tail",                      True),
    ("u_py_grep",
     "python script.py | grep ERROR",                             True),
    # ALLOWED
    ("u_py_then_grep_file",
     "python script.py\ngrep foo file.log",                       False),
    ("u_grep_file",
     'grep "pattern" file.log',                                   False),
    ("u_grep_logs",
     'grep "pattern" logs/*.log',                                 False),
    ("u_curl_file_then_grep",
     "curl https://example.com > out.txt\ngrep foo out.txt",      False),

    # ---------------- my cases (diverse, same count) ----------------
    # BLOCKED
    ("m_node_head",
     "node server.js | head -20",                                 True),
    ("m_npm_tail",
     "npm test 2>&1 | tail -30",                                  True),
    ("m_script_grep",
     "./build.sh | grep -i error",                                True),
    ("m_docker_head",
     "docker build . 2>&1 | head",                                True),
    # ALLOWED
    ("m_tail_f",
     "tail -f /var/log/system.log",                               False),
    ("m_cat_grep",
     "cat config.json | grep host",                               False),
    ("m_grep_sort_tail",
     'grep -r "TODO" src/ | sort | tail -20',                     False),
    ("m_find_head",
     'find . -name "*.py" | head',                                False),
]

# Flagged edge cases: recommendation shown, pending your decision.
# Marked xfail so they don't break the suite; revisit once we agree.
EDGE = [
    ("e_tee_capture",
     "python script.py | tee full.log | tail",                    False),  # Q1: tee saves full output -> allow
    ("e_git_log_tail",
     "git log --oneline | tail -20",                              False),  # Q2: git read subcommand -> allow
    ("e_py_c_pipe",
     'python -c "print(1 | 2)" | tail',                           True),   # quote-aware: inner | is literal; real pipe is python->tail -> BAN
    ("e_echo_pipe",
     'echo "a | b" | tail',                                       False),  # Q3: echo in allowlist -> allow
    ("e_py_sed_trunc",
     "python script.py | sed -n '1,20p'",                         False),  # Q4: v1 scope, sed/awk not blocked -> allow
]


@pytest.mark.parametrize("name,command,expected", CASES, ids=[c[0] for c in CASES])
def test_should_block(name, command, expected):
    if should_block is None:
        pytest.fail("detector not implemented yet")
    assert should_block(command) is expected


@pytest.mark.parametrize("name,command,expected", EDGE, ids=[c[0] for c in EDGE])
def test_edge(name, command, expected):
    if should_block is None:
        pytest.fail("detector not implemented yet")
    assert should_block(command) is expected
