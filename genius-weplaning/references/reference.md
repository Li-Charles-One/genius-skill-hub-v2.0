# WePlaning Reference (protocol 3.0)

Primary results are the last stdout line (`--json` on read, write, init, repair, archive and find); check chatter goes to stderr. Scripts: `weplaning-read`, `weplaning-write`, `weplaning-find`, `check-memory`, `repair-memory`, `init-memory`, `archive-changes` (all `.cjs` under `scripts/`), sharing `weplaning-utils.cjs`.

`<root>` may be any directory inside the project (default: the current directory). Every script except `init-memory` uses the nearest `.agent-memory` at or above it and, when that is a parent directory, prints `Using project memory at …` on stderr. A path that is not a directory is an error. With no memory found, scripts fail and say to run init only when the user asks.

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
## Project Config        (optional, legacy: older inits wrote it; still valid, no longer created)
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

`DECISIONS.md` is created by the first `--decision`. Blocks: `## <iso-time> decision` with `- Agent:`, `- Decision:`, `- Rationale:`. `--supersedes` adds `- Supersedes: <old heading>` to the new block and `- Superseded by: <new heading>` to the old one; nothing else in an old block changes.

`- Agent:` is `<name>@<device>`: the lowercased runtime name (the list in `SKILL.md`; write and init reject a missing or unlisted `--agent`), the device from the host name. Older entries with other names or without a device stay valid.

Only schema 3.0 passes the check; 2.x files are rejected. Old timestamp-only ledger headings stay valid.

## Read

```bash
node weplaning-read.cjs <root> [--brief] [--next N] [--full] [--limit K] [--find "<q>"] [--json]
node weplaning-find.cjs <root> "<query>" [--regex] [--case] [--limit N] [--scope current|changes|decisions|archive] [--json]
```

- Default: memory root, memory update time, goal, understanding, state, the focus step (the first step an agent can start), next steps, blockers, last 3 ledger blocks. `--brief` omits the ledger and cuts understanding/state items over 80 characters to their label (text before the first colon, else the first 40 characters), reporting how many it shortened; `--full` adds recorded verification and file references, the active decisions (superseded ones are counted, not shown) and the CHANGES archive files.
- Reads run the structural check first. Sync-conflict copies do not stop a read: it shows this device's live files with a warning (JSON `warnings`), while every write still fails until the copies are resolved. JSON `generatedAt` is the read time and `lastUpdated` the memory update time; neither is a live verification.
- `--next N` needs a positive integer naming an existing actionable item; invalid input is an error, never #1. `nextStepsStatus` is `ready`, `none` (`none` / `无待执行事项`), `unknown` or `waiting-user` (every step starts with `【待用户` or `[user]`); the focus (JSON `focusNextStep`) is the first step an agent can start, never a placeholder or a user-owned step, and is absent when there is none. `--next N` may still select a user-owned step. Unknown blockers stay visible.
- Search visits CURRENT before CHANGES, DECISIONS, archive and any other `.md` in the memory folder, so history cannot crowd out current truth.

## Write

```bash
node weplaning-write.cjs <root> --agent <name> --changed "<what happened>" [options]
```

| Flag | Effect |
|---|---|
| `--changed` | Ledger line(s); never changes Current State. Required with any CURRENT patch |
| `--replace <old> --with <new>` | Exact text edit; `old` must occur once in CURRENT (Based On excluded). Repeat pairs in order |
| `--drop <text>` | Remove the single CURRENT line containing `text` |
| `--add-state <text>` / `--add-next <text>` | Append Current State bullet(s) / Accepted Next Steps item(s); a section holding only a placeholder (`none`, `unknown`) has the placeholder replaced |
| `--next-step` / `--blockers` | Replace the whole section (`;;` or repeat the flag) |
| `--goal` / `--understanding` | Replace the section with one (multi-line allowed) string |
| `--decision` [`--rationale`] | Append DECISIONS.md and a ledger entry |
| `--supersedes <text>` | With `--decision`: mark the one active decision containing `text` as superseded. Repeatable |
| `--file` / `--verification` / `--note` | Ledger metadata |

