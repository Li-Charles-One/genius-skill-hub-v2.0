# WePlaning Reference (protocol 3.0)

Primary results are the last stdout line (`--json` on read, write, init, repair, archive and find); check chatter goes to stderr. Scripts: `weplaning-read`, `weplaning-write`, `weplaning-find`, `check-memory`, `repair-memory`, `init-memory`, `archive-changes`, `check-dirty` (all `.cjs` under `scripts/`), sharing `weplaning-utils.cjs`.

## Files

```markdown
# Current Mainline
Schema version: 3.0
Last updated: <iso-time>

## Active Goal
## Current Understanding
## Current State
- <fact>
## Accepted Next Steps
1. <next step>
## Open Blockers
- none
## Project Config        (optional; written by init: Type code|ops-doc, Code VCS, Sync)
## Based On
- Last change: <iso-time> <summary>
```

`CHANGES.md` (`# Changes` + schema line) appends blocks and never rewrites old ones:

```markdown
## <iso-time> change <unique-suffix>
- Agent: <agent>
- Changed:
  - <durable change>
- Files touched:
  - <path>
- Verification:
  - <check>
- Notes:
  - <note>
```

The heading is the change ID. `Files touched`, `Verification` and `Notes` appear only when passed. Older blocks with a `Change ID` line and `none` fields stay valid.

`DECISIONS.md` blocks: `## <iso-time> decision` with `- Agent:`, `- Decision:`, `- Rationale:`. `--supersedes` adds `- Supersedes: <old heading>` to the new block and `- Superseded by: <new heading>` to the old one; nothing else in an old block changes.

`- Agent:` is `<name>@<device>`: the name lowercased, the device from the host name. Older entries without a device stay valid.

Only schema 3.0 passes the check; 2.x files are rejected. Old timestamp-only ledger headings stay valid.

## Read

```bash
node weplaning-read.cjs <root> [--brief] [--handoff] [--next N] [--full] [--limit K] [--find "<q>"] [--json]
node weplaning-find.cjs <root> "<query>" [--regex] [--case] [--limit N] [--scope current|changes|decisions|archive] [--json]
```

- Default: memory update time, goal, understanding, state, next steps, blockers, last 3 ledger blocks. `--brief` omits the ledger and cuts understanding/state items over 80 characters to their label (text before the first colon, else the first 40 characters), reporting how many it shortened; `--handoff` adds recorded verification and file references; `--full` adds the active decisions (superseded ones are counted, not shown) and lists CHANGES and DECISIONS archive files.
- Reads run the structural check first. JSON `generatedAt` is the read time and `lastUpdated` the memory update time; neither is a live verification.
- `--next N` needs a positive integer naming an existing actionable item; invalid input is an error, never #1. `nextStepsStatus` is `ready`, `none` (`none` / `无待执行事项`), `unknown` or `waiting-user` (every step starts with `【待用户` or `[user]`); handoff focuses the first step an agent can start, never a placeholder or a user-owned step. `--next N` may still select a user-owned step. Unknown blockers stay visible.
- Search visits CURRENT before CHANGES, DECISIONS, archive and any other `.md` in the memory folder, so history cannot crowd out current truth.

## Write

```bash
node weplaning-write.cjs <root> --agent <name> [note] [options]
```

| Flag | Effect |
|---|---|
| `--changed` / positional note | Ledger line(s); never changes Current State |
| `--replace <old> --with <new>` | Exact text edit; `old` must occur once in CURRENT (Based On excluded). Repeat pairs in order |
| `--drop <text>` | Remove the single CURRENT line containing `text` |
| `--add-state <text>` | Append Current State bullet(s) |
| `--state` / `--next-step` / `--blockers` | Replace the whole section (`;;` or repeat the flag) |
| `--goal` / `--understanding` | Replace the section with one (multi-line allowed) string |
| `--decision` [`--rationale`] | Append DECISIONS.md and a ledger entry |
| `--supersedes <text>` | With `--decision`: mark the one active decision containing `text` as superseded. Repeatable |
| `--file` / `--verification` / `--note` | Ledger metadata |

