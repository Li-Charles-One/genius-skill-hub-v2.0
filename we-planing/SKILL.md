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
| "项目叫什么" / "现在目标是什么" | Read CURRENT.md "Active Goal" only |

For multi-step "继续干 #N" prompts, read memory, report Next Step N, then start work — don't ask the user to re-explain the goal.

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

Core closeout uses `scripts/append-change.cjs` and `scripts/merge-session.cjs`; shared helpers live in `scripts/weplaning-utils.cjs`.

Use `repair-memory.cjs` only after `check-memory.cjs` fails and the cause is understood.

## Installing WePlaning into Hermes (when shipping from a hub repo)

If WePlaning lives in a separate repo (e.g. `genius-skill-hub-v2.0/`) and you want to make it available to Hermes:

1. **Smoke-test first** — run `node <hub>/we-planing/tools/smoke-weplaning.cjs` from the hub path. If it doesn't print all `[ok]` lines and exit 0, don't install.
2. **Pick the right category** in `hermes/skills/`. There's no `project-management` category by default in some Hermes installs — `mkdir -p` it if missing. `software-development` is a wrong fit (WePlaning is about project memory, not code).
3. **Link, don't copy** — use a Windows directory junction (`mklink /J`, no admin needed) so changes in the hub flow to Hermes automatically:
   ```bash
   cmd //c "mklink /J C:\Users\<user>\AppData\Local\hermes\skills\project-management\we-planing <hub>\we-planing"
   ```
   `mklink /D` (symbolic link) requires admin or Developer Mode — junction is the right tool for standard users.
4. **Default agent name** — `init-memory.cjs` defaults to agent name `Codex`. Pass `--agent <name>` (e.g. `Linus`) on first init to match the active persona. Subsequent calls in the same project can rely on the existing THREADS.md entries.
   - **Same trap on `new-session.cjs`** — it also defaults to `Codex`. The Installing section above only mentions `init-memory.cjs`; the trap repeats for every session you open with `new-session.cjs`. Habit: always pass `--agent Linus` (or whatever your persona is) on every `new-session.cjs` call, not just the first `init-memory.cjs` call.
5. **`safe-edit.cjs --close` does not sync `CURRENT.md`** — closeout appends `CHANGES.md`, merges the session into `THREADS.md`, and runs `check-memory.cjs`, but it does **not** rewrite the prose in `CURRENT.md` to reflect the new accepted state. After any closeout that changes facts the user reads in `CURRENT.md` (matrix size, "Agent 矩阵 (N 个)" counts, status of Next Steps, items that should move from "active" to "done"), manually `read_file` `CURRENT.md`, patch the affected lines, then re-run `check-memory.cjs`. Skipping this leaves a stale mainline (e.g. CURRENT.md still saying "4 个" agents after you uninstalled the 4th) and the next session's Read-Only flow will hand the user a wrong summary.

## Rules

- After writing `.agent-memory/`, run `check-memory.cjs` and do not report success until it passes.
- Do not store secrets, tokens, passwords, cookies, or private credentials.
- Keep memory concise: facts, decisions, files, verification, blockers, and exact next step.
- If check fails: stop, inspect the error, repair or correct the files, then rerun check.
- For exact schema details, read `references/weplaning-v2.3-protocol.md`.
- **项目类型与同步策略**：
  - 初始化时判断项目类型：扫描目录是否有代码文件（.js/.py/.ts/.go 等），询问用户项目用途，综合判断
  - **有代码** → 必须 git 管理代码版本，WePlaning 管项目状态，git 管代码
  - **无代码（ops/doc）** → WePlaning 独立工作，同步交给外部工具（Syncthing 等）
  - 过程中出现代码文件 → 引入 git
  - 多端多地同步工具（Syncthing、坚果云、网盘等）的选择和配置不是 WePlaning 的职责，WePlaning 只管 `.agent-memory/` 状态
  - 将项目类型和同步配置记录到 `CURRENT.md` 的 `Project Config` 部分，方便后续 Agent 接力时读取

