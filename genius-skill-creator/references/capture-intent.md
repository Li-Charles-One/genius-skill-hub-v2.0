# Capture Intent

Use this before scaffolding a new skill. Human words are commentary. Files, links, screenshots, and the current conversation are evidence.

## Source order

1. **This conversation.** If the user already completed a workflow, extract tools used, step order, corrections, and input/output shapes. "Turn this into a skill" means harvest the session, not start a questionnaire.
2. **Artifacts.** Spreadsheets, scripts, PDFs, screenshots, and URLs outrank the user's summary. Tab names, column headers, and error text are the spec.
3. **One-line hypothesis.** State: "You do X to get Y, on Z cadence. Right?" Wait for a short confirm or correction.
4. **Gaps only.** Ask about missing I/O, success criteria, or dependencies. Do not open with five blank questions.

## Input triage

| What they gave | What to do |
|---|---|
| Finished chat workflow | Harvest steps and corrections from the thread |
| Files only | Reverse-engineer the workflow from structure |
| URLs only | Fetch, then infer the job from the data surface |
| Screenshot | Name the tool, the data, and the painful manual step |
| One word | Infer from role and nearby skills; confirm the guess |
| Mixed files + sentence | Files are the spec; the sentence is commentary |

## Rules

- Build at about 60% understanding. A concrete wrong draft is faster than a perfect interview.
- If a file will not parse or a URL is down, continue from what you have and flag the gap.
- Sometimes the answer is "you do not need a skill." Say so.
- After confirm, fill purpose, trigger, non-goals, outputs, and dependencies, then scaffold.

## Description craft

Write the `description` a bit pushy so the skill is not under-triggered. Name the job, the phrases that should fire it, and the non-goals. Keep non-goals as near misses, not unrelated chores.
