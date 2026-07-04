---
name: we-planing
version: 1.2.0
description: "Maintain lightweight WePlaning v2.3 project memory. Triggers: initialize project memory, persist session, resume project, hand off, close out, repair memory, verify .agent-memory state, 读取项目记忆, 持久化到项目记忆, 记一笔, 查看项目进度. Do not use for ordinary summaries or code-only edits unless project memory must be updated."
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

## Proactive Triggers

The Agent should **proactively offer** to record memory (without waiting for the user to ask) in these situations:

| Situation | Action |
|---|---|
| A task phase completes (feature done, bug fixed, config updated) | Run Quick Note, report session ID |
| User says "完成了" / "done" / "搞定" | Run Quick Note automatically |
| Multiple files were changed in one session | Suggest Quick Note before ending |
| A non-obvious decision was made (library choice, architecture trade-off) | Run Quick Note to preserve the reasoning |

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



1. Read `.agent-memory/CURRENT.md`.
2. Read `.agent-memory/THREADS.md`.
3. Read the tail of `.agent-memory/CHANGES.md`.
4. Read relevant `sessions/<id>.md` files only when needed.

Do not create a session for read-only inspection.

## Lite Flow

Use this when the user wants a durable note but not a mainline merge:

```bash
node <skill_dir>/scripts/new-session.cjs <project-root> --agent <agent-name> --role <role> --summary "<summary>" --goal "<goal>"
node <skill_dir>/scripts/safe-edit.cjs <project-root> --lite --session <id> --changed "<durable note>"
```

## Closeout Flow

Use this when accepted work should become mainline:

```bash
node <skill_dir>/scripts/safe-edit.cjs <project-root> --close --session <id> \
  --changed "<what changed>" --file "<path>" --verification "<check run>"
```

This runs pre-check, appends `CHANGES.md`, merges the session, runs post-check, and restores the snapshot on failure.

## Maintenance

```bash
node <skill_dir>/scripts/init-memory.cjs <project-root> --agent <agent-name> --project "<name>" --goal "<goal>"
node <skill_dir>/scripts/check-memory.cjs <project-root>
node <skill_dir>/scripts/check-memory.cjs <project-root> --audit
node <skill_dir>/scripts/repair-memory.cjs <project-root>
```

## Verification

- [ ] Smoke test passes: `node <skill_dir>/tools/smoke-weplaning.cjs` prints all `[ok]` and exits 0
- [ ] `init-memory.cjs` completes without error (run with `--agent <name>`)
- [ ] `check-memory.cjs` passes on a freshly initialized project
- [ ] Lite flow: `new-session.cjs` + `safe-edit --lite` completes and `check-memory.cjs` still passes
- [ ] Closeout flow: `safe-edit --close` completes, session appears as `merged` in `THREADS.md`

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

**1. Don't init memory before the smoke test passes.**
A broken init cascade is harder to recover from than a smoke-test failure caught up front.

**2. Don't run `closeout` for "just a quick note"** — use the Lite flow.
The Closeout flow rewrites `CHANGES.md` and merges the session; running it for transient state pollutes the mainline ledger.

**3. Junction target disappears → broken link.**
If the hub repo is moved or deleted, the junction in `hermes/skills/` becomes a dangling empty directory. Hermes won't auto-clean it. If you delete the hub, `rmdir` the junction on the Hermes side too.

**4. Junction is a live mirror — git operations on the hub affect Hermes instantly.**
A Windows directory junction (`mklink /J`) is a filesystem-level mirror, not a snapshot. Any operation that rewrites files inside the hub repo's working tree — `git checkout -- <file>`, `git stash`, `git reset --hard`, `git restore`, even `git pull` with conflicts — propagates to `hermes/skills/<category>/<skill>` **immediately**, with no reload and no warning. To archive hub working-tree edits without losing them from the live install, **commit** them (local or remote) — not stash.

**5. Cross-platform paths in scripts.**
The skill scripts use forward slashes; on Windows they work via Node's path normalization. Don't edit them to use `\\` — they'll break on Linux/macOS usage.

**6. When `clarify` offers options, every option's stated consequence must be true.**
Before offering choices on a destructive command, verify the consequence against the actual environment — junction semantics, process locks, schema invariants. If you cannot verify, say so in the option text ("I'm not sure if X is safe — verify before choosing") instead of writing a confident wrong description.

**7. `safe-edit.cjs` business errors can leak the `.weplaning.lock` directory.**
`withMemoryLock` takes the lock via `fs.mkdirSync` but errors thrown *before* the callback (e.g. "Stale write blocked") abort without releasing it. Recovery: `rm -rf <project>/.agent-memory/.weplaning.lock`. Prevention: set `WEPLANING_LOCK_STALE_MS=1000` if you anticipate a stale-write check failing.

**8. `safe-edit.cjs --close` requires the session's `Parent session:` to equal `THREADS.md` mainline.**
`ensureFreshMainline` throws "Stale write blocked" if `parent !== threads.mainline`. Fix: close the active predecessor first, or manually edit `sessions/<id>.md` to point `Parent session:` at the true mainline before running `--close`.
