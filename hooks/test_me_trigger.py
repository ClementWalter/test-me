#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""UserPromptSubmit hook: route a bare go-ahead prompt to the test-me skill.

When the human approves a plan with a short "ok let's do" / "let's go" / "vas-y",
the hook injects context telling the agent to grill them with the test-me skill
before executing. Long prompts are new instructions, not a go-ahead, so they pass.
"""

import json
import logging
import re
import sys

logger = logging.getLogger("test-me-trigger")

# Longer prompts carry their own instructions; only a bare approval is a go-ahead.
MAX_GO_PROMPT_CHARS = 60

GO_PATTERNS = [
    r"\blet'?s\s+do\b",
    r"\blet'?s\s+go\b",
    r"\bgo\s+ahead\b",
    r"\bgo\s+for\s+it\b",
    r"\bdo\s+it\b",
    r"^\W*(ok(ay)?\W+)?go\W*$",
    r"\bvas[\s-]y\b",
    r"\ballez[\s-]y\b",
    r"\bon\s+y\s+va\b",
]

SKIP_PATTERN = r"\b(no|skip)[\s-]test\b"

CONTEXT = (
    "The human just gave a go-ahead. Before executing anything, invoke the "
    "`test-me` skill and grill them on the plan they are approving. Execute "
    "only once they pass. If they already passed an exam on this exact plan "
    "in this conversation, execute directly."
)


def is_go_ahead(prompt: str) -> bool:
    """Return True when the prompt is a short approval that should trigger the exam."""
    text = prompt.strip().lower().replace("’", "'")
    if not text or len(text) > MAX_GO_PROMPT_CHARS:
        return False
    if re.search(SKIP_PATTERN, text):
        return False
    return any(re.search(p, text) for p in GO_PATTERNS)


def main() -> None:
    """Read the hook payload on stdin and emit additional context on a go-ahead."""
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        logger.warning("invalid hook payload")
        return
    if not is_go_ahead(data.get("prompt", "")):
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