- Exact edits run first, then section replacements. Accepted Next Steps are renumbered whenever they change.
- Without `--changed`, the ledger records what changed (`Replaced in CURRENT: …`, `Updated <section>: …`, `Decision: …`). Unchanged patches with no new fact write nothing (`persisted: false`). Trivial notes (`完成了`, `done`, `搞定`, `ok`) with no patch or decision print `nothing-to-persist`.
- Every write refreshes `Last updated` and `Based On` (summary truncated to one line).
- After a persisted write, the `--audit` warnings (see check) print on stderr as `[audit] …`; they never block the write.
- Invalid input fails before any file changes: unknown flags, missing values, unpaired `--replace`, zero or multiple matches, line breaks outside the multi-line flags, Markdown headings anywhere. Inside a lock the script checks existing memory, validates every proposed file, writes, then checks again. There is no multi-file rollback for OS or disk failure.
- Each overwritten file keeps its last 10 copies in `.backups/`. Change IDs (the block headings) carry a unique suffix even for simultaneous writes.

## Init, check, repair, archive, dirty

```bash
node init-memory.cjs <root> --agent <name> --project "<name>" --goal "<text>" [--type code|ops-doc] [--code-vcs git] [--sync "<note>"] [--force | --reinit]
node check-memory.cjs <root> [--audit [--strict]]
node repair-memory.cjs <root> [--dry-run] [--json]
node archive-changes.cjs <root> [--keep 30] [--dry-run] [--json]
node check-dirty.cjs <root> [--strict] [--json] [--limit N]
```

- `init`: existing memory needs `--force` (create only missing files) or `--reinit` (discard CURRENT/CHANGES/DECISIONS). Project Config: code projects keep code in git and WePlaning owns only `.agent-memory`; ops/doc projects are standalone.
- `check` fails on missing CURRENT/CHANGES, unsupported or duplicate schema lines, missing/empty/duplicate required sections, duplicate optional sections, conflict markers and `*.sync-conflict-*` copies. `--audit` warns on blockers that mix a real item with `none`, on CURRENT items over 300 characters and on a CURRENT.md over 8000 bytes.
- `repair` recreates a missing CHANGES header and inserts a missing schema line when the result is valid. It keeps all facts, extra sections and the update time, and refuses malformed CURRENT, unsupported schemas, sync conflicts and a missing CURRENT.
- `archive-changes` moves older blocks to `archive/CHANGES-<unique>.md` (exclusive create, never overwrites) and leaves an `Archived:` breadcrumb.
- `check-dirty` lists changed paths outside `.agent-memory` (git status, or mtime newer than `Last updated` without git). A git failure is `ok: false`, never clean.

## Pitfalls

1. Run the smoke test before `init` on a new machine; a broken init is harder to recover than a failed test.
2. `--reinit` destroys history. Never use it to fix a failing check; run `check-memory`, then `repair-memory`.
3. Section replacement is not item merging. Prefer `--replace/--with`, `--add-state` or `--drop`; when replacing a section, include every still-valid item.
4. Sync folders (Syncthing, iCloud): the lock is per device, so concurrent writers on two devices create `*.sync-conflict-*` copies and the check fails. Merge what matters, delete the copies, and exclude `.backups/` and `.weplaning.lock` from sync.
5. Recorded state is not a live check. Record verification method/time/result with `--verification`; keep `unknown` distinct from `none`.
6. When offering destructive choices, every stated consequence must be true.
7. Scripts use forward slashes and work on Windows through Node path normalization; do not switch them to `\\`.
8. Installing from the hub through a junction or symlink: see `hermes-install.md` at the hub root.

## Verification (ship / new machine)

- [ ] `node tools/smoke-weplaning.cjs` prints all `[ok]` and exits 0
- [ ] `node tools/test-concurrency.cjs` passes (6 simultaneous writers, unique IDs)
- [ ] `init-memory` → `check-memory` → `weplaning-write` → `check-memory` passes on a fresh project
