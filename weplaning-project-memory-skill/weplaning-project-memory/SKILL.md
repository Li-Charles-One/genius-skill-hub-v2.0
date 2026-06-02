---
name: weplaning-project-memory
description: Maintain WePlaning v2.2 project collaboration memory. Use when the user asks to initialize, resume, continue, close, summarize, hand off, audit, migrate, or repair `.agent-memory/` project memory; when managing multi-Agent or multi-session project state; or when updating required files such as `CURRENT.md`, `THREADS.md`, `CHANGES.md`, `TOOLS.md`, `sessions/`, plus optional indexes/context such as `DECISIONS.md`, `DONE.md`, `PROJECT.md`, or `notes/`.
---

# WePlaning Project Memory

## Overview

Use WePlaning v2.2 as a lightweight, project-owned memory protocol for multi-Agent and multi-session collaboration. Keep the project mainline, session branches, change ledger, tool registry, and handoff context synchronized through `.agent-memory/`.

Read `references/weplaning-v2.2-protocol.md` only when you need exact schema details, migration rules, or protocol wording. For routine work, follow this skill file.

For adapting WePlaning to non-Codex Agents, read `AGENT-INSTRUCTIONS.md`. It requires identifying the target Agent and discovering its real tool surface before mapping protocol operations.

## 🚨 MANDATORY Discipline (MUST — not "should")

These rules are NOT advisory. The Agent MUST execute them; skipping any is a protocol violation.

### P0: ONCE per project — inject rules into system prompt

The first time you use WePlaning on a project (or when the user asks to "remember the rules"):

**Create a `priority: high` project memory** using the Agent's `remember` tool (or equivalent). This ensures every future session gets the discipline rules BEFORE it even invokes the skill.

Memory name: `weplaning-auto-discipline`
Memory content: the three mandatory rules below (check-memory on every write, merge-session on closeout, TOOLS.md update before merge). Write them as imperative Agent instructions, not suggestions.

Then ALSO follow the rules in this SKILL.md when the skill is invoked. The memory is the safety net; the skill is the playbook.

### On every memory write

After ANY write to `.agent-memory/` (CURRENT.md edit, session update, CHANGES.md append, TOOLS.md edit):

```bash
node <skill-dir>/scripts/check-memory.cjs <project-root>
```

If it fails → run `repair-memory.cjs` first, then re-check. Do NOT report success until the gate passes.

### On session closeout

When a session produces durable changes (files edited, decisions made, state changed):

1. Run `pre-close-check.cjs` — scans for TOOLS.md unknowns, CHANGES.md unknowns, mainline drift.
2. Fix any warnings: update TOOLS.md, re-run append-change with --file/--verification.
3. Update `TOOLS.md` — fill in ALL tools actually used this session (not "unknown").
4. Run `merge-session.cjs` — this syncs THREADS.md, CURRENT.md, WePlaning.md automatically.
5. Run `check-memory.cjs` — confirm all invariants hold.
6. Only then report "memory updated successfully."

### Before starting any new session

1. Read `WePlaning.md`, `CURRENT.md`, `THREADS.md`, recent `CHANGES.md`, and `TOOLS.md`.
2. Run `new-session.cjs` to create the session file.
3. Update `TOOLS.md` with this session's Agent capabilities.

### Why this is mandatory

Prior sessions without this discipline caused:
- Mainline drift (CURRENT.md content from session X, mainline pointer still on session Y)
- TOOLS.md staling ("unknown" tools, outdated session notes)
- CHANGES.md with `unknown` files and verification
- Session files not reflecting actual closeout state

The scripts make all of this automatic. The Agent just needs to CALL them.

## Bundled Scripts

Prefer bundled scripts for routine memory operations. They reduce token use and prevent Markdown drift.

Use from the skill directory:

