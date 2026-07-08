---
name: we-planing
version: 1.5.0
description: "Maintain WePlaning v2.3 project memory. Use for: init, resume, persist, hand off, close out, repair .agent-memory. 读取项目记忆 / 持久化到项目记忆 / 记一笔 / 查看项目进度."
---

# WePlaning
_(Skill package v1.5.0; implements WePlaning protocol v2.3)_

## Use When

- The user asks to initialize, resume, hand off, close out, repair, or verify project memory.
- Multiple Agent sessions need shared durable state in `.agent-memory/`.
- You will write accepted project state, session notes, or a change ledger entry.

Do not use for ordinary summaries, one-off answers, or code-only edits unless the user explicitly wants project memory persisted.

## User-Facing Trigger Phrases (pinned to this skill)

When the user says any of these, **read the project memory** — don't ask "what memory?". The agent that comes back online after a break depends on these phrases being recognized:

| User says | Agent does |
|---|---|
| "读取项目记忆" | Read-only flow (CURRENT → THREADS → tail of CHANGES) |
| "读取 .agent-memory 接力" / "读取记忆接力" | Read-only flow + report the last open Next Step |
| "持久化到项目记忆" / "把这个存进 .agent-memory" | Lite flow (new-session + safe-edit --lite) |
| "这件事记下来" / "记一笔" | Lite flow |
| "完成了 / close out / 提交主线" | Closeout flow (safe-edit --close) |
| "修一下记忆" / "memory 坏了" | `check-memory.cjs` first, then `repair-memory.cjs` if cause is known |
| "项目叫什么" / "现在目标是什么" / "查看项目进度" | Read CURRENT.md "Active Goal" only |
| "继续干 #N" | Read memory → report Next Step N → start work |

## Files

> `<skill_dir>` in all commands below refers to the skill's base directory — shown at the bottom of the loaded skill content as "Base directory for this skill".

```text
.agent-memory/
├── CURRENT.md       current accepted mainline state
├── THREADS.md       session tree and mainline pointer
├── CHANGES.md       append-only durable change ledger
└── sessions/<id>.md one working record per Agent session
```

Optional files such as `TOOLS.md`, `PROJECT.md`, `DECISIONS.md`, and `notes/` may exist, but they are not required for the base consistency gate.

## Proactive Triggers

The Agent should **automatically run Quick Note** (without waiting for the user to ask) in these situations:

| Situation | Action |
|---|---|
| A task phase completes (feature done, bug fixed, config updated) | Run `weplaning-note.cjs` automatically, report session ID |
| User says "完成了" / "done" / "搞定" | Run `weplaning-note.cjs` automatically |
| Multiple files were changed in one session | Run `weplaning-note.cjs` automatically before ending |
| A non-obvious decision was made (library choice, architecture trade-off) | Run `weplaning-note.cjs` automatically to preserve the reasoning |

Do **not** wait for "持久化到项目记忆" — by then the user has already had to remember to ask.

## Quick Note (one command)

For post-task recording, use `weplaning-note.cjs` instead of the two-step Lite flow:

```bash
node <skill_dir>/scripts/weplaning-note.cjs <project-root> "<note>" --agent <agent-name>
```

This does `new-session` + `safe-edit --lite` + consistency check in one call.

```bash
# Example
node <skill_dir>/scripts/weplaning-note.cjs . "genius-vision SKILL.md v1.3.0 optimized: 9 fixes, commit 15e3cf5" --agent ZCode
```

Use `--role` and `--goal` to override defaults (`ops` and the note text respectively).

## Read-Only Flow

**Preferred: one command**

```bash
node <skill_dir>/scripts/weplaning-read.cjs <project-root>
```

Outputs goal + current state + next steps + recent unmerged notes + recent changes in one structured briefing. After running, report the summary to the user.

**Manual (fallback):**

1. Read `.agent-memory/CURRENT.md`.
2. Read `.agent-memory/THREADS.md`.
3. Read the tail of `.agent-memory/CHANGES.md`.
4. Read relevant `sessions/<id>.md` files only when needed.
5. Summarize to the user: Active Goal → current state → next steps → blockers.

Do not create a session for read-only inspection.

## Lite Flow

Use this when the user wants a durable note but not a mainline merge:

```bash
node <skill_dir>/scripts/new-session.cjs <project-root> --agent <agent-name> --role <role> --summary "<summary>" --goal "<goal>"
node <skill_dir>/scripts/safe-edit.cjs <project-root> --lite --session <id> --changed "<durable note>"
```

```bash
# Example
node <skill_dir>/scripts/new-session.cjs . --agent ZCode --role ops --summary "update config" --goal "enable dark mode"
node <skill_dir>/scripts/safe-edit.cjs . --lite --session sess_20260708_001 --changed "Updated tailwind.config.ts: darkMode enabled"
```

## Closeout Flow

Use this when accepted work should become mainline:

```bash
node <skill_dir>/scripts/safe-edit.cjs <project-root> --close --session <id> \
  --changed "<what changed>" --file "<path>" --verification "<check run>"
```