- Exact edits run first, then section replacements, then appends. Accepted Next Steps are renumbered whenever they change; dropping the last step leaves `1. none`.
- A new `--add-state`, `--add-next`, `--next-step` or `--blockers` item over 300 characters fails the write; an old long item resent unchanged passes.
- The ledger holds the stated change, not a copy of the CURRENT diff: a patch without a non-trivial `--changed` fails. A decision without `--changed` is recorded as `Decision: …` (plus `Superseded decision: …`). Trivial notes (`完成了`, `done`, `搞定`, `ok`) with no patch or decision print `nothing-to-persist`.
- Every write refreshes `Last updated` and `Based On` (summary truncated to one line).
- After a persisted write, the `--audit` warnings (see check) print on stderr as `[audit] …`, limited to what this write caused: items it added, growth of CURRENT, blockers it changed. They never block the write.
- Invalid input fails before any file changes: unknown flags (including the removed `--state`), a positional note, missing values, a missing or unlisted `--agent`, a patch without `--changed`, unpaired `--replace`, zero or multiple matches, line breaks outside the multi-line flags, Markdown headings anywhere. Inside a lock the script checks existing memory, validates every proposed file, writes, then checks again. There is no multi-file rollback for OS or disk failure.
- Each overwritten file keeps its last 10 copies in `.backups/`. Change IDs (the block headings) carry a unique suffix even for simultaneous writes.

## Init, check, repair, archive

```bash
node init-memory.cjs <root> --agent <name> --project "<name>" --goal "<text>" [--force | --reinit]
node check-memory.cjs <root> [--audit [--strict]]
node repair-memory.cjs <root> [--dry-run] [--json]
node archive-changes.cjs <root> [--keep 30] [--dry-run] [--json]
```

- `init` runs only when the user asks for project memory. It creates `.agent-memory` in `<root>` itself with CURRENT (Current State `- unknown`) and CHANGES. Existing memory needs `--force` (create only missing files) or `--reinit` (discard CURRENT and CHANGES and empty an existing DECISIONS).
- `check` fails on missing CURRENT/CHANGES, unsupported or duplicate schema lines, missing/empty/duplicate required sections, duplicate optional sections, conflict markers and `*.sync-conflict-*` copies. `--audit` warns on blockers that mix a real item with `none`, on CURRENT items over 300 characters and on a CURRENT.md over 10000 characters.
- `repair` recreates a missing CHANGES header and inserts a missing schema line when the result is valid. It keeps all facts, extra sections and the update time, and refuses malformed CURRENT, unsupported schemas, sync conflicts and a missing CURRENT.
- `archive-changes` moves older blocks to `archive/CHANGES-<unique>.md` (exclusive create, never overwrites) and leaves an `Archived:` breadcrumb.

## Pitfalls

1. `--reinit` destroys history. Never use it to fix a failing check; run `check-memory`, then `repair-memory`.
2. `--next-step` and `--blockers` replace the section, they do not merge. To add one step use `--add-next`; to change or remove one use `--replace/--with` or `--drop`.
3. Sync folders (Syncthing, iCloud): the lock is per device, so concurrent writers on two devices create `*.sync-conflict-*` copies; the check and every write then fail, and reads only warn. Merge what matters, delete the copies, and exclude `.backups/` and `.weplaning.lock` from sync.
4. Recorded state is not a live check. Record verification method/time/result with `--verification`; keep `unknown` distinct from `none`.
5. Scripts use forward slashes and work on Windows through Node path normalization; do not switch them to `\\`.

## Verification (ship / new machine)

- [ ] `node tools/smoke-weplaning.cjs` prints all `[ok]` and exits 0
- [ ] `node tools/test-concurrency.cjs` passes (6 simultaneous writers, unique IDs)
- [ ] `init-memory` → `check-memory` → `weplaning-write` → `check-memory` passes on a fresh project