```bash
node scripts/check-memory.cjs <project-root>
node scripts/init-memory.cjs <project-root> --project "<name>" --goal "<goal>"
node scripts/new-session.cjs <project-root> --role <role> --summary "<summary>" --goal "<goal>"
node scripts/append-change.cjs <project-root> --session <session-id> --changed "<change>"
node scripts/close-session.cjs <project-root> --session <session-id> --status <paused|abandoned|merged>
node scripts/merge-session.cjs <project-root> --session <session-id>
node scripts/repair-memory.cjs <project-root>
node scripts/session-list.cjs <project-root>
node scripts/register-agent.cjs <project-root> --session <session-id> --agent "<name>" --adapter "<adapter>"
node scripts/sync-before-write.cjs <project-root> --session <session-id>
node scripts/handoff.cjs <project-root> --session <session-id>
node scripts/pre-close-check.cjs <project-root> [--session <id>] [--fix]
node scripts/sync-skill-package.cjs --source <skill-dir> --target <skill-dir>
```

Use scripts first for:

- initializing Minimal Mode memory;
- creating session files and `THREADS.md` entries;
- appending standard `CHANGES.md` entries;
- closing or pausing sessions;
- merging a session to mainline;
- repairing common mainline/session drift;
- listing session status snapshots;
- registering Agent capability into `TOOLS.md`;
- checking that an Agent is writing from the latest mainline;
- generating handoff packets;
- scanning for pre-close issues (unknown TOOLS/CHANGES fields, mainline drift);
- syncing a changed skill package to a local Skill Hub or mirror;
- running the consistency gate.

Manual edits are still allowed for nuanced content, but run the consistency gate afterward.

## Cross-Agent Sync Rules

Use these rules whenever multiple Agents or tools may update the same project memory.

- Before writing, run `scripts/sync-before-write.cjs` with either `--session <id>` or `--based-on <mainline-id>`.
- Register each Agent's capability with `scripts/register-agent.cjs` before closeout when the Agent or tool surface is new.
- Keep each Agent's work in its own session file; do not edit another active Agent's session except for explicit repair.
- If the mainline changed since a session's parent, do not merge blindly. Re-read `CURRENT.md`, re-apply the durable result, or leave the session paused.
- Use `scripts/handoff.cjs` for standard handoff packets.
- Run `scripts/check-memory.cjs` after any memory write.

## Skill Package Sync Rules

Use these rules when this skill itself is changed.

- Treat the Codex skill directory as the source package unless the user says otherwise.
- Sync the complete package to the configured Skill Hub or mirror with `scripts/sync-skill-package.cjs`.
- Validate both source and target skill directories with the skill validation script.
- Verify source and target hashes match after syncing.
- If the skill update affects memory behavior, record the update in the project `CHANGES.md`.
- Do not report a skill sync complete until package sync, validation, and hash comparison have passed.

## Core Model

Default to Minimal Mode. Treat these files as the required collaboration surface:

```text
.agent-memory/
+-- WePlaning.md       Signpost and snapshot
+-- CURRENT.md         Accepted project mainline only
+-- THREADS.md         Session tree and mainline pointer
+-- CHANGES.md         Append-only change ledger
+-- TOOLS.md           Tool/MCP/skill/script capability registry
+-- sessions/          One Markdown file per Agent conversation
```

Rules:

- `CURRENT.md` is the accepted mainline, not scratch space.
- `sessions/<session_id>.md` is the working branch for one Agent conversation.
- `THREADS.md` records parent relationships and the current mainline session.
- `CHANGES.md` is the canonical append-only ledger.
- `TOOLS.md` records capabilities, never secrets.
- Optional files are indexes or context, not new truth sources.
- Use repo-relative paths with `/` for project files. Mark local absolute paths as `local-only`.
- After any memory write, run the project memory consistency check when available before reporting success.

## Operating Modes

Minimal Mode is required and is the default. Upgrade only on explicit user request or hard triggers.

Standard Mode adds:

```text
+-- PROJECT.md         Stable project identity
+-- notes/             Archived long-form outputs
```

Full Mode adds:

```text
+-- DECISIONS.md       Optional decision index derived from CHANGES.md
+-- DONE.md            Optional completed-work index derived from CHANGES.md
+-- FUTURE.md          Plans, risks, debt
+-- REFERENCES.md      Important paths and references
+-- SCRIPTS.md         Project scripts and commands
```

Upgrade triggers:

- Create `PROJECT.md` when stable project identity, tech stack, or long-term role cannot fit in `WePlaning.md`.
- Create `notes/` when archiving a long-form output, audit, design plan, or report.
- Create `DECISIONS.md` after at least 5 decision entries in `CHANGES.md` or when decisions need independent review.
- Create `DONE.md` after at least 5 done entries in `CHANGES.md` or when completed work needs date-based review.
- Create `FUTURE.md` after at least 3 future/risk/debt items.
- Create `REFERENCES.md` after at least 5 important references or paths.
- Create `SCRIPTS.md` after at least 3 scripts or when scripts have cross-platform/dependency complexity.

