"""Tests for the test-me go-ahead detector."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from test_me_trigger import is_go_ahead  # noqa: E402

HOOK = HOOKS_DIR / "test_me_trigger.py"


@pytest.mark.parametrize(
    "prompt",
    [
        "ok let's do",
        "Ok let’s do it",
        "let's go",
        "go ahead",
        "go",
        "ok go!",
        "go for it",
        "vas-y",
        "ok on y va",
        "allez-y",
    ],
)
def test_go_ahead_triggers(prompt):
    assert is_go_ahead(prompt)


@pytest.mark.parametrize(
    "prompt",
    [
        "",
        "how does the go runtime schedule goroutines?",
        "ok",
        "let's go with option B but rename the table to users_v2 and add an index",
        "ok let's do, no test",
        "go ahead skip-test",
        "golang",
    ],
)
def test_other_prompts_pass(prompt):
    assert not is_go_ahead(prompt)


def test_hook_emits_context_on_go_ahead():
    out = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"prompt": "ok let's do"}),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "test-me" in json.loads(out)["hookSpecificOutput"]["additionalContext"]


def test_hook_silent_on_other_prompt():
    out = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"prompt": "explain the diff"}),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert out == ""
