# Runtime Mapping

Load this file when you need to map neutral skill actions to a concrete agent runtime. This is the only shared reference that may list platform tool names.

`SKILL.md` and other `references/` files stay platform-neutral. Runtime-specific allowlists also live in `agents/<runtime>.yaml`.

## Detect your runtime

Match the first row where every signature tool is available:

| Runtime | Signature tools | Invoke a sub-skill | Install path |
|---|---|---|---|
| **OpenCode** | `Read`, `Write`, `Edit`, `Grep`, `Glob`, `Bash`, `Skill` | `Skill` with `name` | `~/.config/opencode/skills/<name>/` or project `.opencode/skills/<name>/` |
| **Reasonix** | `read_file`, `write_file`, `edit_file`, `bash`, `run_skill` | `run_skill({ name: "<skill>", arguments: "..." })` | `~/.reasonix/skills/<name>/` |
| **Codex** | `read_file`, `search_content`, `search_files`, `directory_tree`, `write_file`, `run_command` | `/skill-name` or `$skill-name` in the prompt | `.agents/skills/<name>/` |
| **Cursor** | `search_file`, `search_content`, `read_file`, `write`, `execute_command`, `editor_edit_file` | `/<skill-name>` in chat | `.cursor/skills/<name>/` |
| **Claude Code** | `Read`, `Write`, `Edit`, `Grep`, `Glob`, `Bash`, `Task` | `/skill-name` in chat | `.claude/skills/<name>/` or `~/.claude/skills/<name>/` |
| **ZCode / Kiro** | `Read`, `Write`, `Edit`, `Bash`, `Agent`, `Skill` | `/skill-name` or the Skill tool | `~/.zcode/skills/<name>/` or `~/.kiro/skills/<name>/` |
| **Hermes** | `read_file`, `write_file`, `bash`, `run_skill` | `run_skill({ name: "<skill>" })` | `~/.hermes/skills/<category>/<name>/` |

If none match, ask which runtime the user is on, then look up that row. Do not guess tool names.

## Evidence notes

- **OpenCode:** verified in-session. Extra tools such as `Task`, `TodoWrite`, `Question`, and `WebFetch` may exist; they are not required to identify the runtime.
- **Reasonix:** `run_skill` and `Bash(...)` are verified from a local `reasonix.toml` allow list. `read_file`, `write_file`, `edit_file`, `grep`, `glob`, `ls`, and `task` follow the hub fingerprint and are **unverified** against upstream source. Do not replace them with Codex names (`search_content`, `directory_tree`, `run_command`).
- **Codex / Cursor / Claude Code / ZCode / Kiro / Hermes:** inherited hub fingerprints; re-check official docs before adding a new adapter.

## Neutral action map

Translate these phrases from `SKILL.md` to the current runtime:

| Neutral action | OpenCode | Reasonix | Codex |
|---|---|---|---|
| read a file | `Read` | `read_file` | `read_file` |
| search code | `Grep` | `grep` (unverified) | `search_content` |
| list files | `Glob` | `glob` or `ls` (unverified) | `directory_tree` or `search_files` |
| run a shell command | `Bash` | `bash` | `run_command` |
| spawn a sub-agent | `Task` | `task` (unverified) | prompt dispatch |
| invoke a skill | `Skill` | `run_skill` | `/skill-name` or `$skill-name` |
| validate a skill | `python scripts/quick_validate.py <skill-dir>` via `Bash` | same via `bash` | same via `run_command` |

For other runtimes, use the signature table plus that runtime's adapter. Never copy another adapter's tool names.

## Paths

A reference such as `references/runtime-mapping.md` is relative to the directory that contains this skill's `SKILL.md`. Compute the absolute path from the install path above.

## Common install roots

| Runtime | Config dir | Skill location |
|---|---|---|
| OpenCode | `~/.config/opencode/` or project `.opencode/` | `skills/<name>/SKILL.md` |
| Reasonix | `~/.reasonix/` | `skills/<name>/SKILL.md` |
| Codex | Project `.agents/` | `skills/<name>/SKILL.md` |
| Cursor | Project `.cursor/` | `skills/<name>/SKILL.md` |
| Claude Code | Project `.claude/` or `~/.claude/` | `skills/<name>/SKILL.md` |
| Gemini CLI | Project `.gemini/` | `skills/<name>/SKILL.md` (tools unverified) |
| Trae CN | `~/.trae-cn/` or project `.trae/` | `skills/<name>/SKILL.md` |
| Hermes | `~/.hermes/` | `skills/<category>/<name>/SKILL.md` |

These paths change. Prefer the runtime's current docs over this table when they disagree.

## If you cannot map something

Mark it unverified and continue with the closest available tool. End the response with: `Platform mapping: <runtime>. Unverified actions: <list>.`
