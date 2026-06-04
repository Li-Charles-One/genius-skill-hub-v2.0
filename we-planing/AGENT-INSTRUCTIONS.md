# WePlaning v2.2 Agent Instructions

This file is the cross-Agent adapter layer for WePlaning. It is intentionally not Codex-specific.

Use it when an Agent cannot install the native Codex skill format but can read project instructions, custom rules, memory files, or a Markdown workflow.

Important:

> Do not guess an Agent's commands from its name. Identify the Agent first, then inspect its actual available tools, commands, rules, or documentation before creating a mapping.

## Purpose

WePlaning is project-owned memory for multi-session and multi-Agent collaboration.

The same protocol supports:

- One Agent continuing the same project across many conversations.
- Multiple Agents collaborating on the same project.
- Humans hand-editing memory files.

Execution principle:

> Minimal first. `CHANGES.md` is the canonical ledger. `CURRENT.md` is accepted state. `sessions/` are work branches. Optional files are indexes or context, not new truth sources.

## Required Agent Capabilities

A WePlaning-capable Agent needs these abilities:

| Capability | Required | Used for |
|:--|:--:|:--|
| Read files | yes | Read `.agent-memory/` state. |
| Write/edit files | yes | Create sessions and update memory. |
| Append text | yes | Append to `CHANGES.md`. |
| List directory | yes | Inspect `.agent-memory/` and `sessions/`. |
| Search files/content | recommended | Drift/schema checks. |
| File metadata or hash | recommended | Conflict detection. |
| Shell/commands | optional | Git, tests, scripts, validation. |
| MCP/tools registry | optional | Record capabilities in `TOOLS.md`. |

If a capability is unavailable, write `unavailable`. If uncertain, write `unknown`.

## Adapter Discovery Workflow

Before adapting WePlaning to a new Agent, run this discovery flow.

### 1. Identify the Agent

If the Agent identity is not obvious, ask the user:

```text
Which Agent or environment should use WePlaning here? Examples: Codex, Reasonix, Claude Code, Cursor, Windsurf, Trae, Tongyi Lingma, Baidu Comate, CodeGeeX, Doubao/豆包, Kimi, Zhipu/智谱, DeepSeek, Qwen, or another tool.
```

Record the answer in `TOOLS.md`:

```markdown
| Session ID | Agent | OS | Adapter | Tools | MCP | Skills | Notes |
|:--|:--|:--|:--|:--|:--|:--|:--|
| <session_id> | <agent name> | <os> | <adapter/rules format> | unknown | unknown | unknown | Discovery pending |
```

### 2. Discover the Agent's Real Tool Surface

Use only available evidence:

- Built-in tool list shown by the Agent.
- Project rule files such as `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `.windsurf/`, `.trae/`, `.reasonix/`, or equivalent.
- Official docs or local help, if the user asks or allows web lookup.
- CLI help such as `<agent> --help`, only when the command is known and safe to run.
- Existing project scripts or MCP config files, without copying secrets.

Do not invent commands such as "read_file" or "edit_file" unless the Agent actually exposes those names.

### 3. Fill a Capability Map

Create or update a capability map in `TOOLS.md`:

```markdown
## Agent Capability Map - <agent name>

