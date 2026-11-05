#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""UserPromptSubmit hook: route a go-ahead prompt to the test-me skill.

A prompt is a go-ahead when it approves the plan Claude last proposed. Short
prompts with an approval-ish word go to a small model (Haiku through the local
`claude` CLI) together with Claude's last message; the model decides. When the
model is unavailable, a strict regex decides instead. On a go-ahead the hook
injects context telling the agent to grill the human with the test-me skill.
"""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("test-me-trigger")

# Longer prompts carry their own instructions; only short replies can be approvals.
MAX_CANDIDATE_CHARS = 200
# Strict-regex fallback only accepts a bare approval.
MAX_FALLBACK_CHARS = 60
# The plan usually sits at the end of Claude's message; cap what the model reads.
MAX_CONTEXT_CHARS = 4000
# Transcripts grow to many MB; the last turn lives in the tail.
TRANSCRIPT_TAIL_BYTES = 2_000_000
# Measured ~2 s per call; leave headroom under the hook timeout.
CLASSIFIER_TIMEOUT_S = 8

# Cheap gate: the model only runs on prompts containing one of these.
CANDIDATE_PATTERN = re.compile(
    r"\b(ok(ay)?|yes|yep|yeah|sure|go|do|proceed|ship|lgtm|sounds good|"
    r"let'?s|oui|vas|allez|y va|d'accord|banco|fais|lance|ça marche)\b|👍"
)

# Anchored on the whole prompt: without context, only a bare approval is safe
# ("don't do it" and "let's go back to X" must not match).
FALLBACK_PATTERN = re.compile(
    r"^\W*(?:(?:ok(?:ay)?|yes|yep|alright|oui|bon)\W+)*"
    r"(?:let'?s\s+(?:do(?:\s+it|\s+this)?|go)|go(?:\s+ahead|\s+for\s+it)?|do\s+it|"
    r"vas[\s-]y|allez[\s-]y|on\s+y\s+va)"
    r"(?:\W+(?:then|now|alors))?\W*$"
)

SKIP_PATTERN = r"\b(no|skip)[\s-]test\b"

CLASSIFIER_PROMPT = """You decide whether a user's reply approves executing a plan.

Claude's last message to the user:
<claude>
{context}
</claude>

The user's reply:
<reply>
{prompt}
</reply>

Answer APPROVE if the reply tells Claude to go ahead and execute what Claude
proposed, even with small tweaks or conditions. Answer OTHER for anything else:
refusals, negations, questions, new or different requests, comments, or when
Claude's message proposes nothing to execute.

Answer with exactly one word: APPROVE or OTHER."""

CONTEXT = (
    "The human just gave a go-ahead. Before executing anything, invoke the "
    "`test-me` skill: first ask whether they want to be tested on the plan "
    "they are approving; if they skip, execute; otherwise grill them and "
    "execute only once they pass. If they already passed an exam on this "
    "exact plan in this conversation, execute directly."
)


def normalize(prompt: str) -> str:
    """Lowercase, trim and straighten apostrophes so patterns stay simple."""
    return prompt.strip().lower().replace("’", "'")


def is_skipped(prompt: str) -> bool:
    """Return True when the human opted out of the exam."""
    return re.search(SKIP_PATTERN, normalize(prompt)) is not None


def is_candidate(prompt: str) -> bool:
    """Return True when the prompt is short and approval-ish enough to ask the model."""
    text = normalize(prompt)
    if not text or len(text) > MAX_CANDIDATE_CHARS:
        return False
    return CANDIDATE_PATTERN.search(text) is not None


def is_fallback_go_ahead(prompt: str) -> bool:
    """Strict regex verdict used when the model cannot answer."""
    text = normalize(prompt)
    if len(text) > MAX_FALLBACK_CHARS:
        return False
    return FALLBACK_PATTERN.match(text) is not None


def _is_human_prompt(entry: dict) -> bool:
    """A real human prompt, as opposed to tool results or injected meta messages."""
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    return isinstance(content, list) and any(
        block.get("type") == "text" for block in content if isinstance(block, dict)
    )


def _assistant_text(entry: dict) -> str:
    """Visible text of an assistant entry; thinking and tool calls are ignored."""
    if entry.get("type") != "assistant" or entry.get("isSidechain"):
        return ""
    content = (entry.get("message") or {}).get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def _read_tail_lines(path: Path) -> list[str]:
    """Lines from the end of the transcript, dropping a partial first line."""
    with path.open("rb") as fh:
        size = fh.seek(0, os.SEEK_END)
        start = max(0, size - TRANSCRIPT_TAIL_BYTES)
        fh.seek(start)
        lines = fh.read().decode("utf-8", errors="replace").splitlines()
    return lines[1:] if start else lines


def last_assistant_message(transcript_path: str | None) -> str:
    """Claude's text from the latest turn that has any, or '' when there is none.

    The current prompt may or may not be in the transcript yet (it is written
    asynchronously), so the latest non-empty turn is taken either way.
    """
    if not transcript_path:
        return ""
    path = Path(transcript_path)
    if not path.is_file():
        return ""
    turns: list[list[str]] = [[]]
    for line in _read_tail_lines(path):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if _is_human_prompt(entry):
            turns.append([])
        elif text := _assistant_text(entry):
            turns[-1].append(text)
    for turn in reversed(turns):
        if turn:
            return "\n".join(turn)[-MAX_CONTEXT_CHARS:]
    return ""


def classify(prompt: str, context: str) -> bool | None:
    """Ask Haiku whether the prompt approves the plan; None when it cannot answer."""
    claude_bin = os.environ.get("TEST_ME_CLAUDE_BIN", "claude")
    cmd = [
        claude_bin,
        "-p",
        "--model",
        "haiku",
        # Without this the nested session would run this hook again.
        "--settings",
        json.dumps({"disableAllHooks": True}),
        "--strict-mcp-config",
        "--tools",
        "",
        "--disable-slash-commands",
        # Keeps classifier calls out of the user's session history.
        "--no-session-persistence",
    ]
    try:
        result = subprocess.run(
            cmd,
            input=CLASSIFIER_PROMPT.format(context=context, prompt=prompt),
            capture_output=True,
            text=True,
            timeout=CLASSIFIER_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("classifier unavailable: %s", exc)
        return None
    answer = result.stdout.strip().upper()
    if result.returncode != 0 or not answer:
        logger.warning("classifier failed: %s", result.stderr.strip()[:200])
        return None
    if answer.startswith("APPROVE"):
        return True
    if answer.startswith("OTHER"):
        return False
    logger.warning("classifier gave an unexpected answer: %s", answer[:80])
    return None


def is_go_ahead(prompt: str, transcript_path: str | None) -> bool:
    """Return True when the prompt approves the plan Claude last proposed."""
    if is_skipped(prompt) or not is_candidate(prompt):
        return False
    context = last_assistant_message(transcript_path)
    if not context:
        # Nothing was proposed, so there is no plan to approve.
        return False
    verdict = classify(prompt, context)
    if verdict is None:
        return is_fallback_go_ahead(prompt)
    return verdict


def main() -> None:
    """Read the hook payload on stdin and emit additional context on a go-ahead."""
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        logger.warning("invalid hook payload")
        return
    if not is_go_ahead(data.get("prompt", ""), data.get("transcript_path")):
        return
    # stdout is the hook protocol channel, not logging.
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": CONTEXT,
                }
            }
        )
    )


if __name__ == "__main__":
    main()
