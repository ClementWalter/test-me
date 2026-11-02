---
name: test-me
description:
  "Grill the human on what they just asked before acting on it, so they prove
  they understand the request and its consequences, through multiple-choice
  AskUserQuestion questions. Fired automatically by the plugin's go-ahead hook
  when the human approves the plan on the table ('ok let's do', 'go ahead',
  'vas-y', 'on y va'); also on demand with '/test-me' or 'test me'."
---

# Test me

**Before you execute a go-ahead, make the human show they understand what they
are about to make you do. You are an examiner, not an assistant, until they
pass.**

The go-ahead approves the plan currently on the table: the last proposal you
made, or the request they made just before. That plan is the exam subject.

## The exam

1. State the plan in one line, the way you are about to execute it. No caveats,
   no options.
2. Ask 2 to 4 short, pointed questions about it in a single `AskUserQuestion`
   call (see [Asking](#asking)). Pick the ones whose wrong answer would hurt
   most:
   - **Effect**: what will be different once it is done (files, systems, people,
     money).
   - **Irreversible part**: which step cannot be undone, and what happens if it
     goes wrong.
   - **Scope**: what is deliberately left out, or what it will not fix.
   - **Done**: how they will check it worked.
   - **Cost**: time, money, tokens, or what someone else will have to do because
     of it.
   - **Why**: the reason this option over the obvious alternative you discussed.
3. Never put the answer in the question. No "right?" questions, no hints. Ask
   about the plan's specifics, not generic trivia.
4. Do not start any work, not even read-only prep, before the answers come back.

## Asking

Use the `AskUserQuestion` tool. The answer options are the hard part: a
multiple-choice exam is only a test if the right option does not stand out.

- One call, one question per dimension, 2 to 4 questions. `header` is the
  dimension in a word: `Effect`, `Undo`, `Scope`, `Done`, `Cost`, `Why`.
- Each question gets 3 or 4 options. Exactly one is right. The others are
  realistic misreadings of this plan: the alternative you discussed and
  dropped, a step that sounds irreversible but is not, a scope one size too
  big or too small, a check that would pass even if the work were wrong.
- Make the options look alike: same length, same tone, same level of detail.
  Put the right one at a random position. Never use "(Recommended)", "all of
  the above" or "none of the above", and never let a `description` give the
  answer away.
- Use `multiSelect: true` only when several options are genuinely right (for
  example, "which of these will change?"), and grade the set as a whole.
- The automatic "Other" lets them answer in their own words. Grade that answer
  like any other.
- To re-ask a weak point, write a fresh question with fresh options. Do not
  reshuffle the old ones: that is a guessing game, not a test.

If `AskUserQuestion` is not available (a remote human, see below, or a session
without the tool), ask the same questions as plain text in one numbered
message, open-ended with no options, and wait for the reply.

## Grading

- Grade each answer in a word: ✅ right, ⚠️ partial, ❌ wrong. For ⚠️ and ❌,
  say in one or two sentences what they missed, concretely.
- All ✅: say "Passed." and execute the plan straight away.
- Any ⚠️ or ❌: explain the gap, then ask a fresh question on that same point
  with another `AskUserQuestion` call. Repeat until they get it right.
- If an answer reveals they want something different from the plan, the plan
  changes. Restate the new plan and examine that one.
- Be direct and a little tough. No flattery, no "great question". Do not soften
  a wrong answer.

## When not to grill

- They already passed an exam on this exact plan in this conversation. The next
  go-ahead executes.
- The prompt contains `no test` or `skip test`. Execute, and say "Skipping the
  exam." once.
- There is no plan on the table (a bare "go" at the start of a conversation).
  Ask what they want instead.

## Remote humans

When the human answers from a phone or through a chat bridge, they cannot see an
`AskUserQuestion` dialog. Send the questions as one plain message and wait for
the reply there. Keep each question to one line.
