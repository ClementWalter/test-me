# test-me

A Claude Code plugin that makes you prove you understand a plan before Claude
executes it.

When you approve the plan Claude just proposed ("ok let's do", "go ahead but
rename it first", "vas-y", "sounds good, ship it"), a `UserPromptSubmit` hook
tells Claude to run the `test-me` skill first. Claude then:

1. asks "should I test you?" in one dialog: pick `Skip, just do it` and Claude
   executes right away, pick `Test me` for the exam below;
2. checks any fact the plan assumes about your situation that you never
   confirmed;
3. restates the plan in one line and asks 2 or 3 plain questions about your
   decision (what changes, what cannot be undone, what is left out, what you
   will have to do, why this option) in one `AskUserQuestion` dialog. The
   questions cover outcomes, not how things work: no code names, no arithmetic.
   Options are short and the wrong ones are the alternative plans, plus "Other"
   to answer in your own words;
4. grades each answer ✅ / ⚠️ / ❌. An "Other" answer that changes the plan
   changes the plan. "I don't understand" makes Claude rewrite the question. A
   point missed twice gets explained, then Claude asks whether to go ahead;
5. executes only once you pass.

Add `no test` or `skip test` to a go-ahead to bypass even the question. You are
not examined twice on the same plan in one conversation. You can also run it on
demand with `/test-me`.

## How a go-ahead is detected

1. **Cheap gate.** Only prompts under 200 characters containing an approval-ish
   word (ok, yes, go, do, proceed, ship, lgtm, vas, allez, …) go further.
   Everything else passes instantly.
2. **Context.** The hook reads Claude's last message from the session
   transcript. No message, no plan, no exam.
3. **Model.** Haiku, through your own logged-in `claude` CLI (no API key, hooks
   disabled in the nested call, no session saved), reads that message and your
   reply and answers APPROVE or OTHER. So "don't do it" or "let's go back to the
   other file" do not trigger, while "ok go ahead but rename it first" does.
   This adds about 2 seconds to candidate prompts only.
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
