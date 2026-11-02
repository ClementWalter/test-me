"""Tests for the test-me go-ahead detector."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from test_me_trigger import (
    classify,
    is_candidate,
    is_fallback_go_ahead,
    is_go_ahead,
    is_skipped,
    last_assistant_message,
)

HOOK = HOOKS_DIR / "test_me_trigger.py"
PLAN = "Plan: rename foo to bar in 3 files, then run tests. Shall I proceed?"


def human(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def assistant_text(text):
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def assistant_thinking(text):
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "thinking", "thinking": text}],
        },
    }


def tool_result():
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}],
        },
    }


@pytest.fixture
def write_transcript(tmp_path):
    def write(entries):
        path = tmp_path / "session.jsonl"
        path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
        return str(path)

    return write


@pytest.fixture
def plan_transcript(write_transcript):
    return write_transcript([human("rename foo"), assistant_text(PLAN)])


@pytest.fixture
def stub_claude(tmp_path, monkeypatch):
    """Point the hook at a fake `claude` that prints `stdout` and exits with `code`."""

    def install(stdout, code=0):
        args_file = tmp_path / "args.json"
        stub = tmp_path / "claude"
        stub.write_text(
            f"#!{sys.executable}\n"
            "import json, pathlib, sys\n"
            f"pathlib.Path({str(args_file)!r}).write_text(json.dumps(sys.argv[1:]))\n"
            f"sys.stdout.write({stdout!r})\n"
            f"sys.exit({code})\n"
        )
        stub.chmod(0o755)
        monkeypatch.setenv("TEST_ME_CLAUDE_BIN", str(stub))
        return args_file

    return install


# --- cheap gate -------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "ok let's do",
        "Ok let’s do it",
        "go",
        "vas-y",
        "ok go ahead but rename it fetch_all first",
        "don't do it",
        "sounds good",
        "👍",
        "oui, lance",
    ],
)
def test_short_approval_ish_prompt_is_candidate(prompt):
    assert is_candidate(prompt)


@pytest.mark.parametrize(
    "prompt",
    [
        "",
        "explain the diff",
        "golang",
        "x" * 150 + " ok let's do " + "y" * 50,
    ],
)
def test_other_prompt_is_not_candidate(prompt):
    assert not is_candidate(prompt)


@pytest.mark.parametrize("prompt", ["ok let's do, no test", "go ahead skip-test"])
def test_opt_out_is_skipped(prompt):
    assert is_skipped(prompt)


# --- strict fallback --------------------------------------------------------


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
        "yes do it now",
    ],
)
def test_fallback_accepts_bare_approval(prompt):
    assert is_fallback_go_ahead(prompt)


@pytest.mark.parametrize(
    "prompt",
    [
        "",
        "don't do it",
        "let's go back to the other file",
        "how does the go runtime schedule goroutines?",
        "ok",
        "golang",
    ],
)
def test_fallback_rejects_everything_else(prompt):
    assert not is_fallback_go_ahead(prompt)


# --- transcript reading -----------------------------------------------------


def test_last_message_before_unwritten_prompt(plan_transcript):
    assert last_assistant_message(plan_transcript) == PLAN


def test_last_message_when_prompt_already_written(write_transcript):
    path = write_transcript(
        [human("rename foo"), assistant_text(PLAN), human("ok go ahead")]
    )
    assert last_assistant_message(path) == PLAN


def test_last_message_joins_text_across_tool_calls(write_transcript):
    path = write_transcript(
        [
            human("rename foo"),
            assistant_text("Looking."),
            tool_result(),
            assistant_text(PLAN),
        ]
    )
    assert last_assistant_message(path) == f"Looking.\n{PLAN}"


def test_last_message_ignores_thinking(write_transcript):
    path = write_transcript([human("rename foo"), assistant_thinking("secret")])
    assert last_assistant_message(path) == ""


def test_last_message_skips_older_turns(write_transcript):
    path = write_transcript(
        [human("a"), assistant_text("old answer"), human("b"), assistant_text(PLAN)]
    )
    assert last_assistant_message(path) == PLAN


def test_last_message_tolerates_bad_lines(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text("not json\n" + json.dumps(assistant_text(PLAN)) + "\n")
    assert last_assistant_message(str(path)) == PLAN


def test_last_message_missing_file(tmp_path):
    assert last_assistant_message(str(tmp_path / "nope.jsonl")) == ""


def test_last_message_no_path():
    assert last_assistant_message(None) == ""


# --- classifier -------------------------------------------------------------


def test_classify_approve(stub_claude):
    stub_claude("APPROVE\n")
    assert classify("go", PLAN) is True


def test_classify_other(stub_claude):
    stub_claude("OTHER\n")
    assert classify("don't do it", PLAN) is False


def test_classify_unexpected_answer(stub_claude):
    stub_claude("Maybe?\n")
    assert classify("go", PLAN) is None


def test_classify_cli_error(stub_claude):
    stub_claude("", code=1)
    assert classify("go", PLAN) is None


def test_classify_missing_cli(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_ME_CLAUDE_BIN", str(tmp_path / "missing"))
    assert classify("go", PLAN) is None


def test_classify_disables_hooks_in_nested_session(stub_claude):
    args_file = stub_claude("OTHER\n")
    classify("go", PLAN)
    assert json.dumps({"disableAllHooks": True}) in json.loads(args_file.read_text())


# --- decision ---------------------------------------------------------------


def test_go_ahead_follows_model(stub_claude, plan_transcript):
    stub_claude("OTHER\n")
    assert not is_go_ahead("ok go", plan_transcript)


def test_go_ahead_needs_a_plan(stub_claude, write_transcript):
    stub_claude("APPROVE\n")
    assert not is_go_ahead("go", write_transcript([human("hi")]))


def test_go_ahead_falls_back_to_regex(tmp_path, monkeypatch, plan_transcript):
    monkeypatch.setenv("TEST_ME_CLAUDE_BIN", str(tmp_path / "missing"))
    assert is_go_ahead("ok go ahead", plan_transcript)


def test_go_ahead_respects_opt_out(stub_claude, plan_transcript):
    stub_claude("APPROVE\n")
    assert not is_go_ahead("go ahead, no test", plan_transcript)


# --- hook process -----------------------------------------------------------


def run_hook(prompt, transcript_path):
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"prompt": prompt, "transcript_path": transcript_path}),
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_hook_emits_context_on_go_ahead(stub_claude, plan_transcript):
    stub_claude("APPROVE\n")
    out = run_hook("ok let's do", plan_transcript)
    assert "test-me" in json.loads(out)["hookSpecificOutput"]["additionalContext"]


def test_hook_silent_on_other_prompt(stub_claude, plan_transcript):
    stub_claude("OTHER\n")
    assert run_hook("let's go back to the other file", plan_transcript) == ""


# --- live model (needs a logged-in `claude` CLI) ----------------------------

live = pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI not found")


@live
@pytest.mark.parametrize(
    "prompt",
    ["ok go ahead but rename it fetch_all first", "vas-y", "sounds good, ship it"],
)
def test_live_model_approves(prompt):
    assert classify(prompt, PLAN) is True


@live
@pytest.mark.parametrize(
    "prompt",
    ["don't do it", "let's go back to the other file", "ok but why bar?"],
)
def test_live_model_rejects(prompt):
    assert classify(prompt, PLAN) is False
