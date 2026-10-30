# test-me

A Claude Code plugin that makes you prove you understand a plan before Claude
executes it.

When you approve with a short go-ahead ("ok let's do", "let's go", "go ahead",
"go for it", "do it", "go", "vas-y", "on y va", "allez-y"), a `UserPromptSubmit`
hook tells Claude to run the `test-me` skill first. Claude then:

1. restates the plan in one line;
2. asks 2 to 4 pointed questions about it (what changes, what cannot be undone,
   scope, how you will check it, cost, why this option), with no hints;
3. grades each answer ✅ / ⚠️ / ❌ and re-asks on weak points;
4. executes only once you pass.

Prompts longer than 60 characters are treated as new instructions and never
trigger the exam. Add `no test` or `skip test` to a go-ahead to bypass it. You
are not examined twice on the same plan in one conversation. You can also run
it on demand with `/test-me`.

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

The hook needs `python3` on your `PATH` (standard library only).

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
