# WePlaning Adapter - Reasonix

Agent: Reasonix Code
Integration format: native skill in `.reasonix/skills/we-planing/`
Protocol: WePlaning v2.3

## Capability Map

| WePlaning operation | Reasonix tool pattern | Notes |
|:--|:--|:--|
| Read memory | `read_file` | Read `CURRENT.md`, `THREADS.md`, `CHANGES.md`, and session files. |
| Create session | `write_file` | Create `.agent-memory/sessions/<id>.md`. |
| Update memory | `edit_file`, `multi_edit`, or full `write_file` rewrite | Re-read before edit. |
| Append ledger | read full `CHANGES.md`, then `write_file` full appended content | Avoid non-unique last-line SEARCH anchors. |
| List sessions | `list_directory` | Inspect `.agent-memory/sessions/`. |
| Verify | `run_command` | Prefer `node scripts/check-memory.cjs <root>`. |

## Startup

1. Read `.agent-memory/CURRENT.md`.
2. Read `.agent-memory/THREADS.md`.
3. Read recent `.agent-memory/CHANGES.md`.
4. Read relevant `.agent-memory/sessions/<id>.md`.
5. Create a session only if writing durable memory.

## Closeout

1. Update the session file with result and exact next step.
2. Append `CHANGES.md` by reading the full file and writing the appended content.
3. Update `THREADS.md` and `CURRENT.md` consistently, or run `safe-edit.cjs --close`.
4. Run `check-memory.cjs`.
5. Output a concise handoff packet in chat when the user asks.

## Rules

- `WePlaning.md` is not part of v2.3; ignore it if present.
- `TOOLS.md` is optional and should not block base validation.
- Do not use `close-session`, `register-agent`, `session-list`, `sync-before-write`, `pre-close-check`, or `audit-memory`; those v2.2 scripts are removed or folded into v2.3 flows.
- Do not record secrets or private credentials.
