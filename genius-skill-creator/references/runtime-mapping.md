# Runtime Mapping

Load this file when you need to map neutral skill actions to a concrete agent runtime. This is the only shared reference that may list platform tool names.

`SKILL.md` and other `references/` files stay platform-neutral. Runtime-specific metadata lives in `agents/<runtime>.yaml`.

## Detect your runtime

Match the first row where every signature tool is available:

| Runtime | Signature tools | Invoke a sub-skill | Install path |
|---|---|---|---|
| **Claude Code** | `Read`, `Write`, `Edit`, `Grep`, `Glob`, `Bash`, `Skill`, `Agent` | `/skill-name` in chat or the `Skill` tool | `~/.claude/skills/<name>/` or project `.claude/skills/<name>/` |
| **OpenCode** | `Read`, `Write`, `Edit`, `Grep`, `Glob`, `Bash`, `Skill`, `Task` | `Skill` with `name` | `~/.config/opencode/skills/<name>/` or project `.opencode/skills/<name>/` |
| **Codex** | `read_file`, `search_content`, `search_files`, `directory_tree`, `write_file`, `run_command` | `/skill-name` or `$skill-name` in the prompt | project `.agents/skills/<name>/` |

If none match, ask which runtime the user is on and check that runtime's current docs. Do not guess tool names.

## Neutral action map

Translate these phrases from `SKILL.md` to the current runtime:

| Neutral action | Claude Code | OpenCode | Codex |
|---|---|---|---|
| read a file | `Read` | `Read` | `read_file` |
| search code | `Grep` | `Grep` | `search_content` |
| list files | `Glob` | `Glob` | `directory_tree` or `search_files` |
| run a shell command | `Bash` | `Bash` | `run_command` |
| spawn a sub-agent | `Agent` | `Task` | prompt dispatch |
| invoke a skill | `Skill` | `Skill` | `/skill-name` or `$skill-name` |
| validate a skill | `python scripts/quick_validate.py <skill-dir>` via `Bash` | same via `Bash` | same via `run_command` |

## Paths

A reference such as `references/runtime-mapping.md` is relative to the directory that contains this skill's `SKILL.md`. Compute the absolute path from the install path above.

Install paths change between releases. Prefer the runtime's current docs over this table when they disagree.

## If you cannot map something

Mark it unverified and continue with the closest available tool. End the response with: `Platform mapping: <runtime>. Unverified actions: <list>.`