Information routing:

| Information | File |
|:--|:--|
| Accepted current facts | `CURRENT.md` |
| Conversation work notes | `sessions/<session_id>.md` |
| Session tree | `THREADS.md` |
| Who changed what | `CHANGES.md` |
| Tool capabilities | `TOOLS.md` |
| Decisions | `CHANGES.md`; optionally `DECISIONS.md` in Full Mode |
| Completed work | `CHANGES.md`; optionally `DONE.md` in Full Mode |
| Long-form output | `notes/` when Standard Mode is enabled |
| Project identity | `PROJECT.md` when Standard Mode is enabled; otherwise `WePlaning.md` |

## Session IDs

Use this format:

```text
<UTC timestamp>-<agent>-<os>-<role>-<short id>
```

Example:

```text
20260601T063000Z-codex-win-editor-a3f9
```

Roles: `creator`, `editor`, `auditor`, `reviewer`, `implementer`, or `other`.

Statuses: `active`, `paused`, `merged`, `abandoned`.

## Workflows

### Bootstrap

Use when the project has no `.agent-memory/` or the user asks to set up WePlaning.

1. Prefer `scripts/init-memory.cjs` to create `.agent-memory/`, Minimal Mode files, and the root merged session.
2. Record available capabilities in `TOOLS.md` after initialization if the defaults are incomplete.
3. Create optional files only when their mode or trigger is enabled.
4. Run the consistency gate.

### Start Or Resume Work

Use when continuing a project, switching Agents, opening a new conversation, auditing, or editing.

1. Read `WePlaning.md`, `CURRENT.md`, `THREADS.md`, recent `CHANGES.md`, and `TOOLS.md` if tool capability matters.
2. If a session will change project or memory state, prefer `scripts/new-session.cjs` to create the session file and add the `THREADS.md` row.
3. Set `Parent session` to the current mainline session unless intentionally branching from another session.
4. Register basic tool capability in `TOOLS.md`; record MCP, scripts, and skills before closeout if used.

### During Work

- Write durable notes into the current session file.
- Do not use `CURRENT.md` as scratch space.
- Record important "why" decisions as `decision` entries in `CHANGES.md`.
- Also index decisions in `DECISIONS.md` only when Full Mode is enabled.
- Save durable change summaries for closeout instead of logging every tiny edit.
- If a memory write changes session status, mainline, snapshot counts, or accepted state, run the consistency gate before continuing.

### Close A Session

Close means preserving this conversation state. It does not always mean the work is complete.

Close when the user asks to stop, summarize, hand off, close, switch Agents, or when work reaches a stable checkpoint, changes project/memory files, makes durable decisions, or needs exact next steps saved.

At closeout:

1. Prefer `scripts/close-session.cjs` for `paused` or `abandoned` closeout.
2. Prefer `scripts/merge-session.cjs` when closeout should become accepted mainline.
3. Prefer `scripts/append-change.cjs` to append to `CHANGES.md` if durable changes occurred.
4. Update `TOOLS.md` if notable tools, MCP servers, scripts, or skills were used.
5. Update `DECISIONS.md` or `DONE.md` only if Full Mode is enabled and relevant.
6. Refresh `WePlaning.md` manually only when scripts are not used.
7. Run the consistency gate.

### Merge To Mainline

Merge only when the session result should become accepted project state.

Before merging, check whether the session parent is still the `THREADS.md` mainline. If not, re-read the current mainline, re-apply the session's durable result, or record a conflict and leave the session `paused`.

When merging:

1. Prefer `scripts/merge-session.cjs` to set session status, update `THREADS.md`, refresh `CURRENT.md` metadata, refresh `WePlaning.md`, and run the consistency gate.
2. Append `CHANGES.md` with `scripts/append-change.cjs` when durable changes should be recorded.
3. Update `DECISIONS.md` and `DONE.md` only if Full Mode is enabled and relevant.
4. If merging manually, set the session status to `merged`, update `THREADS.md` `Mainline session`, update `THREADS.md` `Last merged session` to the same session, update `CURRENT.md`, refresh `WePlaning.md`, and run the consistency gate.