| WePlaning operation | Agent capability/tool | Status | Notes |
|:--|:--|:--|:--|
| Read file | <actual tool/command/rule> | available/unknown/unavailable | <notes> |
| Write/edit file | <actual tool/command/rule> | available/unknown/unavailable | <notes> |
| Append ledger | <actual tool/command/rule> | available/unknown/unavailable | <notes> |
| List directory | <actual tool/command/rule> | available/unknown/unavailable | <notes> |
| Search content | <actual tool/command/rule> | available/unknown/unavailable | <notes> |
| Run shell/tests | <actual tool/command/rule> | available/unknown/unavailable | <notes> |
| MCP/tools | <actual tool/command/rule> | available/unknown/unavailable | <notes> |
```

### 4. Choose Integration Format

Pick the simplest supported format:

| If the Agent supports... | Use... |
|:--|:--|
| Native skill/plugin folders | Convert `SKILL.md` and this file to that format. |
| Project instructions | Add this file or a concise version to project instructions. |
| Rule files | Add a WePlaning rule file. |
| Only chat context | Paste the relevant sections of this file and the protocol actions. |
| Only filesystem access | Keep this file in the repo and tell the Agent to read it first. |

### 5. Test With One Minimal Flow

Do not claim support until the Agent can perform this small flow:

1. Read `.agent-memory/WePlaning.md`.
2. Read `CURRENT.md` and `THREADS.md`.
3. Create one session file.
4. Append one entry to `CHANGES.md`.
5. Update `THREADS.md`.
6. Produce a handoff packet.

## Minimal Mode Files

Every Agent must understand Minimal Mode:

```text
.agent-memory/
├── WePlaning.md
├── CURRENT.md
├── THREADS.md
├── CHANGES.md
├── TOOLS.md
└── sessions/
```

Optional mode files:

```text
Standard: PROJECT.md, notes/
Full: DECISIONS.md, DONE.md, FUTURE.md, REFERENCES.md, SCRIPTS.md
```

Do not require optional files unless the project has enabled that mode.

## Protocol Actions

### bootstrap

Create `.agent-memory/`, Minimal Mode files, and `sessions/`.

Steps:

1. Create root session under `sessions/`.
2. Set `THREADS.md` `Mainline session` to the root session.
3. Write `CURRENT.md` as accepted mainline.
4. Append initialization to `CHANGES.md`.
5. Record available capabilities in `TOOLS.md`.

### start-session

Use when beginning work that may affect project or memory state.

Steps:

1. Read `WePlaning.md`, `CURRENT.md`, `THREADS.md`, recent `CHANGES.md`, and `TOOLS.md`.
2. Create `sessions/<session_id>.md`.
3. Set `Parent session` to the current mainline unless intentionally branching.
4. Add the session to `THREADS.md` as `active`.

Session ID format:

```text
<UTC timestamp>-<agent>-<os>-<role>-<short id>
```

Example:

```text
20260601T063000Z-codex-win-editor-a3f9
```

### close-session

Close means preserving conversation state, not necessarily finishing work.

Close when:

- The user asks to stop, summarize, hand off, close, or switch Agent.
- Work reaches a stable checkpoint.
- Durable project/memory changes occurred.
- A durable decision was made.
- Exact next steps need preservation.

Statuses:

- `paused`: closed but not accepted into mainline.
- `merged`: closed and accepted into mainline.
- `abandoned`: closed and intentionally not used.

### merge-mainline

Merge only when the session result should become accepted project state.

Steps:

1. Check whether the session parent is still the `THREADS.md` mainline.
2. If not, re-read current mainline and re-apply the durable result or record a conflict.
3. Update `CURRENT.md`.
4. Update `THREADS.md` `Mainline session`.
5. Append `CHANGES.md`.
6. Update optional indexes only when enabled.

### handoff

Output this packet in chat:

```markdown
Project:
Current mainline session:
Current session:
Parent session:
Current goal:
Current state:
Important files:
Tools used:
Commands/tests run:
Open blockers:
Session status:
Should merge to mainline:
Exact next step:
```

## Tool Mapping

Map your Agent's tools to these protocol operations:

| Protocol operation | Tool capability needed |
|:--|:--|
| Read memory | read file |
| Create memory file | write file |
| Update summary file | edit file / write file after re-read |
| Append ledger entry | append text / edit file |
| List sessions | list directory |
| Find references | search files/content |
| Check drift | search + file exists + optional shell/git |
| Check conflict | file metadata/hash or re-read before write |
| Record tools | write/edit `TOOLS.md` |
| Run verification | shell/test command, if available |

## Adapter Matrix

This matrix lists likely integration targets, not guaranteed command names.

| Agent / environment | Recommended integration | Discovery note |
|:--|:--|:--|
| Codex | Install as native skill. Use `SKILL.md`; read reference only when needed. | Validate with Codex skill validator. |
| Reasonix | Convert this file into a Reasonix skill or project rule. | Inspect `.reasonix/` and Reasonix tool docs/config before mapping commands. |
| Claude Code | Add this file or a condensed version to project instructions / `CLAUDE.md`. | Inspect available file edit, shell, and MCP tools in the current Claude Code environment. |
| Cursor | Add as project rule. | Inspect `.cursor/rules` and available editor/terminal abilities. |
| Windsurf | Add as workspace rule. | Inspect Windsurf rules and available terminal/file tools. |
| Trae / TREA | Add as project rule or custom instruction. | Inspect Trae/TREA rule format and tool surface first. |
| Tongyi Lingma / 通义灵码 | Add as workspace/project instruction if supported. | Check Lingma's current rule/plugin/tool mechanism before mapping operations. |
| Baidu Comate / 文心快码 | Add as project instruction if supported. | Check Comate's current command/rule/tool mechanism before mapping operations. |
| CodeGeeX | Add as project instruction or prompt template if supported. | Check CodeGeeX IDE/plugin capabilities first. |
| Doubao / 豆包 | Use as custom instruction or project prompt if filesystem access exists. | Confirm whether the environment can read/write project files. |
| Kimi | Use as custom instruction or project prompt if filesystem access exists. | Confirm whether the environment can edit files or only provide guidance. |
| Zhipu / 智谱 / GLM | Use as custom instruction or tool wrapper guidance. | Confirm actual file/shell tool exposure before mapping. |
| DeepSeek | Use as custom instruction or coding-agent rule if available. | Confirm actual IDE/agent wrapper capabilities. |
| Qwen / 通义千问 | Use as custom instruction or coding-agent rule if available. | Confirm actual filesystem/tool access first. |
| Generic Agent | Read this file and the protocol reference, then implement protocol actions manually. | Fill the capability map before editing memory files. |

## Adapter Deliverable Template

When creating an adapter for another Agent, produce a short adapter note:

```markdown
# WePlaning Adapter - <Agent>

Agent:
Environment:
OS:
Integration format:
Verified capabilities:

## Capability Map
| WePlaning operation | Actual Agent tool/command | Status | Notes |
|:--|:--|:--|:--|

## Startup Instruction
<what the Agent should read first>

## Closeout Instruction
<how the Agent should close/merge/handoff>

## Limitations
- <unknown/unavailable capabilities>
```

Store this note in one of:

- `TOOLS.md` for short mappings.
- `notes/` for long adapter notes when Standard Mode is enabled.
- The Agent's own rule/skill directory when it has a native format.

## Safety Rules

- Never record secrets, tokens, private MCP credentials, cookies, or passwords.
- Record tool capability, not credentials.
- Use repo-relative paths for project files.
- Mark local absolute paths as `local-only`.
- Do not silently overwrite human edits.
- Use `unknown` for uncertain facts and `unavailable` for missing capabilities.

## Reference Files

- Full protocol: `references/weplaning-v2.2-protocol.md`
- Codex native skill: `SKILL.md`
