# WePlaning 3.0 Protocol

WePlaning is project-owned Markdown memory. The accepted state is one file. History is an append-only ledger. There is no session tree.

## Required Structure

```text
.agent-memory/
├── CURRENT.md
└── CHANGES.md
```

`DECISIONS.md` is optional. `THREADS.md` and `sessions/` are leftover 2.3 files: readable, not truth, not required.

## CURRENT.md

```markdown
# Current Mainline
Schema version: 3.0
Last updated: <iso-time>

## Active Goal
<current accepted goal>

## Current Understanding
<accepted context>

## Current State
- <fact>

## Accepted Next Steps
1. <next step>

## Open Blockers
- none

## Based On
- Last change: <iso-time> <summary>
```

`Project Config` is optional. A 2.2/2.3 `CURRENT.md` (including a `Mainline session` line) remains valid until the next write, which upgrades the file to 3.0 without deleting Current State.

## CHANGES.md

Append-only:

```markdown
# Changes
Schema version: 3.0

## <iso-time> change
- Agent: <agent>
- Change ID: <iso-time> change
- Changed:
  - <durable change>
- Files touched:
  - <path or none>
- Verification:
  - <check or none>
- Notes:
  - none
```

Do not replace old entries.

## DECISIONS.md

```markdown
# Decisions
Schema version: 3.0

## <iso-time> decision
- Agent: <agent>
- Decision: <text>
- Rationale: <why>
```

## Consistency Gate

`check-memory.cjs` verifies:

- `.agent-memory/CURRENT.md` and `CHANGES.md` exist;
- schema is `2.2`, `2.3`, or `3.0`;
- CURRENT has Active Goal, Current State, Accepted Next Steps, Open Blockers;
- no merge conflict markers;
- no `*.sync-conflict-*` copies.

It does **not** require THREADS.md, sessions/, or a mainline session id.

`--audit` warns on mixed real/no-blocker bullets. Warnings exit 0 unless `--strict`.

## Write Rules

1. Re-read `CURRENT.md` before writing.
2. Use `weplaning-write.cjs`. `--changed` appends the ledger and never overwrites Current State.
3. Pass `--state` / `--next-step` / `--goal` / `--blockers` only when those sections should change.
4. Trivial oral notes (`完成了`, `done`, `搞定`) with no patch and no decision do not write.
5. Run `check-memory.cjs` after any `.agent-memory/` write.
6. Never store secrets or private credentials.
7. Do not record this skill's own maintenance in a business project's memory.

## Legacy 2.3

Old session files may remain for audit. Do not create new ones. `repair-memory.cjs` does not rebuild session trees.