### Handoff

When asked for handoff, closeout, summary, or equivalent Chinese requests such as jiaojie/zongjie/shouwei, output this packet in chat:

```markdown
Project:
Current mainline session:
Current session:
Parent session:
Current goal:
Current state:
Important files:
Tools used:
Commands/tests run:
Open blockers:
Session status:
Should merge to mainline:
Exact next step:
```

Write `unknown` for uncertain fields. Do not invent missing facts.

## Checks

### Consistency Gate

Run after every memory write and before saying memory was updated successfully.

If `.agent-memory/scripts/check-memory.js` exists, run:

```bash
node .agent-memory/scripts/check-memory.js
```

If `.agent-memory/scripts/check-memory.cjs` exists, run:

```bash
node .agent-memory/scripts/check-memory.cjs
```

If no project check script exists, use the bundled script from this skill:

```bash
node <skill-dir>/scripts/check-memory.cjs <project-root>
```

When the user wants a self-contained project memory package, copy the bundled script into the project at `.agent-memory/scripts/check-memory.cjs` and record that in `CHANGES.md`.

If a project provides another `check-memory` script in `.agent-memory/scripts/`, use it. If no script is available, perform the manual checks below and consider creating or copying the bundled script when the user asks for reliability.

Hard invariants:

- `CURRENT.md` `Mainline session` equals `THREADS.md` `Mainline session`.
- `WePlaning.md` snapshot `Mainline session` equals `THREADS.md` `Mainline session`.
- `THREADS.md` `Last merged session` equals `THREADS.md` `Mainline session` after a mainline merge.
- The mainline session appears in the `THREADS.md` session tree.
- The mainline session file exists under `.agent-memory/sessions/`.
- The mainline row in `THREADS.md` has status `merged`.
- The mainline session file has `Status: merged`.
- `WePlaning.md` snapshot `Active sessions` equals the count of `active` rows in `THREADS.md`.
- Required Minimal Mode files and session files declare `Schema version: 2.2`.

If the gate fails:

1. Do not report success.
2. Prefer `scripts/repair-memory.cjs` for common mainline/session drift.
3. Repair any remaining inconsistent file(s), preserving human edits.
4. Re-run the gate.
5. Record the repair in `CHANGES.md` when it changes durable memory state.

### Drift Check

Check whether memory still matches project reality:

- `CURRENT.md` mainline session exists in `THREADS.md`.
- The mainline session file exists under `sessions/`.
- Recent project file changes are reflected in `CHANGES.md`; `DONE.md` is only an optional Full Mode index.
- Paths in `REFERENCES.md` and `SCRIPTS.md` still exist when those files are enabled.
- Tool assumptions in `TOOLS.md` are still true enough.

### Schema Health Check

Check internal consistency:

- Minimal Mode files exist and declare `Schema version: 2.2`.
- Enabled Standard/Full Mode files should declare `Schema version: 2.2`.
- Session files should declare `Schema version: 2.2`.
- Archived notes may omit schema headers.
- Session references in `THREADS.md`, `CURRENT.md`, and `CHANGES.md` point to real entries.
- Append-only files are not obviously corrupted.

## Migration From v2.1

Use when upgrading an existing v2.1 project:

1. Create `sessions/` and `notes/`.
2. Create `THREADS.md`, `CHANGES.md`, and `TOOLS.md`.
3. Create a synthetic root session with status `merged`.
4. Strip scratch notes out of `CURRENT.md`; keep only accepted mainline state.
5. Update enabled memory file headers to `Schema version: 2.2`.
6. Run Drift Check and Schema Health Check.
7. Record the migration in `CHANGES.md`.

## Safety

- Never record secrets, API keys, tokens, cookies, private MCP credentials, or passwords.
- Never silently overwrite human edits.
- Preserve paused and abandoned session files.
- Use `unknown` for uncertain information and `unavailable` for unavailable tools.
- Keep memory files concise; archive long-form outputs under `notes/` only when Standard Mode is enabled.

## Reference

- Full protocol: `references/weplaning-v2.2-protocol.md`
- Cross-Agent adapter instructions: `AGENT-INSTRUCTIONS.md`
