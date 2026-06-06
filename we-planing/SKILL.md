---
name: we-planing
description: Maintain lightweight WePlaning v2.3 project memory only when the user asks to initialize, persist, resume, hand off, close out, repair, or verify `.agent-memory/` state across Agent sessions. Do not use for ordinary summaries or code-only edits unless project memory must be updated.
---

# WePlaning

## Use When

- The user asks to initialize, resume, hand off, close out, repair, or verify project memory.
- Multiple Agent sessions need shared durable state in `.agent-memory/`.
- You will write accepted project state, session notes, or a change ledger entry.

Do not use for ordinary summaries, one-off answers, or code-only edits unless the user explicitly wants project memory persisted.

## Files

```text
.agent-memory/
├── CURRENT.md       current accepted mainline state
├── THREADS.md       session tree and mainline pointer
├── CHANGES.md       append-only durable change ledger
└── sessions/<id>.md one working record per Agent session
```

Optional files such as `TOOLS.md`, `PROJECT.md`, `DECISIONS.md`, and `notes/` may exist, but they are not required for the base consistency gate.

## Read-Only Flow

1. Read `.agent-memory/CURRENT.md`.
2. Read `.agent-memory/THREADS.md`.
3. Read the tail of `.agent-memory/CHANGES.md`.
4. Read relevant `sessions/<id>.md` files only when needed.

Do not create a session for read-only inspection.

## Lite Flow

Use this when the user wants a durable note but not a mainline merge:

```bash
node <skill-dir>/scripts/new-session.cjs <project-root> --role <role> --summary "<summary>" --goal "<goal>"
node <skill-dir>/scripts/safe-edit.cjs <project-root> --lite --session <id> --changed "<durable note>"
```

## Closeout Flow

Use this when accepted work should become mainline:

```bash
node <skill-dir>/scripts/safe-edit.cjs <project-root> --close --session <id> \
  --changed "<what changed>" --file "<path>" --verification "<check run>"
```

This runs pre-check, appends `CHANGES.md`, merges the session, runs post-check, and restores the snapshot on failure.

## Maintenance

```bash
node <skill-dir>/scripts/init-memory.cjs <project-root> --project "<name>" --goal "<goal>"
node <skill-dir>/scripts/check-memory.cjs <project-root>
node <skill-dir>/scripts/check-memory.cjs <project-root> --audit
node <skill-dir>/scripts/repair-memory.cjs <project-root>
```

Use `repair-memory.cjs` only after `check-memory.cjs` fails and the cause is understood.

## Rules

- After writing `.agent-memory/`, run `check-memory.cjs` and do not report success until it passes.
- Do not store secrets, tokens, passwords, cookies, or private credentials.
- Keep memory concise: facts, decisions, files, verification, blockers, and exact next step.
- If check fails: stop, inspect the error, repair or correct the files, then rerun check.
- For exact schema details, read `references/weplaning-v2.3-protocol.md`.
