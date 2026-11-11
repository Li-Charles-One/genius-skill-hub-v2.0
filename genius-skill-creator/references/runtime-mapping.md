# Runtime Mapping

Load this file when you need to map neutral skill actions to a concrete agent runtime. This is the only shared reference that may list platform tool names.

`SKILL.md` and other `references/` files stay platform-neutral. Runtime-specific metadata lives in `agents/<runtime>.yaml`.

## Detect your runtime

Match the first row where every signature tool is available:

| Runtime | Signature tools | Invoke a sub-skill | Install path |
|---|---|---|---|
| **Claude Code** | `Read`, `Edit`, `Bash`, `Skill`, `Agent` | `/skill-name` in chat or the `Skill` tool | `~/.claude/skills/<name>/` or project `.claude/skills/<name>/` |
| **OpenCode** | `Read`, `Write`, `Edit`, `Grep`, `Glob`, `Bash`, `Skill`, `Task` | `Skill` with `name` | `~/.config/opencode/skills/<name>/` or project `.opencode/skills/<name>/` |
| **Codex** | `apply_patch`, `update_plan` and a shell tool (`shell` or `shell_command`, by version) | `$skill-name` in the prompt, or `/skills` | `~/.agents/skills/<name>/` or project `.agents/skills/<name>/` |

If none match, ask which runtime the user is on and check that runtime's current docs. Do not guess tool names.

How far each row is verified: Claude Code in a live session on 2026-11-11 (that build had no `Grep` or `Glob`, so they are not signature tools); Codex install paths from the official skills docs; Codex tool names from third-party references only, and they change between versions; OpenCode as recorded in `agents/opencode.yaml`.

## Neutral action map

Translate these phrases from `SKILL.md` to the current runtime:

| Neutral action | Claude Code | OpenCode | Codex |
|---|---|---|---|
| read a file | `Read` | `Read` | the shell tool, or `read_file` where present |
| search code | `Grep` where present, else `Bash` | `Grep` | the shell tool (`rg`) |
| list files | `Glob` where present, else `Bash` | `Glob` | the shell tool, or `list_dir` where present |
| edit a file | `Edit` | `Edit` | `apply_patch` |
| run a shell command | `Bash` | `Bash` | the shell tool |
| spawn a sub-agent | `Agent` | `Task` | `spawn_agent` where present, else prompt dispatch |
| invoke a skill | `Skill` | `Skill` | `$skill-name` |
| validate a skill | `python scripts/quick_validate.py <skill-dir>` via `Bash` | same via `Bash` | same via the shell tool |

## Paths

A reference such as `references/runtime-mapping.md` is relative to the directory that contains this skill's `SKILL.md`. Compute the absolute path from the install path above.

Install paths change between releases. Prefer the runtime's current docs over this table when they disagree.

## If you cannot map something

Mark it unverified and continue with the closest available tool. End the response with: `Platform mapping: <runtime>. Unverified actions: <list>.`
