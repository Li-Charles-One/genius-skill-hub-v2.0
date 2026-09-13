# WePlaning CLI

`<skill_dir>` is the skill directory. Primary results are the last stdout line. Pass `--json` on `init-memory`, `weplaning-write`, and `repair-memory`. Consistency check chatter goes to stderr.

Always pass `--agent <persona>` unless `$WEPLANING_AGENT` is set.

Public commands: **read / write / check / init**.

## Read

```bash
node <skill_dir>/scripts/weplaning-read.cjs <project-root>
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --handoff
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --brief
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --next 1
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --full
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --find "<query>"
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --json
node <skill_dir>/scripts/weplaning-find.cjs <project-root> "<query>" [--regex] [--case] [--scope current|changes|decisions|archive] [--json]
```

Default read is memory update time / goal / understanding / recorded state / next / last 3 ledger blocks. `--brief` omits the ledger. `--handoff` includes recorded verification and file references. `--full` also lists leftover 2.3 sessions and archive files.

Reads check structural validity first. `generatedAt` is the read time; JSON `lastUpdated` is the memory update time, not a live verification. Recent change JSON includes `verification` and `files`.

`--next N` requires a positive integer that selects an existing actionable item; invalid input never falls back to #1. Use `none` / `无待执行事项` for no pending tasks, or `unknown` for undecided next steps. JSON exposes `nextStepsStatus` (`ready`, `none`, `unknown`); handoff does not focus a none/unknown placeholder. Unknown blockers remain visible.

Search visits CURRENT before CHANGES, DECISIONS and archived/legacy history, so the default result limit cannot crowd out current truth.

## Write

```bash
node <skill_dir>/scripts/weplaning-write.cjs <project-root> --agent <name> --changed "<fact>"
node "<skill_dir>/scripts/weplaning-write.cjs" "<project-root>" --agent "<name>" --changed "<fact>" --state "Fact A;;Fact B" --next-step "Do C" --blockers "none"
```

`--changed` (or a positional note) appends `CHANGES.md` and bumps `Last updated`. It does not replace Current State.

`--state` / `--next-step` / `--blockers` replace those CURRENT sections (`;;` or repeat the flag). `--goal` / `--understanding` each accept one string. Re-read and retain other still-valid items before replacing a section; unrelated sections and custom content are preserved.

Missing values and unknown flags fail before writing. Inside the lock, write checks existing memory and validates all proposed files before changing any of them, then checks the written result. These checks do not provide multi-file rollback for an OS or disk failure.

A real patch without `--changed` generates a factual ledger entry; decision-only writes also create a change entry. An unchanged patch with no new fact or decision reports `persisted: false`. Change IDs include a unique suffix, even for simultaneous writes in the same second.

`--decision` appends `DECISIONS.md`. `--file` and `--verification` are optional ledger metadata.

Trivial notes (`完成了`, `done`, `搞定`) with no CURRENT patch and no `--decision` print `nothing-to-persist` and exit 0.

`weplaning-note.cjs` and `weplaning-close.cjs` wrap write. Close no longer requires `--file` / `--verification`.

## Init / check / repair

```bash
node <skill_dir>/scripts/init-memory.cjs <project-root> --agent <name> --project "<name>" --goal "<text>"
# optional: --type code|ops-doc --code-vcs git --sync "<note>"
# existing memory: --force fills only missing files; --reinit destroys CURRENT/CHANGES/DECISIONS
node <skill_dir>/scripts/check-memory.cjs <project-root>
node <skill_dir>/scripts/check-memory.cjs <project-root> --audit
node <skill_dir>/scripts/check-memory.cjs <project-root> --audit --strict
node <skill_dir>/scripts/repair-memory.cjs <project-root>
node <skill_dir>/scripts/check-dirty.cjs <project-root> [--strict] [--json]
node <skill_dir>/scripts/archive-changes.cjs <project-root> [--keep 30] [--dry-run]
```

`check-memory` hard-fails on missing CURRENT/CHANGES, unsupported or duplicate schema lines, missing/empty/duplicate required sections, duplicate known optional sections, conflict markers, and `*.sync-conflict-*` copies. Heading separators and trailing spaces/tabs use the same rules as the parser. It does not require THREADS.md.

`repair-memory` recreates a missing CHANGES header and locally inserts a missing schema line when the resulting files are structurally valid. It retains existing facts, extra sections and the original update time. Malformed CURRENT, unsupported schemas and sync conflicts are rejected before file writes; `--dry-run` applies the same checks. It refuses to invent CURRENT.md. `--prefer current|threads` is removed.

`check-dirty` reports changed paths outside `.agent-memory` — git when the project is a repo, otherwise mtime vs `CURRENT.md` Last updated. Git failure returns `ok: false` and a nonzero exit code; it never reports a clean workspace.

`archive-changes` rolls old ledger blocks into `archive/` and refuses a `CHANGES.md` with no schema header. Archive filenames have unique suffixes; exclusive creation refuses to overwrite an existing archive. Old filenames remain readable/searchable.

## Compatibility scripts

These still exist for old 2.3 trees and should not be used on 3.0 projects: `new-session.cjs`, `safe-edit.cjs`, `merge-session.cjs`, `session-status.cjs`, `archive-threads.cjs`, `append-change.cjs`.

Internal helpers: `weplaning-utils.cjs`.

## Verification (ship / new machine)

- [ ] `node <skill_dir>/tools/smoke-weplaning.cjs` prints all `[ok]` and exits 0
- [ ] `node <skill_dir>/tools/test-concurrency.cjs` passes with 6 simultaneous workers and unique IDs
- [ ] `init-memory.cjs` completes with `--agent <name>`
- [ ] `check-memory.cjs` passes on a fresh project
- [ ] `weplaning-write.cjs` completes and `check-memory.cjs` still passes
- [ ] A 2.3 leftover tree still passes `check-memory.cjs` without being rewritten
