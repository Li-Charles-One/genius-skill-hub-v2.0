---
name: genius-weplaning
metadata:
  version: "3.3.0"
description: "维护 .agent-memory 中的 WePlaning 3.0 项目记忆：读取状态快照、追加变更账本、推进里程碑与执行记忆校验修缮。不要用于普通聊天总结或临时一次性代码修改。"
---

# Genius-WePlaning

Project memory lives in `.agent-memory/`: **CURRENT.md** is accepted truth, **CHANGES.md** the append-only ledger, `DECISIONS.md` optional, `archive/` rolled-off ledger. Leftover 2.3 `THREADS.md` / `sessions/` are history, never truth; never create sessions. `.backups/` and `.weplaning.lock` are device-local: never sync them.

Do not use for ordinary summaries, one-off answers, trivial code edits, or **this skill's own changelog** (skill upgrades never go into a business project's memory).

## Triggers

| User says | Run |
|---|---|
| "查看项目记忆" / "读取项目记忆" | `weplaning-read.cjs` |
| "查看项目进度" / "项目叫什么" / "现在目标是什么" | `weplaning-read.cjs --brief` |
| "读取记忆接力" | `weplaning-read.cjs --handoff`; report the focus, or no pending tasks / unknown |
| "继续干 #N" | `weplaning-read.cjs --next N`; start only after a successful selection |
| "记一笔" / "这件事记下来" / "提交主线" / "close out" | `weplaning-write.cjs` |
| "完成了" / "done" / "搞定" with no new fact | nothing; say nothing was persisted |
| "修一下记忆" | `check-memory.cjs`, then `repair-memory.cjs` if the cause is known |

Write on your own only for **durable, cross-session** facts: accepted state changes, approvals, blockers, verified completion, or a non-obvious decision (`--decision`). Never for routine edits, process chatter or skill maintenance.

## Commands

`<skill_dir>` is this skill's directory. Always pass `--agent <name>`.

```bash
node <skill_dir>/scripts/weplaning-read.cjs <root> [--brief | --handoff | --next N | --full | --find "<q>" | --json]
node <skill_dir>/scripts/weplaning-write.cjs <root> --agent <name> --changed "<fact>" [--verification "<method/time/result>"] [--file <path>]
# Change one fact in place instead of resending a whole section:
node <skill_dir>/scripts/weplaning-write.cjs <root> --agent <name> --replace "<exact old text>" --with "<new text>" --changed "<what happened>"
node <skill_dir>/scripts/weplaning-write.cjs <root> --agent <name> --add-state "<new fact>" --drop "<text unique to the obsolete line>"
node <skill_dir>/scripts/check-memory.cjs <root>
node <skill_dir>/scripts/init-memory.cjs <root> --agent <name> --project "<name>" --goal "<goal>"
```

Full CLI, schema and pitfalls: `references/reference.md`.

## Rules

- Never hand-edit `.agent-memory/`. For one fact use `--replace/--with`, `--add-state` or `--drop`: each must match exactly once or the write fails with nothing changed.
- `--state` / `--next-step` / `--blockers` / `--goal` / `--understanding` replace the whole section: re-read it first and keep every still-valid item.
- `--changed` only appends the ledger and never touches Current State. A CURRENT patch without `--changed` still gets a ledger entry.
- One event, one write: put its patches, `--changed`, `--verification` and `--decision` in a single command instead of several writes.
- Values are one line (`;;` separates items); only `--goal`, `--understanding`, `--replace` and `--with` may span lines. Markdown headings are rejected.
- Every write runs the consistency check; report success only when it passes.
- Accepted Next Steps holds accepted actions: `none` / `无待执行事项` when nothing is pending, `unknown` when undecided; keep conditional triggers. Durable guidance belongs in Current Understanding.
- One fact per item: concrete paths, decisions, verification method/time/result, blockers, exact next step.
- Never store secrets, tokens, passwords, cookies or private credentials.

## Workflow Handoff

Planning states shared with `genius-brief-thinking` and `genius-impl-plans`: `BRIEF_APPROVED`, `PLAN_DRAFT`, `PLAN_APPROVED`, `IMPLEMENTING`, `BLOCKED`, `DONE`. On approvals, implementation start, blockers or verified completion, record `Brief`, `Plan`, `Status` and `Current Task` in the existing Current State / Accepted Next Steps sections. Never create another state file.

## Output

- Read: memory update time, goal, understanding, recorded state, next steps, blockers (including unknown), latest ledger lines. It is recorded state, not a live verification. `--brief` cuts long understanding/state items to their label: run a full read before acting on one. Handoff adds recorded verification/file references; no pending tasks means stop, unknown means clarify, and an invalid task number is an error, never a fallback to #1.
- Write: whether anything persisted, whether the check passed, the change ID, any `[audit]` warning (oversized CURRENT; relay it, do not trim memory unasked), the exact next step. Unchanged patches persist nothing.

## Resource Map

- `scripts/repair-memory.cjs`, `scripts/archive-changes.cjs`, `scripts/weplaning-find.cjs`, `scripts/check-dirty.cjs`: repair, ledger archiving, full-history search, dirty-file check; usage in `references/reference.md`.
- `scripts/weplaning-utils.cjs`: shared helpers for all scripts.
- `evals/evals.json`: trigger and behavior checks.
