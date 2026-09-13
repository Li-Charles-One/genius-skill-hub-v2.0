---
name: genius-weplaning
metadata:
  version: "3.0.1"
description: "Maintain WePlaning 3.0 project memory in .agent-memory. Use for: 查看项目记忆 / 记一笔 / 提交主线 / 查看项目进度 / 修一下记忆 / init. Write patches CURRENT.md. Do not use for ordinary summaries, one-off code edits, or skill self-upgrades."
---

# Genius-WePlaning
_(Skill package v3.0.1; protocol 3.0)_

The planning handoff states and fields are defined in the repository-level [`WORKFLOW.md`](../WORKFLOW.md). Reuse the existing `CURRENT.md` sections; do not create another state file.

## Use When

- Shared durable project state lives in `.agent-memory/`.
- The user asks to read, write, repair, or initialize that memory.

Do not use for ordinary summaries, one-off answers, trivial code edits, or **this skill's own changelog**. Skill upgrades belong in the skill folder, never in a business project's memory.

## Mode

| Intent | Command |
|---|---|
| Read | `weplaning-read.cjs` |
| Brief progress | `weplaning-read.cjs --brief` |
| Handoff / continue #N | `weplaning-read.cjs --handoff` / `--next N` |
| Search history | `weplaning-read.cjs --find "<query>"` |
| Write (note or mainline) | `weplaning-write.cjs` |
| Repair | `check-memory.cjs` then `repair-memory.cjs` |
| Init | `init-memory.cjs` |

`<skill_dir>` is this skill's directory. Do not create a session. Truth: **CURRENT.md**. `CHANGES.md` is the ledger. Leftover 2.3 `THREADS.md` / `sessions/` are not truth.

## User-Facing Trigger Phrases

| User says | Agent does |
|---|---|
| "查看项目记忆" / "读取项目记忆" | `weplaning-read.cjs` |
| "读取记忆接力" | `weplaning-read.cjs --handoff`; report focus, or no pending tasks / unknown |
| "项目叫什么" / "现在目标是什么" / "查看项目进度" | `weplaning-read.cjs --brief` |
| "继续干 #N" | `weplaning-read.cjs --next N` → start the selected task only after successful selection |
| "记一笔" / "这件事记下来" / "提交主线" / "close out" | `weplaning-write.cjs` with `--changed` and CURRENT patches when facts changed |
| "完成了" / "done" / "搞定" | Call write only if there is a durable fact; trivial oral done is a no-op |
| "修一下记忆" | `check-memory.cjs` first, then `repair-memory.cjs` if the cause is known |

Oral "完成了" with no new fact **must not** write. If accepted state changed, pass `--state` / `--next-step` / `--goal` / `--blockers`. `--changed` alone never overwrites Current State.

## Workflow Handoff

When a durable transition occurs, record `Brief`, `Plan`, `Status`, and `Current Task` in the existing Current State or Accepted Next Steps sections. Use the states from `WORKFLOW.md`: `BRIEF_APPROVED`, `PLAN_DRAFT`, `PLAN_APPROVED`, `IMPLEMENTING`, `BLOCKED`, or `DONE`. Write on approvals, implementation start, blockers, or verified completion; do not write for routine task progress or ordinary code edits.

## Proactive Triggers

Auto-run `weplaning-write.cjs` only for **durable, cross-session** facts: accepted state changes, or a non-obvious decision with `--decision`.

Do **not** auto-write routine code edits, process chatter, or WePlaning/skill maintenance.

## Commands

```bash
node <skill_dir>/scripts/weplaning-read.cjs <project-root>
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --brief
node <skill_dir>/scripts/weplaning-write.cjs <project-root> --agent <name> --changed "<fact>"
node <skill_dir>/scripts/weplaning-write.cjs <project-root> --agent <name> --changed "<fact>" --state "Fact A;;Fact B" --next-step "Do C"
node <skill_dir>/scripts/check-memory.cjs <project-root>
node <skill_dir>/scripts/init-memory.cjs <project-root> --agent <name> --project "<name>" --goal "<goal>"
```

`weplaning-note.cjs` and `weplaning-close.cjs` are wrappers around write.

Full CLI: `references/cli.md`.

## Rules

- After writing `.agent-memory/`, run `check-memory.cjs` and do not report success until it passes.
- Before replacing a section, re-read it and retain still-valid facts. `--state` / `--next-step` replace the entire named section; scripts preserve other sections and extra content.
- Keep next steps actionable and accepted. Use `none` / `无待执行事项` when there is no pending work, and `unknown` when undecided. Preserve conditional triggers; reading memory does not activate them.
- Do not store secrets, tokens, passwords, cookies, or private credentials.
- Keep memory concise and factual: one fact per item, concrete file paths, decisions, verification method/time/result, blockers, exact next step. Put durable operating guidance in Current Understanding.
- Always pass `--agent <persona>`.
- Never hand-edit `.agent-memory/` when the scripts can do the write.
- Leftover 2.3 session trees are read-only; do not create new sessions.

**Project type:** `init-memory` writes `CURRENT.md` → Project Config. Has code → git versions code, WePlaning owns `.agent-memory` only. Ops/doc → standalone.

## Files

```text
.agent-memory/
├── CURRENT.md       accepted truth (goal, state, next steps, blockers)
├── CHANGES.md       append-only ledger
├── DECISIONS.md     optional decision ledger
└── archive/         rolled-off CHANGES
```

`THREADS.md` and `sessions/` may exist on old projects. Ignore them as truth. `.backups/` and `.weplaning.lock` are device-local scratch: never sync them.

## Resource Map

- `references/weplaning-v3.0-protocol.md` — schema
- `references/weplaning-v2.3-protocol.md` — leftover 2.3 pointer
- `references/cli.md` — full CLI
- `references/pitfalls.md` — failure modes
- `references/hermes-install.md` — hub / junction install
- `scripts/weplaning-read.cjs`, `scripts/weplaning-write.cjs`, `scripts/weplaning-utils.cjs`
- `scripts/weplaning-note.cjs`, `scripts/weplaning-close.cjs` — write wrappers
- `scripts/weplaning-find.cjs`, `scripts/check-dirty.cjs`, `scripts/archive-changes.cjs`, `scripts/append-decision.cjs`
- `scripts/init-memory.cjs`, `scripts/check-memory.cjs`, `scripts/repair-memory.cjs`
- Compatibility only (do not use on 3.0 projects): `scripts/new-session.cjs`, `scripts/safe-edit.cjs`, `scripts/merge-session.cjs`, `scripts/session-status.cjs`, `scripts/archive-threads.cjs`, `scripts/append-change.cjs`
- `evals/evals.json`

## Output

- Read: memory update time, goal, key understanding, recorded state, next steps, blockers (including unknown), last few ledger lines. A read is not live verification; update time is not verification time. Handoff also includes recorded verification/file references.
- Handoff: no pending tasks means stop; unknown means clarify. Invalid task numbers are errors, never a fallback to #1. Do not dump leftover session notes.
- Write: whether anything persisted, whether check passed, corresponding change ID, exact next step. Unchanged patches are no-ops; state-only changes still create a ledger entry.
- Trivial done: say nothing was persisted.

## Gotchas

- CURRENT.md is truth. Do not hand-edit `.agent-memory` files; run the bundled scripts.
- Failed structural/argument checks must be resolved before writing. Repair adds missing schema lines locally; it refuses malformed state, unsupported schemas and sync conflicts rather than inventing facts.
- Do not write this skill's own changelog into a project's memory.