## Pitfalls

- **Don't init memory before the smoke test passes.** A broken init cascade is harder to recover from than a smoke-test failure caught up front.
- **Don't run `closeout` for "just a quick note"** — use the Lite flow. The Closeout flow rewrites `CHANGES.md` and merges the session; running it for transient state pollutes the mainline ledger.
- **Junction target disappears → broken link.** If the hub repo is moved or deleted, the junction in `hermes/skills/` becomes a dangling empty directory. Hermes won't auto-clean it. If you delete the hub, `rmdir` the junction on the Hermes side too.
- **Junction is a live mirror — git operations on the hub affect Hermes instantly.** A Windows directory junction (`mklink /J`) is a filesystem-level mirror, not a snapshot. Any operation that rewrites files inside the hub repo's working tree — `git checkout -- <file>`, `git stash`, `git reset --hard`, `git restore`, even `git pull` with conflicts — propagates to `hermes/skills/<category>/<skill>` **immediately**, with no reload and no warning. If the hub has uncommitted skill edits (e.g. expanded `SKILL.md`), they vanish from Hermes the moment those commands run. Don't recommend `git stash` or `git checkout --` as a "clean up the working tree" move when the junction target contains skill files the live Hermes install depends on. To archive hub working-tree edits without losing them from the live install, **commit** them (local or remote) — not stash.
- **Cross-platform paths in scripts.** The skill scripts use forward slashes; on Windows they work via Node's path normalization. Don't edit them to use `\\` — they'll break on Linux/macOS usage.
- **When `clarify` offers options, every option's stated consequence must be true.** This is the meta-lesson behind the "Junction is live mirror" pitfall: a tempting "non-destructive" path (e.g. `git stash` on a hub repo whose `skills/` is junctioned into Hermes) turns destructive the moment the junction is live. Before offering choices on a destructive command, run the consequence in your head against the actual environment — junction semantics, process locks, schema invariants — not just the obvious git/filesystem semantics. If you cannot verify the consequence, say so in the option text ("I'm not sure if X is safe — verify before choosing") instead of writing a confident wrong description. Users pick options that look clean; a wrong "clean" option will be picked and you'll have to walk it back.
- **`safe-edit.cjs` business errors can leak the `.weplaning.lock` directory.** `withMemoryLock` (in `scripts/weplaning-utils.cjs`) takes the lock via `fs.mkdirSync` inside a `while(true)` loop, then runs the callback inside a `try/finally` that removes the lock. However, errors thrown **before** the callback (e.g. `ensureFreshMainline`'s "Stale write blocked" or "Mainline mismatch" thrown during the `readThreads` / `readMemory` step) abort inside the `while` loop, never entering the `try/finally`, so the lock directory is left on disk. The next `safe-edit` call then times out after 30s reporting "Timed out waiting for WePlaning lock held by pid <N>" against a PID that is already dead. Recovery: `rm -rf <project>/.agent-memory/.weplaning.lock`. Prevention: if you anticipate a stale-write check failing (e.g. you just changed a session's `Parent session:` field by hand and now want to close it), set `WEPLANING_LOCK_STALE_MS=1000` so the next run auto-clears any leaked lock after 1s. The script's own 120s default `staleMs` is for live-but-slow writers, not for leaked locks.
- **`safe-edit.cjs --close` requires the session's `Parent session:` to equal `THREADS.md` mainline.** `ensureFreshMainline` throws "Stale write blocked" if `parent !== threads.mainline && sessionId !== threads.mainline`. `new-session.cjs` defaults `--parent` to the **current** `THREADS.md` mainline at the time of session creation — if the previous session is still marked `active` (even when it was effectively a no-op read-only handoff), the new session inherits the active parent and `safe-edit --close` then blocks. Fix: either close the active predecessor first (recommended — it makes the tree honest), or manually edit `sessions/<id>.md` to point `Parent session:` at the true mainline before running `--close`. Choosing the wrong parent because it "looks right" is the common failure mode.
