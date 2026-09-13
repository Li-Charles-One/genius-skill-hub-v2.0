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

## <iso-time> change <unique-suffix>
- Agent: <agent>
- Change ID: <iso-time> change <unique-suffix>
- Changed:
  - <durable change>
- Files touched:
  - <path or none>
- Verification:
  - <check or none>
- Notes:
  - none
```

Do not replace old entries. Existing timestamp-only entries remain valid. New writes use a unique suffix; an actual CURRENT patch without explicit `--changed` still creates a factual ledger entry. Unchanged patches without a new fact or decision do not update files or timestamps.

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
- CURRENT has one nonempty Active Goal, Current State, Accepted Next Steps, Open Blockers section; known optional sections cannot be duplicated;
- heading whitespace follows the same rules as reading/writing, and schema lines cannot be duplicated;
- no merge conflict markers;
- no `*.sync-conflict-*` copies.

It does **not** require THREADS.md, sessions/, or a mainline session id.

`--audit` warns on mixed real/no-blocker bullets. Warnings exit 0 unless `--strict`.

## Write Rules

1. Re-read `CURRENT.md` before writing.
2. Use `weplaning-write.cjs`. `--changed` appends the ledger and never overwrites Current State.
3. Pass `--state` / `--next-step` / `--goal` / `--blockers` only when those sections should change. Keep still-valid items in any replaced section; unrelated content is preserved.
4. Trivial oral notes (`完成了`, `done`, `搞定`) with no patch and no decision do not write.
5. Run `check-memory.cjs` after any `.agent-memory/` write.
6. Never store secrets or private credentials.
7. Do not record this skill's own maintenance in a business project's memory.
8. Validate arguments, existing memory and all proposed file contents before writing, then check the written result. Recognized invalid inputs do not change memory files.
9. Repair may insert a missing schema line; it does not reconstruct malformed accepted state or discard unrecognized text. Archive files must be created with unique names without overwriting history.

## Read and Handoff

- Report Current Understanding and Last updated alongside recorded state. Read time, memory update time and verification time have different meanings.
- Handoff surfaces recorded verification/file references from recent changes; these are evidence of past checks, not newly executed checks.
- Accepted Next Steps contains accepted actions; store durable guidance in Current Understanding. Use `none` / `无待执行事项` for no work and `unknown` for undecided work. Handoff does not execute either placeholder.
- Keep unknown blockers visible. Invalid `--next N` is an error; never substitute a different task.
- Search prioritizes CURRENT over historical matches. History provides context but does not override accepted current state.

## Legacy 2.3

Old session files may remain for audit. Do not create new ones. `repair-memory.cjs` does not rebuild session trees.
