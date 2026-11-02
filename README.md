# test-me

A Claude Code plugin that makes you prove you understand a plan before Claude
executes it.

When you approve the plan Claude just proposed ("ok let's do", "go ahead but
rename it first", "vas-y", "sounds good, ship it"), a `UserPromptSubmit` hook
tells Claude to run the `test-me` skill first. Claude then:

1. restates the plan in one line;
2. asks 2 to 4 pointed questions about it (what changes, what cannot be undone,
   scope, how you will check it, cost, why this option), with no hints;
3. grades each answer ✅ / ⚠️ / ❌ and re-asks on weak points;
4. executes only once you pass.

Add `no test` or `skip test` to a go-ahead to bypass it. You are not examined
twice on the same plan in one conversation. You can also run it on demand with
`/test-me`.

## How a go-ahead is detected

1. **Cheap gate.** Only prompts under 200 characters containing an
   approval-ish word (ok, yes, go, do, proceed, ship, lgtm, vas, allez, …) go
   further. Everything else passes instantly.
2. **Context.** The hook reads Claude's last message from the session
   transcript. No message, no plan, no exam.
3. **Model.** Haiku, through your own logged-in `claude` CLI (no API key, hooks
   disabled in the nested call, no session saved), reads that message and your
   reply and answers APPROVE or OTHER. So "don't do it" or "let's go back to
   the other file" do not trigger, while "ok go ahead but rename it first"
   does. This adds about 2 seconds to candidate prompts only.
4. **Fallback.** If the CLI is missing, fails or times out, a strict regex
   accepts only a bare approval ("go", "ok let's do it", "vas-y").

Set `TEST_ME_CLAUDE_BIN` to use a `claude` binary that is not on `PATH`.

## Install

```text
/plugin marketplace add ClementWalter/test-me
/plugin install test-me@test-me
```

Or from a shell:

```bash
claude plugin marketplace add ClementWalter/test-me
claude plugin install test-me@test-me
```

The hook needs `python3` (standard library only) and the `claude` CLI on your
`PATH`.

## Layout

```text
.claude-plugin/   plugin.json + marketplace.json
skills/test-me/   the exam the agent runs
hooks/            go-ahead detector (UserPromptSubmit)
tests/            pytest suite
```

## Test

```bash
uv run --with pytest pytest -q tests
```

The `live` tests call the real model and are skipped when `claude` is not on
`PATH` (as in CI).
