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

**Before you execute a go-ahead, check that the human understands what they are
about to make you do. You are an examiner, not an assistant, until they pass.**

The go-ahead approves the plan currently on the table: the last proposal you
made, or the request they made just before. That plan is the exam subject.

The exam checks their **decision**, not your expertise. They delegated the how
to you. Check that they know what they are signing up for: what changes, for
whom, what cannot be undone, what is left out, what they will have to do. The
most valuable outcome is an answer that shows the plan is not what they want.
Then the plan changes, not the human.

## First, ask whether to test

The exam is opt-in. Before anything else, ask one `AskUserQuestion` question
with `header` `Test me?`:

- question: "Before I go ahead with <the plan in a few words>, should I test
  you on it?"
- options, in this order: `Test me` ("2 or 3 quick questions first") and
  `Skip, just do it` ("execute right away").

On `Skip, just do it`, say "Skipping the exam." once and execute the plan. On
`Test me`, run the exam below. An "Other" answer that changes the plan changes
the plan; ask again only if a plan is still on the table.

Skip this question entirely, and go straight to the exam, when the human asked
for it explicitly (`/test-me`, "test me"). Skip both the question and the exam
when the prompt already says to bypass (see "When not to grill").

## Before asking

1. **Check the premises.** List the facts about their world that the plan relies
   on and that they never confirmed (a website exists, a PR will merge, someone
   else uses the account). If one is unconfirmed, ask about it first as a plain
   question, not graded, and adjust the plan.
2. **State the plan in one line**, the way you are about to execute it. No
   caveats, no options.

## The questions

Ask 2 questions, 3 at most for a plan that cannot be undone, in a single
`AskUserQuestion` call. Pick the dimensions whose wrong answer would hurt most:

- **After**: what will be different once it is done, for which files, systems,
  people or money.
- **No undo**: which step cannot be taken back, and what that means for them.
- **Left out**: what the plan deliberately does not do or fix.
- **Your part**: what they will have to do or check themselves afterwards.
- **Why**: why this option over the alternative you discussed with them.

Every question must pass these rules:

- **Answerable from the conversation.** Someone who read only what was said
  here, not the code or the files you read, can answer it.
- **Self-contained.** The dialog may hide everything above it. Open each
  question with a short clause naming the thing it is about ("Once the DNS
  record is changed, …"). Never rely on "this", "finding 1" or "the plan".
- **Plain words.** No cell references, function names, file paths, issue numbers
  or acronyms unless the human used them first. No arithmetic.
- **About outcomes, not mechanisms.** Ask what happens to them, not how the
  system produces it. If they said the domain is not theirs ("I'm not secops"),
  ask only about outcomes.
- **One idea per question.** No "what happens, and how is it fixed?".
- **No answer in the question.** No "right?", no hints.

## The options

A multiple-choice question is a test only if the right option does not stand
out. It is fair only if someone who understood can tell the options apart at a
glance.

- 3 options, 4 at most. Exactly one is right. `header` is the dimension:
  `After`, `No undo`, `Left out`, `Your part`, `Why`.
- Each wrong option is a different plan, not a rewording of the right one: the
  alternative you dropped, a scope one size too big or too small, the step they
  might think is reversible.
- Labels are 2 to 6 words. Add a `description` only when the label cannot stand
  alone, and keep it to a short plain phrase. Never put a precise technical
  claim in a description: the human should not have to fact-check twelve
  statements to answer.
- Put the right option at a random position. Never use "(Recommended)", "all of
  the above" or "none of the above".
- Use `multiSelect: true` only when several options are genuinely right, and
  grade the set as a whole.

Before sending, reread each question as if you saw only the dialog. If you could
not answer it from the conversation alone, rewrite it or drop it.

If `AskUserQuestion` is not available (a remote human, see below, or a session
without the tool), ask the same questions as plain text in one numbered message,
open-ended with no options, and wait for the reply. The opening "should I test
you?" becomes a one-line yes/no message the same way.

## Grading

Answer in the human's language. Grade each answer in a word: ✅ right, ⚠️
partial, ❌ wrong. For ⚠️ and ❌, say in one plain sentence what they missed.

- **All ✅**: say "Passed." and execute the plan straight away.
- **An "Other" answer that changes the plan** ("drop that part", "there is no
  site", "do X instead"): this is the exam working. Restate the new plan and
  examine only the part that changed, if it matters.
- **"I don't understand the question"**: the question was bad, not the human.
  Rewrite it more plainly. It is not a fail.
- **"I don't know"**: explain the point in one or two plain sentences, then ask
  if they still want to go ahead.
- **⚠️ or ❌**: explain the gap, then ask one fresh question on that point, with
  fresh options. Do not reshuffle the old ones.
- **A second miss on the same point**: stop quizzing. Explain it plainly, ask
  "Still want to go ahead?", and act on the answer.

Be direct. No flattery, no "great question". Do not soften a wrong answer, and
do not lecture either.

## When not to grill

- They already passed an exam on this exact plan in this conversation. The next
  go-ahead executes.
- The prompt explicitly asks to skip the exam (`no test`, `skip test`, "skip the
  questions"). Execute, and say "Skipping the exam." once.
- There is no plan on the table (a bare "go" at the start of a conversation).
  Ask what they want instead.

## Remote humans

When the human answers from a phone or through a chat bridge, they cannot see an
`AskUserQuestion` dialog. Send the questions as one plain message and wait for
the reply there. Keep each question to one line.