This runs pre-check, appends `CHANGES.md`, merges the session, runs post-check, and restores the snapshot on failure.

**Sync `CURRENT.md` prose in the same call** — if the closeout changes facts the user reads in `CURRENT.md` (state bullets, next steps, blockers, goal), pass the sync flags instead of hand-editing afterwards:

```bash
node <skill_dir>/scripts/safe-edit.cjs <project-root> --close --session <id> \
  --changed "<what changed>" --file "<path>" --verification "<check run>" \
  --state "Feature A done;;Feature B in review" \
  --next-step "Ship feature B;;Start feature C" \
  --blockers "none"
```

`--state`/`--next-step`/`--blockers` replace their whole section (repeat the flag or use `;;` for multiple items); `--goal` and `--understanding` replace their sections as plain text.

## Maintenance

```bash
node <skill_dir>/scripts/init-memory.cjs <project-root> --agent <agent-name> --project "<name>" --goal "<goal>"
node <skill_dir>/scripts/check-memory.cjs <project-root>
node <skill_dir>/scripts/check-memory.cjs <project-root> --audit
node <skill_dir>/scripts/repair-memory.cjs <project-root>
```

## Verification

> _Run this checklist when setting up WePlaning on a new machine, after recovery, or before shipping a new skill version._

- [ ] Smoke test passes: `node <skill_dir>/tools/smoke-weplaning.cjs` prints all `[ok]` and exits 0
- [ ] `init-memory.cjs` completes without error (run with `--agent <name>`)
- [ ] `check-memory.cjs` passes on a freshly initialized project
- [ ] Lite flow: `new-session.cjs` + `safe-edit --lite` completes and `check-memory.cjs` still passes
- [ ] Closeout flow: `safe-edit --close` completes, session appears as `merged` in `THREADS.md`

## Agent Name

Scripts default the agent name to `$WEPLANING_AGENT` (or `Agent` if unset). Set `WEPLANING_AGENT=<persona>` once in the environment, or pass `--agent <persona>` explicitly on `init-memory.cjs`, `new-session.cjs`, `weplaning-note.cjs`, and `safe-edit.cjs`.

## Rules

- After writing `.agent-memory/`, run `check-memory.cjs` and do not report success until it passes.
- Do not store secrets, tokens, passwords, cookies, or private credentials.
- Keep memory concise: facts, decisions, files, verification, blockers, and exact next step.
- If check fails: stop, inspect the error, repair or correct the files, then rerun check.
- For exact schema details, read `references/weplaning-v2.3-protocol.md`.

**Project type and sync strategy** (项目类型与同步策略):
- On init, scan for code files (`.js/.py/.ts/.go` etc.) and ask the user about project purpose to determine project type.
- **Has code** → use git for code versioning; WePlaning manages project state only.
- **No code (ops/doc)** → WePlaning works standalone; sync is handled by external tools (Syncthing etc.).
- If code files appear mid-project → introduce git at that point.
- WePlaning's scope is `.agent-memory/` state only; sync tool choice and config are outside its responsibility.
- Record project type and sync config in `CURRENT.md` under `Project Config` for handoff continuity.

## Pitfalls

**1. Don't init memory before the smoke test passes.**
A broken init cascade is harder to recover from than a smoke-test failure caught up front.

**2. Don't run `closeout` for "just a quick note"** — use Quick Note (`weplaning-note.cjs`) or the Lite flow.
The Closeout flow appends `CHANGES.md` and merges the session; running it for transient state pollutes the mainline ledger.

**3. Junction pitfalls (dangling links, live-mirror git propagation).**
See `references/hermes-install.md`.

**4. Cross-platform paths in scripts.**
The skill scripts use forward slashes; on Windows they work via Node's path normalization. Don't edit them to use `\\` — they'll break on Linux/macOS usage.

**5. When `clarify` offers options, every option's stated consequence must be true.**
Before offering choices on a destructive command, verify the consequence against the actual environment — junction semantics, process locks, schema invariants. If you cannot verify, say so in the option text ("I'm not sure if X is safe — verify before choosing") instead of writing a confident wrong description.

**6. `safe-edit.cjs --close` requires the session's `Parent session:` to equal `THREADS.md` mainline.**
Otherwise it fails with "Stale write blocked" — the error message includes the fix (close the active predecessor first, or repoint `Parent session:` at the true mainline). Lock cleanup on failure is automatic; if a lock ever lingers after a crash, remove `<project>/.agent-memory/.weplaning.lock`.

**7. Always sync `CURRENT.md` on closeout.**
If the closeout changes any facts in `CURRENT.md` (state, next steps, blockers, goal) and you skip the `--state`/`--next-step`/`--blockers`/`--goal` sync flags, the mainline becomes stale. The next session's Read-Only flow will report that stale state as truth.

## Hub / Hermes Installation

For shipping WePlaning from a hub repo, read `references/hermes-install.md` (covers smoke-test-first, category choice, junction linking, and junction pitfalls).
