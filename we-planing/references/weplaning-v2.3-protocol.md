# WePlaning v2.3 Protocol

WePlaning is project-owned Markdown memory for multi-session and multi-Agent collaboration. It keeps accepted state, session branches, and durable changes in files that humans can read and Git can diff.

## Required Structure

```text
.agent-memory/
├── CURRENT.md
├── THREADS.md
├── CHANGES.md
└── sessions/
    └── <session-id>.md
```

`WePlaning.md` is not part of v2.3. Old projects may still contain it; scripts ignore it.

Optional files such as `TOOLS.md`, `PROJECT.md`, `DECISIONS.md`, `DONE.md`, and `notes/` can be created when useful. They do not define the mainline.

## Session ID

New sessions use:

```text
YYYYMMDDTHHMM-agent-4char
```

Example:

```text
20260606T1405-codex-a3f9
```

Old v2.2 session IDs remain valid because scripts treat session IDs as opaque strings.

## CURRENT.md

Required fields:

```markdown
# Current Mainline
Schema version: 2.3
Last updated: <iso-time>
Mainline session: <session-id>

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
- Session: <session-id>
- Last change: <iso-time> <summary>
```

## THREADS.md

Required fields:

```markdown
# Threads
Schema version: 2.3
Last updated: <iso-time>

Mainline session: <session-id>
Last merged session: <session-id>

## Session Tree

| Session ID | Parent | Agent | OS | Role | Status | Summary |
|:--|:--|:--|:--|:--|:--|:--|
| <id> | <parent> | <agent> | <os> | <role> | active|merged|paused|abandoned|closed | <summary> |
```

## CHANGES.md

Append-only ledger:

```markdown
# Changes
Schema version: 2.3

## <change-id>
- Session: <session-id>
- Agent: <agent>
- Role: <role>
- Based on: <mainline-or-parent>
- Change ID: <change-id>
- Changed:
  - <durable change>
- Files touched:
  - <path>
- Verification:
  - <command/result>
- Notes:
  - none
```

## Session File

Each session file lives under `sessions/<id>.md` and records in-progress or completed work:

```markdown
# Session <id>

Schema version: 2.3
Session ID: <id>
Agent: <agent>
Adapter: <adapter>
OS: <os>
Role: <role>
Parent session: <id>
Status: active|merged|paused|abandoned|closed

`closed` is a terminal status for Lite/Quick-Note sessions that are finished but were never merged into the mainline (used by `weplaning-note.cjs` auto-close). It is valid for non-mainline rows; the consistency gate still requires the mainline session to be `merged`.

THREADS.md Summary cells are truncated to 120 characters on write. Full text stays in the session file. `weplaning-close.cjs` is the one-command closeout (creates a session if needed; defaults to leaving CURRENT.md prose unchanged).
Started: <iso-time>
Closed: <iso-time|unknown>

## Goal
<goal>

## Context Read
- <file or fact>

## Work Notes
- <note>

## Files Touched
- <path>

## Decisions
- none yet

## Result
<result>

## Exact Next Step
<next step>
```

## Consistency Gate

`check-memory.cjs` verifies:

- required files and `sessions/` exist;
- `CURRENT.md`, `THREADS.md`, and `CHANGES.md` use schema `2.2` or `2.3`;
- `CURRENT.md Mainline session` equals `THREADS.md Mainline session`;
- `Last merged session` equals mainline;
- mainline row exists and is `merged`;
- mainline session file exists and is `merged`.

`check-memory.cjs --audit` also checks stale `Based On`, placeholder mainline result, placeholder exact next step, and mixed real/no-blocker bullets.

## Write Rules

1. Re-read `CURRENT.md` and `THREADS.md` before writing.
2. Use one session for durable work.
3. Append change ledger entries; do not replace old entries.
4. Run `check-memory.cjs` after any `.agent-memory/` write.
5. Run `repair-memory.cjs` only after a failed check and only when the cause is clear.
6. Never store secrets or private credentials.

## Cross-Agent Adaptation

An Agent needs file read, file write/edit, directory listing, and enough shell or file operations to run or emulate the scripts. Do not invent tool names from the Agent brand. Inspect the actual environment first, then map these operations:

- read `CURRENT.md`, `THREADS.md`, `CHANGES.md`, and sessions;
- create or edit one session file;
- append `CHANGES.md`;
- update `THREADS.md` and `CURRENT.md` on closeout;
- run or emulate `check-memory.cjs`.
