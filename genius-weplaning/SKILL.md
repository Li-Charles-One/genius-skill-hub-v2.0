---
name: genius-weplaning
metadata:
  version: "3.7.0"
description: "维护项目 .agent-memory 里的 WePlaning 项目记忆：跨会话的已确认状态、下一步、变更账本与决策。用户说「查看项目记忆」「查看项目进度」「读取记忆接力」「继续干 #N」「记一笔」「这件事记下来」「提交主线」「记个决策」「修一下记忆」「初始化项目记忆」时使用。不要用于普通聊天总结或一次性小改动；个人笔记和想法走 flomo；不记 Agent 自身的偏好，也不记本 skill 的升级。"
---

# Genius-WePlaning

Project memory lives in `.agent-memory/`: **CURRENT.md** is accepted truth, **CHANGES.md** the append-only ledger, `DECISIONS.md` optional, `archive/` rolled-off ledger. `.backups/` and `.weplaning.lock` are device-local: never sync them.

## Triggers

| User says | Run |
|---|---|
| "查看项目记忆" / "读取记忆接力" | `weplaning-read.cjs`; report the focus step, or no pending tasks / unknown |
| "查看完整的项目记忆" | `weplaning-read.cjs --full` (adds recorded verification, files, active decisions, archive list) |
| "查看项目进度" / "现在目标是什么" | `weplaning-read.cjs --brief` |
| "继续干 #N" | `weplaning-read.cjs --next N`; start only after a successful selection |
| "记一笔" / "这件事记下来" / "提交主线" / "记个决策" | `weplaning-write.cjs` |
| "完成了" / "done" / "搞定" with no new fact | nothing; say nothing was persisted |
| "修一下记忆" | `check-memory.cjs`, then `repair-memory.cjs` if the cause is known |
| "初始化项目记忆" | `init-memory.cjs`, only when the user asks; a read that finds no memory reports that and stops |

## What to record

Only durable, cross-session project facts: accepted state changes, approvals, blockers, verified completion, non-obvious decisions (`--decision`). For each fact ask "would someone maintaining this a year from now need it?" Yes → the skill, doc or code that owns that area; CURRENT gets a pointer, never a copy. No, it only says what happened (a change, a measurement, a verification) → the ledger via `--changed` / `--verification`. CURRENT is the project's index: goal, routing (which skill or doc owns what), cross-cutting rules and facts with no other home; when a fact moves to its owner, drop it from CURRENT.

Never record routine edits, process chatter, personal notes or ideas (flomo), the agent's own preferences, this skill's upgrades, or secrets (tokens, passwords, cookies, credentials).

## Commands

`<skill_dir>` is this skill's directory. `<root>` is any directory inside the project: scripts use the nearest `.agent-memory` at or above it (init creates it in `<root>` itself). Write and init require `--agent <name>`, your runtime: `claude-code`, `codex`, `opencode`, `grok`, `cursor`, `zcode` or `hermes`; anything else is rejected.

```bash
node <skill_dir>/scripts/weplaning-read.cjs <root> [--brief | --next N | --full | --find "<q>" | --json]
# One event, one write: the ledger line plus whichever patches, evidence and decision belong to it
node <skill_dir>/scripts/weplaning-write.cjs <root> --agent <name> --changed "<what happened>" \
  [--replace "<exact old text>" --with "<new text>"] [--add-state "<fact>"] [--add-next "<step>"] \
  [--drop "<text unique to the obsolete line>"] [--verification "<method/time/result>"] [--file <path>] \
  [--decision "<decision>" --rationale "<why>" --supersedes "<text unique to the old decision>"]
node <skill_dir>/scripts/check-memory.cjs <root>
node <skill_dir>/scripts/init-memory.cjs <root> --agent <name> --project "<name>" --goal "<goal>"
```

## Rules

- Read memory only through `weplaning-read.cjs`, never `cat` the files: the script checks structure and Syncthing `*.sync-conflict-*` copies first.
- Never hand-edit `.agent-memory/`. Patch one fact with `--replace/--with`, `--add-state`, `--add-next` or `--drop`.
- `--next-step` / `--blockers` / `--goal` / `--understanding` replace the whole section: re-read it first and keep every still-valid item.
- Every CURRENT patch needs `--changed` saying what happened in one line; `--changed` alone only appends the ledger.
- One fact per item, one line each (`;;` separates items). A new item over 300 characters is rejected: detail goes to the doc that owns it.
- Accepted Next Steps: `none` when nothing is pending, `unknown` when undecided; keep conditional triggers. Start a step only the user can do with `【待用户…】` or `[user]`; the focus skips it. Durable guidance belongs in Current Understanding.

## Output

- Read is recorded state, not a live verification. Obey the script's stop lines (no pending tasks, unknown, waiting on the user, invalid task number, sync conflict): never invent a task, fall back to #1 or write while copies conflict. `--brief` cuts long items to their label: run a full read before acting on one.
- Write: say whether anything persisted, the change ID and the exact next step. Relay any `[audit]` warning; do not trim memory unasked.

## Gotchas

`references/reference.md` § Pitfalls: `--reinit` destroys history; `--next-step` and `--blockers` replace a section instead of merging; sync-conflict copies block every write until resolved.

## Resource Map

- `references/reference.md`: full CLI, file schema and pitfalls.
- `scripts/repair-memory.cjs`, `scripts/archive-changes.cjs`, `scripts/weplaning-find.cjs`: repair, ledger archiving, full-history search.
- `scripts/weplaning-utils.cjs`: shared helpers for all scripts.
- `evals/evals.json`: trigger and behavior checks.
