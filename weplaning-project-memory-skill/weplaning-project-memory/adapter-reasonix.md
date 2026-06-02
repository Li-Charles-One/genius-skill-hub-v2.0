# WePlaning Adapter - Reasonix

Agent: Reasonix Code (deepseek-v4-pro)
Environment: Reasonix CLI / sandbox
OS: (detected at runtime)
Integration format: Native skill in `.reasonix/skills/weplaning-project-memory/`
Verified capabilities: Full — all protocol operations mappable.

## Capability Map

| WePlaning operation | Actual Agent tool/command | Status | Notes |
|:--|:--|:--|:--|
| Read memory | `read_file` | available | Reads any `.agent-memory/` file. Supports range/head/tail scoping. |
| Create memory file | `write_file` | available | Creates file + parent directories automatically. |
| Update summary file | `edit_file` or `write_file` (after `read_file`) | available | `edit_file` uses SEARCH/REPLACE for surgical edits. `write_file` for full rewrites. |
| Append ledger entry | `edit_file` | available | Append to `CHANGES.md` via SEARCH/REPLACE targeting the last line. |
| List sessions | `list_directory` | available | `list_directory .agent-memory/sessions/` |
| Find references | `search_content` / `search_files` / `glob` | available | `search_content` for content grep; `search_files` for filename match; `glob` for pattern listing. |
| Check drift | `search_content` + `get_file_info` + `run_command` | available | `get_file_info` for existence/mtime; `run_command` for `git diff --stat` |
| Check conflict | `get_file_info` (mtime) + `read_file` re-read before write | available | Re-read-before-write pattern is the standard Reasonix conflict strategy. |
| Record tools | `edit_file` or `write_file` on `TOOLS.md` | available | Same edit primitives. |
| Run verification | `run_command` | available | Full shell access for tests, lints, git commands. |
| Create directory | `create_directory` | available | Creates parent dirs automatically. |
| Delete | `delete_file` / `delete_directory` | available | `delete_directory` supports recursive. |
| Move / copy files | `move_file` / `copy_file` | available | Supports both files and directories. |
| Multi-file edits | `multi_edit` | available | Batch SEARCH/REPLACE across files — useful for cross-file session updates. |

## Tool Mapping Cheat Sheet

Quick reference for Reasonix → WePlaning:

```
read_file(path)                   → Read any memory file
write_file(path, content)          → Create memory/session file
edit_file(path, search, replace)   → Update summary, append ledger
multi_edit(edits[])                → Atomic cross-file updates
list_directory(path)               → List sessions, inspect memory
search_content(pattern, path)      → Drift check, find references
get_file_info(path)                → Exists?, mtime for conflict
run_command(cmd)                   → git diff, tests, lint
create_directory(path)             → Bootstrap .agent-memory/
```

## Append Pattern (CHANGES.md)

Reasonix has no raw append tool. Use `edit_file` targeting the file's last line:

```
read_file(".agent-memory/CHANGES.md", tail:5)    // get last lines for SEARCH anchor
edit_file(
  path: ".agent-memory/CHANGES.md",
  search: "<last line of file>",
  replace: "<last line of file>\n\n## <new entry>"
)
```

Or, when the file is short, read full content and `write_file` with the appended entry.

**Important**: Reasonix requires `read_file` on a path before `edit_file` will accept it — the re-read-before-write constraint is enforced by the tool system, which naturally satisfies WePlaning's conflict-detection rule.

## Startup Instruction

When starting a WePlaning session on Reasonix, read these files in order:

1. `read_file(".agent-memory/WePlaning.md")`
2. `read_file(".agent-memory/CURRENT.md")`
3. `read_file(".agent-memory/THREADS.md")`
4. `read_file(".agent-memory/CHANGES.md", tail:30)` — recent changes
5. `read_file(".agent-memory/TOOLS.md")` — if tool capability matters
6. Create session: `write_file(".agent-memory/sessions/<session_id>.md", content)`
7. Update THREADS: `edit_file(".agent-memory/THREADS.md", ...)` — add active row

## Closeout Instruction

1. Update session status to `paused`, `merged`, or `abandoned` → `edit_file` on the session file
2. Update `THREADS.md` → `edit_file`
3. Append `CHANGES.md` → `edit_file` (append pattern above)
4. Update `TOOLS.md` if tools were used → `edit_file`
5. Refresh `WePlaning.md` if mainline changed → `edit_file`
6. Output handoff packet in chat (plain markdown, no file write unless user asks)

## Limitations

- No `append_text` primitive — worked around via `edit_file` (SEARCH/REPLACE on last line) or `write_file` (full rewrite). Mildly heavier for long `CHANGES.md` but functionally equivalent.
- No `directory_tree` in capability map — use `list_directory` for flat listing; `directory_tree` exists but is for exploration, not protocol operations.
- `edit_file` SEARCH must be unique in file — safe for structured WePlaning files where entries have unique timestamps/IDs.
- Shell commands require user confirmation for mutating operations — `run_command` for git diff / verification is read-only and runs immediately; writes to project files should use file tools anyway.
- All file paths resolve under sandbox root — repo-relative paths work directly; absolute Windows paths must be marked `local-only` per WePlaning rules.
