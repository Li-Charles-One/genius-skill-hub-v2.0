---
name: we-planing
version: 1.8.0
description: "Maintain WePlaning v2.3 project memory. Use for: init, resume, persist, hand off, close out, repair .agent-memory. 读取项目记忆 / 持久化到项目记忆 / 记一笔 / 查看项目进度."
---

# WePlaning
_(Skill package v1.8.0; implements WePlaning protocol v2.3)_

## Use When

- The user asks to initialize, resume, hand off, close out, repair, or verify project memory.
- Multiple Agent sessions need shared durable state in `.agent-memory/`.
- You will write accepted project state, session notes, or a change ledger entry.

Do not use for ordinary summaries, one-off answers, or trivial code-only edits unless the user explicitly wants project memory persisted. (The Proactive Triggers below are the deliberate exception — they fire only for durable, cross-session-relevant work, not routine Q&A or cosmetic one-off edits.)

## User-Facing Trigger Phrases (pinned to this skill)

When the user says any of these, **read the project memory** — don't ask "what memory?". The agent that comes back online after a break depends on these phrases being recognized:

| User says | Agent does |
|---|---|
| "读取项目记忆" | `weplaning-read.cjs` (or CURRENT → THREADS → recent CHANGES) |
| "读取 .agent-memory 接力" / "读取记忆接力" | `weplaning-read.cjs --handoff` (+ report Focus Next Step #1) |
| "持久化到项目记忆" / "把这个存进 .agent-memory" | Lite flow (new-session + safe-edit --lite) |
| "这件事记下来" / "记一笔" | Lite flow |
| "完成了 / close out / 提交主线" | Closeout flow (safe-edit --close) |
| "修一下记忆" / "memory 坏了" | `check-memory.cjs` first, then `repair-memory.cjs` if cause is known |
| "项目叫什么" / "现在目标是什么" / "查看项目进度" | Read CURRENT.md "Active Goal" only |
| "继续干 #N" | `weplaning-read.cjs --next N` → report Focus Next Step #N → start work |

## Files

> `<skill_dir>` in all commands below refers to the skill's base directory — shown at the bottom of the loaded skill content as "Base directory for this skill".

```text
.agent-memory/
├── CURRENT.md       current accepted mainline state (+ Project Config)
├── THREADS.md       session tree and mainline pointer
├── CHANGES.md       append-only durable change ledger
├── DECISIONS.md     optional decision ledger (created on init)
├── archive/         rolled-off CHANGES blocks
└── sessions/<id>.md one working record per Agent session
```

`.backups/` and `.weplaning.lock` also appear under `.agent-memory/`. Both are device-local scratch, not project state: never sync them and never treat them as recoverable history.

Optional files such as `TOOLS.md`, `PROJECT.md`, and `notes/` may exist, but they are not required for the base consistency gate.

## Proactive Triggers

The Agent should **automatically run Quick Note** (without waiting for the user to ask) in these situations:

| Situation | Action |
|---|---|
| A task phase completes (feature done, bug fixed, config updated) | Run `weplaning-note.cjs` automatically, report session ID |
| User says "完成了" / "done" / "搞定" | Run `weplaning-note.cjs` automatically |
| Multiple files were changed for durable, cross-session-relevant work (not routine one-off edits) | Run `weplaning-note.cjs` automatically before ending |
| A non-obvious decision was made (library choice, architecture trade-off) | Run `weplaning-note.cjs` automatically to preserve the reasoning |

Do **not** wait for "持久化到项目记忆" — by then the user has already had to remember to ask.

## Quick Note (one command)

For post-task recording, use `weplaning-note.cjs` instead of the two-step Lite flow:

```bash
node <skill_dir>/scripts/weplaning-note.cjs <project-root> "<note>" --agent <agent-name>
```

This runs `new-session` + `safe-edit --lite` + consistency check, then **auto-closes** the session (status `closed`) so Lite notes don't accumulate as `active`.

```bash
# Example
node <skill_dir>/scripts/weplaning-note.cjs . "genius-vision SKILL.md v1.3.0 optimized: 9 fixes, commit 15e3cf5" --agent ZCode
```

Use `--role` and `--goal` to override defaults (`ops` and the note text respectively). Pass `--decision` / `--rationale` to also append `DECISIONS.md`.

## Read-Only Flow

**Preferred: one command**

```bash
node <skill_dir>/scripts/weplaning-read.cjs <project-root>
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --handoff
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --brief    # goal/state/next/blockers only
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --next 1
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --all      # also list abandoned sessions
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --json
```

To answer "when did we decide X" or "when was Y retired", search instead of scrolling — this is the only reader that also covers `archive/`:

```bash
node <skill_dir>/scripts/weplaning-find.cjs <project-root> "<query>" [--regex] [--case] [--scope changes|sessions|archive|...] [--json]
```

Outputs goal + mainline state + next steps + closed notes + active sessions + complete recent change blocks. Truth order: **mainline CURRENT > closed notes > active sessions**. When older history has been rolled into `archive/`, the briefing lists those files so it can still be found.

Do not create a session for read-only inspection.

## Lite / Update Flow

Durable note without mainline merge:

```bash
node <skill_dir>/scripts/new-session.cjs <project-root> --agent <agent-name> --role <role> --summary "<summary>" --goal "<goal>"
node <skill_dir>/scripts/safe-edit.cjs <project-root> --lite --session <id> --changed "<durable note>"
```

Mid-session field updates (active/closed only; refuses merged):

```bash
node <skill_dir>/scripts/safe-edit.cjs <project-root> --update --session <id> \
  --result "<progress>" --next-step "<exact next>" --file "<path>" --decision "<decision>" --note "<work note>"
```

```bash
# Example
node <skill_dir>/scripts/new-session.cjs . --agent ZCode --role ops --summary "update config" --goal "enable dark mode"
node <skill_dir>/scripts/safe-edit.cjs . --update --session 20260708T1430-zcode-a3f9 \
  --result "darkMode wired" --file "tailwind.config.ts" --next-step "close out after review"
```

## Closeout Flow

Use this when accepted work should become mainline:

```bash
node <skill_dir>/scripts/safe-edit.cjs <project-root> --close --session <id> \
  --changed "<what changed>" --file "<path>" --verification "<check run>"
```

This runs pre-check, writes session `Result`/`Files Touched` from close args, appends `CHANGES.md`, merges the session, syncs `CURRENT.md` prose, runs post-check, and restores the snapshot on failure.

**Session fields on close:** `--changed` → session `Result` and (unless `--no-sync`) `CURRENT.md` Current State; `--file` → session Files Touched; `--next-step` → session Exact Next Step and CURRENT Accepted Next Steps.

**Sync `CURRENT.md` prose in the same call** — preferred when you know the full mainline state:

```bash
node <skill_dir>/scripts/safe-edit.cjs <project-root> --close --session <id> \
  --changed "<what changed>" --file "<path>" --verification "<check run>" \
  --state "Feature A done;;Feature B in review" \
  --next-step "Ship feature B;;Start feature C" \
  --blockers "none"
```

`--state`/`--next-step`/`--blockers` replace their whole section (repeat the flag or use `;;` for multiple items); `--goal` and `--understanding` replace their sections as plain text. Use `--no-sync` only when you intentionally keep CURRENT prose unchanged.

**Curated state is protected.** When `CURRENT.md` Current State holds 2 or more curated bullets, a close without `--state` is refused before anything is written, because the auto-sync would replace the whole section with the `--changed` text. Pick one: `--state "<full accepted state>"` (preferred), `--no-sync` to leave the prose alone, or `--replace-state` to accept the overwrite.

**CLI output:** primary results (session id / success) are the last stdout line. Pass `--json` on `init-memory`, `new-session`, `safe-edit`, `weplaning-note`, and `repair-memory` for machine-readable output. Consistency check chatter goes to stderr.

## Maintenance

```bash
node <skill_dir>/scripts/init-memory.cjs <project-root> --agent <agent-name> --project "<name>" --goal "<goal>"
# optional overrides: --type code|ops-doc --code-vcs git --sync "<note>"
# on an existing .agent-memory: --force fills in only missing files; --reinit destroys and rebuilds
node <skill_dir>/scripts/check-memory.cjs <project-root>
node <skill_dir>/scripts/check-memory.cjs <project-root> --audit
node <skill_dir>/scripts/check-memory.cjs <project-root> --audit --strict
node <skill_dir>/scripts/check-dirty.cjs <project-root> [--strict] [--json]
node <skill_dir>/scripts/session-status.cjs <project-root> --session <id> --pause|--resume|--abandon [--reason "<text>"]
node <skill_dir>/scripts/append-decision.cjs <project-root> --decision "<text>" [--rationale "<why>"] [--session <id>]
node <skill_dir>/scripts/archive-changes.cjs <project-root> [--keep 30] [--dry-run]
node <skill_dir>/scripts/archive-threads.cjs <project-root> [--keep 40] [--dry-run]
node <skill_dir>/scripts/repair-memory.cjs <project-root>
# mainline mismatch only:
node <skill_dir>/scripts/repair-memory.cjs <project-root> --prefer current
node <skill_dir>/scripts/repair-memory.cjs <project-root> --prefer threads
```

`check-memory` hard-fails on structure errors (mainline mismatch, missing session files, unknown parents, conflict markers, and file-sync conflict copies). `--audit` adds warnings (orphans, placeholders); warnings exit 0 unless `--strict`.

`archive-threads` bounds `THREADS.md`: it moves finished rows and their session files into `archive/`, never touching the mainline or anything active/paused. Archived ids stay valid as parents because `check-memory` also reads `archive/THREADS-*.md`.

`check-dirty` reports changed paths outside `.agent-memory` (handoff reminder) — via git when the project is a repo, otherwise by comparing mtimes against `CURRENT.md` `Last updated`, so ops-doc projects get the reminder too. `archive-changes` rolls old ledger blocks into `.agent-memory/archive/`, records an `Archived:` breadcrumb in `CHANGES.md`, and refuses to rewrite a `CHANGES.md` with no schema header.

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
- `THREADS.md` summaries are table cells: a literal `|` is normalized to `/` on write. Hand-edited rows keep their text, but do not rely on pipes surviving verbatim.
- If check fails: stop, inspect the error, repair or correct the files, then rerun check.
- For exact schema details, read `references/weplaning-v2.3-protocol.md`.

**Project type and sync strategy** (项目类型与同步策略):
- `init-memory` auto-detects code files and writes `CURRENT.md` → `Project Config` (`Type`, `Code VCS`, `Sync`). Override with `--type` / `--code-vcs` / `--sync` when needed.
- **Has code** → use git for code versioning; WePlaning manages project state only.
- **No code (ops/doc)** → WePlaning works standalone; sync is handled by external tools (Syncthing etc.).
- If code files appear mid-project → introduce git at that point; update Project Config on a closeout or hand edit.
- WePlaning's scope is `.agent-memory/` state only; sync tool choice and config are outside its responsibility.
- Before handoff, run `check-dirty.cjs` when the project is a git repo.

## Pitfalls

**1. Don't init memory before the smoke test passes.**
A broken init cascade is harder to recover from than a smoke-test failure caught up front.

**2. Don't run `closeout` for "just a quick note"** — use Quick Note (`weplaning-note.cjs`) or the Lite flow.
The Closeout flow appends `CHANGES.md` and merges the session; running it for transient state pollutes the mainline ledger.

**3. Junction pitfalls (dangling links, live-mirror git propagation, copies that write through).**
The installed skill path is often a junction to a hub repo, so "isolated copies" made with `fs.cpSync` without `dereference: true` are still the hub. See `references/hermes-install.md`.

**4. Cross-platform paths in scripts.**
The skill scripts use forward slashes; on Windows they work via Node's path normalization. Don't edit them to use `\\` — they'll break on Linux/macOS usage.

**5. When `clarify` offers options, every option's stated consequence must be true.**
Before offering choices on a destructive command, verify the consequence against the actual environment — junction semantics, process locks, schema invariants. If you cannot verify, say so in the option text ("I'm not sure if X is safe — verify before choosing") instead of writing a confident wrong description.

**6. `safe-edit.cjs --close` requires the session's `Parent session:` to equal `THREADS.md` mainline.**
Otherwise it fails with "Stale write blocked" — the error message includes the fix (close the active predecessor first, or repoint `Parent session:` at the true mainline). Lock cleanup on failure is automatic; if a lock ever lingers after a crash, remove `<project>/.agent-memory/.weplaning.lock`.

**7. Prefer explicit `CURRENT.md` sync flags on closeout.**
Without `--no-sync`, close auto-sets Current State from `--changed`, so a one-line change description would become the entire accepted state. Closes that would discard 2 or more curated bullets are now refused up front, but the guard only protects Current State — still pass `--next-step`/`--blockers`/`--goal` when the full mainline prose should change, otherwise next sessions inherit stale next-steps and blockers.

**9. Running memory inside a file-sync folder (Syncthing, Dropbox, iCloud).**
Two devices writing `.agent-memory` concurrently produce sync conflict copies; the lock is process-local and cannot prevent this. `check-memory.cjs` hard-fails when it finds `*.sync-conflict-*` copies so the fork cannot go unnoticed — merge anything worth keeping, then delete the copies. Exclude `.backups/` and `.weplaning.lock` from the sync rules: both are device-local churn and syncing the lock can make one machine look permanently busy to another.

**10. `init-memory --reinit` is a total wipe, `--force` is not.**
`--force` only creates files that are missing and adopts the surviving mainline, so it is safe on a live project. `--reinit` rebuilds `CURRENT.md`, `THREADS.md`, `CHANGES.md` and `DECISIONS.md` from scratch and prints how many session rows and change blocks it is discarding. Never reach for `--reinit` to "fix" a failing check — run `check-memory` and `repair-memory` first.

**8. `repair-memory.cjs` will not guess on mainline mismatch.**
If CURRENT and THREADS disagree, it exits until you pass `--prefer current` or `--prefer threads`. Do not use repair as a silent authority rewrite.

## Hub / Hermes Installation

For shipping WePlaning from a hub repo, read `references/hermes-install.md` (covers smoke-test-first, category choice, junction linking, and junction pitfalls).
