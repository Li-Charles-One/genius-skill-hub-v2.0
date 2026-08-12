---
name: we-planing
metadata:
  version: "1.9.0"
description: "Maintain WePlaning v2.3 project memory in .agent-memory. Use for: 查看项目记忆 / 读取项目记忆 / 记一笔 / 完成了 / 提交主线 / 查看项目进度 / 修一下记忆 / init, resume, hand off, close out, repair. Do not use for ordinary summaries or one-off code edits."
---

# WePlaning
_(Skill package v1.9.0; implements WePlaning protocol v2.3)_

## Use When

- The user asks to initialize, resume, hand off, close out, repair, or verify project memory.
- Multiple Agent sessions need shared durable state in `.agent-memory/`.
- You will write accepted project state, a durable note, or a change ledger entry.

Do not use for ordinary summaries, one-off answers, or trivial code-only edits unless the user explicitly wants memory persisted.

## Mode

| Intent | Command |
|---|---|
| Read memory | `weplaning-read.cjs` |
| Brief progress / current goal | `weplaning-read.cjs --brief` |
| Handoff | `weplaning-read.cjs --handoff` |
| Continue step N | `weplaning-read.cjs --next N` |
| Search history (incl. archive) | `weplaning-find.cjs` |
| Quick note | `weplaning-note.cjs` |
| Submit mainline | `weplaning-close.cjs` |
| Repair | `check-memory.cjs` then `repair-memory.cjs` |
| Init | `init-memory.cjs` |

`<skill_dir>` is this skill's directory. Do not create a session for read-only inspection. Truth order: **mainline CURRENT > closed notes > active sessions**.

## User-Facing Trigger Phrases

When the user says any of these, act — don't ask "what memory?".

| User says | Agent does |
|---|---|
| "查看项目记忆" / "读取项目记忆" | `weplaning-read.cjs` |
| "读取 .agent-memory 接力" / "读取记忆接力" | `weplaning-read.cjs --handoff` (report Focus Next Step #1) |
| "项目叫什么" / "现在目标是什么" / "查看项目进度" | `weplaning-read.cjs --brief` |
| "这件事记下来" / "记一笔" / "完成了" / "done" / "搞定" / "持久化到项目记忆" | `weplaning-note.cjs` |
| "提交主线" / "close out" / "merge to mainline" | `weplaning-close.cjs` |
| "修一下记忆" / "memory 坏了" | `check-memory.cjs` first, then `repair-memory.cjs` if the cause is known |
| "继续干 #N" | `weplaning-read.cjs --next N` → report Focus Next Step #N → start work |

Oral "完成了" is a **note**, not a mainline merge. Only "提交主线" / "close out" / "merge" runs closeout.

## Proactive Triggers

Automatically run `weplaning-note.cjs` only for **durable, cross-session** facts: accepted state changes, or a non-obvious decision (library/architecture) with `--decision`. Report the session ID.

Do **not** auto-note routine code edits, one-off fixes, or process chatter. Do **not** wait for the user to say "持久化到项目记忆".

## Commands

```bash
node <skill_dir>/scripts/weplaning-read.cjs <project-root>
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --brief
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --handoff
node <skill_dir>/scripts/weplaning-find.cjs <project-root> "<query>"
node <skill_dir>/scripts/weplaning-note.cjs <project-root> "<note>" --agent <agent-name>
node <skill_dir>/scripts/weplaning-close.cjs <project-root> --changed "<text>" --file <path> --verification "<check>" --agent <agent-name>
```

`weplaning-close` creates a session if `--session` is omitted, and defaults to `--no-sync` so curated `CURRENT.md` Current State is not replaced by `--changed`. Pass `--state` when the accepted state should change.

Full CLI, maintenance, and verification: `references/cli.md`.

## Rules

- After writing `.agent-memory/`, run `check-memory.cjs` and do not report success until it passes.
- Do not store secrets, tokens, passwords, cookies, or private credentials.
- Keep memory concise: facts, decisions, files, verification, blockers, and exact next step.
- Always pass `--agent <persona>`. Scripts fall back to `$WEPLANING_AGENT`, then a few known runtime env vars, then `Agent`.
- Before handoff, run `check-dirty.cjs` (git repo **or** ops-doc mtime fallback).
- If check fails: stop, inspect, repair or correct, then rerun check.
- Schema: `references/weplaning-v2.3-protocol.md`. Pitfalls: `references/pitfalls.md`.

**Project type:** `init-memory` writes `CURRENT.md` → Project Config. Has code → git versions code, WePlaning owns `.agent-memory` only. Ops/doc → standalone; external sync (Syncthing etc.) is outside this skill.

## Files

```text
.agent-memory/
├── CURRENT.md       accepted mainline state (+ Project Config)
├── THREADS.md       session tree and mainline pointer
├── CHANGES.md       append-only durable change ledger
├── DECISIONS.md     optional decision ledger
├── archive/         rolled-off CHANGES / THREADS
└── sessions/<id>.md one working record per Agent session
```

`.backups/` and `.weplaning.lock` are device-local scratch: never sync them, never treat them as history.

## Resource Map

- `references/weplaning-v2.3-protocol.md` — schema
- `references/cli.md` — full CLI (init, safe-edit, maintenance, JSON)
- `references/pitfalls.md` — known failure modes
- `references/hermes-install.md` — hub / junction install
- `scripts/weplaning-read.cjs`, `scripts/weplaning-find.cjs`, `scripts/weplaning-note.cjs`, `scripts/weplaning-close.cjs`
- `scripts/init-memory.cjs`, `scripts/new-session.cjs`, `scripts/safe-edit.cjs`, `scripts/check-memory.cjs`, `scripts/repair-memory.cjs`
- `scripts/check-dirty.cjs`, `scripts/session-status.cjs`, `scripts/append-decision.cjs`, `scripts/append-change.cjs`, `scripts/merge-session.cjs`
- `scripts/archive-changes.cjs`, `scripts/archive-threads.cjs`, `scripts/weplaning-utils.cjs`
- `evals/evals.json` — trigger cases
- `agents/openai.yaml`, `agents/reasonix.yaml`
- `tools/smoke-weplaning.cjs` — ship gate

## Output

- Read: goal, current state, next steps, blockers (if real), session id of focus. Do not dump entire closed-note bodies.
- Write: session id, whether check passed, and the exact next step.
- Closeout: what merged, whether `CURRENT.md` was synced or left with `--no-sync`.
