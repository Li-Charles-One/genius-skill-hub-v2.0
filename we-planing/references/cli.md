# WePlaning CLI

`<skill_dir>` is the skill directory. Primary results (session id / success) are the last stdout line. Pass `--json` on `init-memory`, `new-session`, `safe-edit`, `weplaning-note`, `weplaning-close`, and `repair-memory`. Consistency check chatter goes to stderr.

Always pass `--agent <persona>` unless `$WEPLANING_AGENT` is set.

## Read

```bash
node <skill_dir>/scripts/weplaning-read.cjs <project-root>
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --handoff
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --brief
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --next 1
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --all
node <skill_dir>/scripts/weplaning-read.cjs <project-root> --json
node <skill_dir>/scripts/weplaning-find.cjs <project-root> "<query>" [--regex] [--case] [--scope current|threads|changes|decisions|sessions|archive] [--json]
```

`--brief` is goal / state / next / blockers only. `--all` also lists abandoned sessions.

## Quick note

```bash
node <skill_dir>/scripts/weplaning-note.cjs <project-root> "<note>" --agent <agent-name>
```

Runs `new-session` + `safe-edit --lite` + check, then auto-closes the session (`closed`) so notes do not stay `active`. Optional: `--role`, `--goal`, `--decision`, `--rationale`, `--json`.

Do not use the two-step Lite flow (`new-session` + `safe-edit --lite`) unless you need an in-progress `active` session.

## Closeout (submit mainline)

```bash
node <skill_dir>/scripts/weplaning-close.cjs <project-root> \
  --changed "<what changed>" --file <path> --verification "<check>" --agent <agent-name>
```

Creates a session if `--session` is omitted. Defaults to `--no-sync` so curated Current State is not replaced by `--changed`. To update accepted state:

```bash
node <skill_dir>/scripts/weplaning-close.cjs <project-root> \
  --changed "<what changed>" --file <path> --verification "<check>" \
  --state "Feature A done;;Feature B in review" \
  --next-step "Ship feature B;;Start feature C" \
  --blockers "none"
```

`--state` / `--next-step` / `--blockers` / `--understanding` replace their CURRENT sections (`;;` or repeat the flag). `--goal` is the new session's goal only (default: `--changed`); it does not rewrite CURRENT Active Goal. `--replace-state` allows `--changed` to overwrite curated Current State.

Low-level equivalent: `safe-edit.cjs --close --session <id> ...` (session must already exist; parent must equal THREADS mainline).

## Mid-session update

For an `active` or `closed` session that is not yet merged:

```bash
node <skill_dir>/scripts/new-session.cjs <project-root> --agent <agent-name> --role <role> --summary "<summary>" --goal "<goal>"
node <skill_dir>/scripts/safe-edit.cjs <project-root> --update --session <id> \
  --result "<progress>" --next-step "<exact next>" --file "<path>" --decision "<decision>" --note "<work note>"
```

`safe-edit --update` refuses `merged` sessions.

## Maintenance

```bash
node <skill_dir>/scripts/init-memory.cjs <project-root> --agent <agent-name> --project "<name>" --goal "<goal>"
# optional: --type code|ops-doc --code-vcs git --sync "<note>"
# existing memory: --force fills only missing files; --reinit destroys and rebuilds
node <skill_dir>/scripts/check-memory.cjs <project-root>
node <skill_dir>/scripts/check-memory.cjs <project-root> --audit
node <skill_dir>/scripts/check-memory.cjs <project-root> --audit --strict
node <skill_dir>/scripts/check-dirty.cjs <project-root> [--strict] [--json]
node <skill_dir>/scripts/session-status.cjs <project-root> --session <id> --pause|--resume|--abandon [--reason "<text>"]
node <skill_dir>/scripts/append-decision.cjs <project-root> --decision "<text>" [--rationale "<why>"] [--session <id>]
node <skill_dir>/scripts/archive-changes.cjs <project-root> [--keep 30] [--dry-run]
node <skill_dir>/scripts/archive-threads.cjs <project-root> [--keep 40] [--dry-run]
node <skill_dir>/scripts/repair-memory.cjs <project-root>
node <skill_dir>/scripts/repair-memory.cjs <project-root> --prefer current
node <skill_dir>/scripts/repair-memory.cjs <project-root> --prefer threads
```

`check-memory` hard-fails on structure errors (mainline mismatch, missing session files, unknown parents, conflict markers, `*.sync-conflict-*` copies). `--audit` warnings exit 0 unless `--strict`.

`archive-threads` moves finished rows and their session files into `archive/`; never touches mainline or active/paused. Archived ids stay valid parents because `check-memory` also reads `archive/THREADS-*.md`.

`check-dirty` reports changed paths outside `.agent-memory` — git when the project is a repo, otherwise mtime vs `CURRENT.md` Last updated.

`archive-changes` rolls old ledger blocks into `archive/`, writes an `Archived:` breadcrumb, and refuses a `CHANGES.md` with no schema header.

Internal helpers (do not call from chat unless debugging): `append-change.cjs`, `merge-session.cjs`, `weplaning-utils.cjs`.

## Verification (ship / new machine)

- [ ] `node <skill_dir>/tools/smoke-weplaning.cjs` prints all `[ok]` and exits 0
- [ ] `init-memory.cjs` completes with `--agent <name>`
- [ ] `check-memory.cjs` passes on a fresh project
- [ ] `weplaning-note.cjs` completes and `check-memory.cjs` still passes
- [ ] `weplaning-close.cjs` completes; session is `merged` in `THREADS.md`
