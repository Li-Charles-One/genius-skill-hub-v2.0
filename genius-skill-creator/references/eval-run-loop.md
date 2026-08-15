# Eval Run Loop

Use this when a skill has objectively checkable output. Do not stand up a browser reviewer. Compare in the conversation. If the user says to skip evals, skip them.

Trigger-only work stays in `eval-workflow.md`.

## When to run

Run a with-skill vs baseline comparison when:

- output is a file, command result, or other checkable artifact;
- you are creating a new skill or changing behavior of an existing one;
- the user did not opt out.

Skip for pure writing style unless the user wants a side-by-side read.

## Setup

Put results next to the skill folder, not inside it:

```text
my-skill/
my-skill-workspace/
  iteration-1/
    eval-login/
      with_skill/
      without_skill/    # new skill
      old_skill/        # improving an existing skill
```

Confirm 2-3 realistic prompts with the user before running. Casual phrasing. Include one near-miss if trigger risk matters.

## Run

For each prompt, run two passes:

1. **With skill** — load the skill, do the task, save outputs under `with_skill/`.
2. **Baseline** — new skill: same prompt, no skill, save under `without_skill/`. Improving: snapshot the pre-edit skill and run that under `old_skill/`.

Prefer two sub-agents in one turn. If sub-agents are unavailable, run both passes yourself and say the comparison is less independent.

Do not edit the skill between the paired runs of one iteration.

## Review

Show the user, per prompt: the prompt, with-skill output, baseline output, and what got better or worse. Wait for their notes before rewriting the skill.

Then:

1. Generalize. Do not overfit the two prompts.
2. Prefer a bundled script when both runs reinvented the same helper.
3. Explain why in the skill text. All-caps ALWAYS/NEVER is a yellow flag.
4. Rerun into `iteration-2/` if you changed behavior.

Stop when the user is happy, notes are empty, or another pass would not change the skill.

## What not to do

- Do not treat `contains: "Create"` on this creator's own reply as proof the generated skill works.
- Do not add an HTTP eval viewer or custom grading HTML.
- Do not keep draft workspaces inside the skill package.
