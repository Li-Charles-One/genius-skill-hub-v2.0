# WePlaning v2.2 - Project Collaboration Memory Protocol

> WePlaning is a lightweight, project-owned collaboration memory protocol for multiple agents, multiple sessions, and multiple operating systems.

WePlaning v2.2 is not a database and not a private memory store for one agent. It is a set of Markdown files kept inside a project repository, used to record the project mainline, session branches, durable changes, decisions, completed work, tools, scripts, and handoff context.

The goal is simple:

> Let any capable Agent open the project, understand the current mainline, see who changed what, continue from the right session, and leave enough durable context for the next Agent.

---

## 0. Scope

### This protocol is for

- Multi-Agent project collaboration.
- Same-Agent continuation across different conversations.
- Project memory that follows the repository.
- Lightweight human-readable state tracking.
- Auditable handoff between Agent sessions.
- Cross-platform use on Windows, macOS, and Linux.

### This protocol is not for

- Storing secrets, API keys, tokens, or private MCP credentials.
- Replacing Git history.
- Replacing issue trackers or full project management systems.
- Perfect distributed synchronization without conflicts.
- Long chat transcript storage.

---

## 1. Core Model

WePlaning v2.2 has five central ideas:

| Concept | Meaning |
|:--|:--|
| Project-owned memory | Memory files live in the project repo and belong to the project, not to a specific Agent. |
| Mainline | `CURRENT.md` is the current accepted project state. |
| Session branches | Each Agent conversation writes its own file under `sessions/`. |
| Auditable changes | `CHANGES.md` records who changed what, when, and from which session. |
| Human-in-the-loop | Humans can hand-edit any memory file at any time. Agents MUST NOT silently overwrite human edits. |

The minimum mental model:

```text
CURRENT.md     = accepted project mainline
sessions/*.md  = per-session branch records
THREADS.md     = session tree and mainline pointer
CHANGES.md     = append-only change ledger
TOOLS.md       = tool capability registry
```

Execution principle:

> Minimal first. `CHANGES.md` is the canonical ledger. `CURRENT.md` is accepted state. `sessions/` are work branches. Optional files are indexes or context, not new truth sources.

---

## 2. Normative Words

The protocol uses these words deliberately:

| Word | Meaning |
|:--|:--|
| MUST | Required for a compliant adapter. |
| SHOULD | Strongly recommended, but exceptions are allowed. |
| MAY | Optional. |
| MUST NOT | Forbidden. |

---

## 3. Directory Structure

All files live under `.agent-memory/` at the project root.

WePlaning is mode-based. Minimal Mode is the required compatibility layer. Standard and Full modes add context, not new truth sources.

### Minimal Mode - Required Collaboration Layer

Every WePlaning v2.2 project MUST support Minimal Mode.

```text
.agent-memory/
├── WePlaning.md          HOT   Signpost and project memory index
├── CURRENT.md            HOT   Accepted project mainline state
├── THREADS.md            HOT   Session tree and mainline pointer
├── CHANGES.md            WARM  Append-only change ledger
├── TOOLS.md              WARM  Agent tools, MCP, skills, scripts, constraints
└── sessions/             WARM  One Markdown file per Agent session
```

Minimal Mode provides:

- Mainline state.
- Session branching.
- Change audit trail.
- Tool capability trace.
- Handoff and resume.

Minimal Mode does not try to maintain long-term planning, script encyclopedias, reference libraries, or separate decision/done indexes.

### Standard Mode - Stable Project Context

Upgrade to Standard Mode when the project will continue beyond the current session, stable project identity matters, or long-form outputs need archiving.

```text
.agent-memory/
├── PROJECT.md            WARM  Project identity and stable context
└── notes/                COLD  Archived long-form outputs
```

### Full Mode - Long-Term Maintenance Layer

Upgrade to Full Mode only when the project has enough history or operational surface to justify extra files.

```text
.agent-memory/
├── DECISIONS.md          WARM  Optional index of decision entries from CHANGES.md
├── DONE.md               WARM  Optional index of completed-work entries from CHANGES.md
├── FUTURE.md             COLD  Future plans, risks, technical debt
├── REFERENCES.md         COLD  Important files, links, references
└── SCRIPTS.md            COLD  Project scripts and commands
```

Rules:

- A project MUST start in Minimal Mode unless the user explicitly requests Standard or Full Mode.
- Higher modes MUST NOT change the meaning of lower-mode files.
- `CHANGES.md` remains the canonical ledger in every mode.
- `DECISIONS.md` and `DONE.md`, when present, are optional indexes derived from or cross-referenced to `CHANGES.md`; they do not replace it.
- Optional files SHOULD be created only when their trigger conditions are met.

### Upgrade Triggers

Use hard triggers instead of vague judgment:

| Create | Trigger |
|:--|:--|
| `PROJECT.md` | Stable project identity, tech stack, or long-term role cannot fit cleanly in `WePlaning.md`. |
| `notes/` | A long-form output, audit, design plan, or report needs archiving. |
| `DECISIONS.md` | `CHANGES.md` has at least 5 `decision` entries or decisions need independent review. |
| `DONE.md` | `CHANGES.md` has at least 5 `done` entries or completed work needs date-based review. |
| `FUTURE.md` | There are at least 3 future/risk/debt items that should outlive the current session. |
| `REFERENCES.md` | There are at least 5 important references or paths that no longer fit in `WePlaning.md`. |
| `SCRIPTS.md` | There are at least 3 scripts, or scripts have cross-platform/dependency complexity. |

### Information Routing Table

Route information mechanically:

| Information | File |
|:--|:--|
| Accepted current project facts | `CURRENT.md` |
| One conversation's work notes | `sessions/<session_id>.md` |
| Parent/child session relationships | `THREADS.md` |
| Who changed what and when | `CHANGES.md` |
| Tool, MCP, skill, and script capabilities | `TOOLS.md` |
| Stable project identity | `PROJECT.md` if Standard Mode is enabled; otherwise `WePlaning.md` |
| Long-form outputs | `notes/` |
| Important decisions | `CHANGES.md`; optionally indexed in `DECISIONS.md` |
| Completed work | `CHANGES.md`; optionally indexed in `DONE.md` |
| Future plans, risks, debt | `FUTURE.md` when trigger is met; otherwise current session file |
| References and important paths | `REFERENCES.md` when trigger is met; otherwise `WePlaning.md` |
| Script usage | `SCRIPTS.md` when trigger is met; otherwise `TOOLS.md` or current session file |

### Heat Levels

| Heat | Meaning | Read Strategy |
|:--:|:--|:--|
| HOT | Needed to resume work safely | Read at session start. |
| WARM | Needed for context, audit, or closeout | Read when relevant. |
| COLD | Useful reference material | Read only when needed. |

---

## 4. File Responsibilities

### `WePlaning.md` - Signpost

`WePlaning.md` is a signpost, not a summary dump. It tells an Agent what to read next.

It SHOULD fit in one screen.

Recommended structure:

```markdown
# WePlaning
Schema version: 2.2
Last updated: <ISO datetime UTC>
Last updated by: <agent/session>

## Read First
| Need | Read | Why |
|:--|:--|:--|
| Current accepted state | CURRENT.md | Mainline |
| Session tree | THREADS.md | Parent/mainline |
| Recent changes | CHANGES.md | Audit trail |
| Tool capabilities | TOOLS.md | Available tools |

## Snapshot
| Key | Value |
|:--|:--|
| Mainline session | <session_id> |
| Last closed session | <session_id or none> |
| Active sessions | <count/list> |
| Blocker | <none or short blocker> |

## Human Concerns
- <items humans care about>

## Repeat Patterns
| Pattern | Count | Agent workload | Last seen | Suggested action |
|:--|:--|:--|:--|:--|
```

Rules:

- MUST point to `CURRENT.md`, `THREADS.md`, `CHANGES.md`, and `TOOLS.md`.
- SHOULD avoid copying content from other files.
- MUST be updated when the mainline pointer changes.

---

### `CURRENT.md` - Mainline

`CURRENT.md` records the accepted project state. It is not every Agent's scratchpad.

Recommended structure:

```markdown
# Current Mainline
Schema version: 2.2
Last updated: <ISO datetime UTC>
Mainline session: <session_id>

## Active Goal
<1-3 sentences>

## Current Understanding
<stable facts the next Agent should trust>

## Current State
<where the project stands now>

## Accepted Next Steps
1. <next action>
2. <next action>

## Open Blockers
<none or precise blockers>

## Based On
- Session: <session_id>
- Last change: <change_id>
```

Rules:

- MUST represent only accepted mainline state.
- MUST NOT be used as a live scratchpad by every Agent.
- SHOULD be updated only during Mainline Merge.
- MUST say `none` when there are no blockers.

---

### `THREADS.md` - Session Tree

`THREADS.md` records the session tree and the current mainline pointer.

Recommended structure:

```markdown
# Threads
Schema version: 2.2
Last updated: <ISO datetime UTC>

Mainline session: <session_id>
Last merged session: <session_id or none>

## Session Tree

| Session ID | Parent | Agent | OS | Role | Status | Summary |
|:--|:--|:--|:--|:--|:--|:--|
| <session_id> | root | Codex | Windows | creator | merged | Created outline |
```

Session statuses:

| Status | Meaning |
|:--|:--|
| active | Session is in progress. |
| paused | Session was closed but not merged. Work may continue later. |
| merged | Session was closed and accepted into mainline. |
| abandoned | Session was closed and intentionally not used. |

Rules:

- MUST contain exactly one `Mainline session` pointer.
- MUST record every session that modifies project or memory state.
- MUST record the parent session for each non-root session.
- SHOULD keep summaries short.

---

### `CHANGES.md` - Change Ledger

`CHANGES.md` is an append-only ledger of durable changes.

Recommended structure:

```markdown
# Changes
Schema version: 2.2

## <ISO datetime UTC> <change_id>
- Session: <session_id>
- Agent: <agent name>
- Role: <creator/editor/auditor/reviewer/implementer/other>
- Based on: <parent session or mainline session>
- Change ID: <change_id>
- Changed:
  - <what changed>
- Files touched:
  - <repo-relative path>
- Verification:
  - <commands/tests/checks or none>
- Notes:
  - <anything the next Agent should know>
```

Rules:

- MUST be append-only.
- MUST record who changed what.
- MUST use repo-relative paths for project files.
- MUST NOT record secrets.
- SHOULD include verification when work changed behavior or files.
- Each entry MUST have a unique `change_id` (format: `<ISO datetime UTC> <4-hex>`, e.g. `2026-06-01T06:45:00Z a3f9`).

---

### `TOOLS.md` - Tool Capability Registry

`TOOLS.md` records what tools each Agent session had available. It records capabilities, not secrets.

Recommended structure:

```markdown
# Tools
Schema version: 2.2
Last updated: <ISO datetime UTC>

## Agent Sessions

| Session ID | Agent | OS | Adapter | Tools | MCP | Skills | Notes |
|:--|:--|:--|:--|:--|:--|:--|:--|
| <session_id> | Codex | Windows | codex | shell, apply_patch | unavailable | openai-docs | Created outline |

## MCP Servers

| Name | Session ID | Capability | Scope | Config Source | Secret Stored |
|:--|:--|:--|:--|:--|:--|
| <name> | <session_id> | <capability> | project/local/global | <path or unknown> | no |

## Skills

| Skill | Session ID | Version | Purpose | Location | Trigger |
|:--|:--|:--|:--|:--|:--|

## Scripts

| Script | Purpose | OS | Inputs | Outputs | How to run | Owner |
|:--|:--|:--|:--|:--|:--|:--|

## Constraints

- Secrets, API keys, tokens, private MCP credentials, cookies, and passwords MUST NOT be recorded.
- Tool capability SHOULD be recorded even when exact configuration is private.
- If a tool is not available, write `unavailable`.
- If a tool's availability is unknown, write `unknown`.
- Local absolute paths MUST be marked `local-only` and include OS when necessary.
```

Rules:

- MUST be updated when a session uses non-obvious tools, MCP servers, skills, or scripts.
- MUST NOT contain secrets.
- SHOULD explain important tool limitations.

---

### `sessions/<session_id>.md` - Per-Session Branch

Each Agent conversation that changes project or memory state gets one session file.

Recommended session ID:

```text
<UTC timestamp>-<agent>-<os>-<role>-<short id>
```

Example:

```text
20260601T063000Z-codex-win-editor-a3f9
```

Recommended structure:

```markdown
# Session <session_id>

Schema version: 2.2
Session ID: <session_id>
Agent: <agent name>
Adapter: <adapter name or unknown>
OS: <Windows/macOS/Linux/unknown>
Role: <creator/editor/auditor/reviewer/implementer/other>
Parent session: <session_id or root>
Status: active
Started: <ISO datetime UTC>
Closed: <ISO datetime UTC or none>

## Goal
<what this session is trying to do>

## Context Read
- <files read>

## Work Notes
- <short durable notes, not full chat transcript>

## Files Touched
- <repo-relative path>

## Decisions
- <session-local decisions>

## Result
<pending / summary>

## Exact Next Step
<precise next action or none>
```

Rules:

- MUST have a unique Session ID.
- MUST have a parent session, except the first root session.
- MUST start as `active`.
- MUST be closed as `paused`, `merged`, or `abandoned`.
- SHOULD record only durable notes, not full conversation logs.

---

### Optional WARM/COLD Files

The following files keep their v2.1 purpose when their mode or trigger is enabled:

| File | Purpose | Rule |
|:--|:--|:--|
| `PROJECT.md` | Stable project identity | Standard Mode. Keep concise. |
| `notes/` | Archived long-form outputs | Standard Mode. Create only when archiving. |
| `DECISIONS.md` | Decision index | Full Mode. Append-only index; `CHANGES.md` remains canonical. |
| `DONE.md` | Completed work index | Full Mode. Append-only index; `CHANGES.md` remains canonical. |
| `FUTURE.md` | Plans, risks, debt | Full Mode. Update when new durable risks/todos appear. |
| `REFERENCES.md` | Important paths and external references | Full Mode. Use repo-relative paths where possible. |
| `SCRIPTS.md` | Script usage | Full Mode. Cross-reference `TOOLS.md` when scripts are Agent-specific. |

---

## 5. Session Lifecycle

### 5.1 Session Start

When an Agent starts work on a project, it SHOULD:

1. Read `WePlaning.md`.
2. Read `CURRENT.md`.
3. Read `THREADS.md`.
4. Read recent entries in `CHANGES.md`.
5. Read `TOOLS.md` if tool capability matters.
6. Create a new `sessions/<session_id>.md` if the session will change project or memory state.
7. Add the new session to `THREADS.md` as `active`.

Parent session rule:

- If continuing the accepted mainline, parent SHOULD be the current `Mainline session`.
- If auditing or branching from another session, parent SHOULD be that specific session.
- If no previous session exists, parent MUST be `root`.

---

### 5.2 During Work

During work, an Agent SHOULD write durable notes into its own session file.

Rules:

- MUST NOT use `CURRENT.md` as scratch space.
- SHOULD update `sessions/<session_id>.md` when important context changes.
- SHOULD record important decisions as `decision` entries in `CHANGES.md`.
- MAY also index decisions in `DECISIONS.md` when Full Mode is enabled.
- SHOULD append durable file changes to `CHANGES.md` at closeout, not after every tiny edit.

---

### 5.3 When to Close a Session

A session close means preserving the state of this conversation. It does not always mean the work is complete.

A session MUST be closed when one of these happens:

- The user asks to stop, summarize, handoff, close, or switch Agent.
- The current goal reaches a stable checkpoint.
- The Agent made a durable decision.
- The Agent changed project files or memory files.
- The Agent cannot continue and needs to preserve the exact next step.
- The conversation is likely to be resumed by another Agent or another session.

A session MAY stay active when the work is continuous and no durable project state has changed.

Closeout MUST update:

- The session file status.
- `THREADS.md`.
- `CHANGES.md` if durable changes occurred.
- `TOOLS.md` if notable tools were used.
- `DECISIONS.md` and `DONE.md` only if Full Mode is enabled and relevant.

---

### 5.4 When to Merge to Mainline

Mainline Merge means the session result becomes the accepted project state.

A session SHOULD update `CURRENT.md` only when:

- Its result is now the best known project state.
- Its next step should become the project's next step.
- Its decisions or findings should affect future work.
- It supersedes the previous mainline session.

A session SHOULD NOT update `CURRENT.md` when:

- It was exploratory and not adopted.
- It failed or was abandoned.
- It is only a side note with no impact on future project work.
- It conflicts with the mainline and has not been resolved.

#### Rebase Before Merge

Before merging, an Agent MUST check whether its parent session is still the current mainline (from `THREADS.md`).

If the parent is no longer the mainline:

- The Agent SHOULD diff its own changes against the parent.
- The Agent SHOULD re-apply those changes onto the current mainline.
- If re-application fails, the Agent MUST record a conflict in `CHANGES.md` and mark the session `paused` with a note explaining the conflict.
- The Agent MUST NOT silently overwrite changes made by the newer mainline.

Merge update checklist:

```markdown
- [ ] Session status changed to `merged`
- [ ] THREADS.md Mainline session updated
- [ ] CURRENT.md updated
- [ ] CHANGES.md appended
- [ ] DECISIONS.md indexed if Full Mode is enabled and decisions were made
- [ ] DONE.md indexed if Full Mode is enabled and work was completed
- [ ] WePlaning.md snapshot refreshed
```

---

### 5.5 Session Resume

A `paused` session MAY be resumed by a later Agent session. Resuming does not reopen the original session file — it creates a new session that continues the work.

Resume checklist:

1. Read the paused session file, especially `Exact Next Step` and `Work Notes`.
2. Read `CURRENT.md` and `THREADS.md` for any mainline changes since the pause.
3. Create a new session file with `Parent session` set to the paused session ID.
4. In the new session `Context Read`, reference the paused session.
5. Record in `CHANGES.md`:

```markdown
## <ISO datetime UTC> <change_id>
- Session: <new_session_id>
- Agent: <agent>
- Resume:
  - Continued from: <paused_session_id>
  - Reason: <why resuming>
```

If the paused session is no longer relevant (superseded by mainline changes), the Agent MAY mark it `abandoned` instead.

---

## 6. Handoff Packet

When the user says `handoff`, `交接`, `总结`, or `收尾`, the Agent SHOULD output a concise handoff packet in chat.

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

Rules:

- If a field is uncertain, write `unknown`.
- MUST NOT invent missing facts.
- SHOULD NOT create a separate handoff file unless the user asks.

---

## 7. Drift Check

Drift Check tests whether memory files still match project reality.

At session start or resume, an Agent SHOULD check:

1. `CURRENT.md` mainline session exists in `THREADS.md`.
2. The mainline session file exists under `sessions/`.
3. Recent project file changes are reflected in `CHANGES.md`; `DONE.md` may provide an optional Full Mode index.
4. Paths in `REFERENCES.md` and `SCRIPTS.md` still exist.
5. Tool assumptions in `TOOLS.md` are still true enough for this session.

If drift is minor, the Agent MAY fix it and record the fix in `CHANGES.md`.

If drift is major, the Agent SHOULD mark the issue clearly in the current session file:

```markdown
## Drift
- DRIFT: <specific mismatch>
```

If the memory is unusable, write:

```markdown
## Drift
- STALE: project memory is too stale to trust without human review.
```

---

## 8. Schema Health Check

Schema Health Check verifies that memory files still follow the protocol structure. Unlike Drift Check (which compares memory to project reality), this checks internal consistency of the memory files themselves.

At session start or mainline merge, an Agent SHOULD verify:

1. All Minimal Mode files exist and have a valid `Schema version: 2.2` header, except the `sessions/` directory itself.
2. Files enabled by Standard or Full Mode SHOULD have a valid `Schema version: 2.2` header.
3. Session files under `sessions/` SHOULD have a valid `Schema version: 2.2` header.
4. Archived notes under `notes/` MAY omit schema headers.
5. The `THREADS.md` mainline session file exists under `sessions/`.
6. Every session file referenced in `THREADS.md` exists under `sessions/`.
7. Cross-file references (e.g. `Based On` in `CURRENT.md`, `Parent session` in session files, `change_id` references) point to real entries.
8. Append-only files that exist (`CHANGES.md`, and optionally `DECISIONS.md` / `DONE.md`) have no obvious structural corruption (e.g. missing timestamps, truncated entries).

If issues are minor (e.g. a missing header field), the Agent MAY fix them and record the fix in `CHANGES.md`.

If issues are structural (e.g. a missing mainline session file, broken references), the Agent SHOULD report them to the human and record them in the current session file under `## Drift`.

---

## 9. Cross-Platform Path Rules

WePlaning is intended for Windows, macOS, and Linux.

Rules:

- Project files MUST be recorded as repo-relative paths.
- Path separators SHOULD use `/`.
- Local absolute paths MUST be marked `local-only`.
- Windows-only paths MUST NOT be used as canonical project paths.
- Generated paths SHOULD include enough context to be understood on another OS.

Examples:

```text
Good: src/app/main.ts
Good: .agent-memory/sessions/20260601T063000Z-codex-win-editor-a3f9.md
Local-only: C:/Users/name/local-tool/config.json
Bad as canonical path: C:\Users\name\project\src\app.ts
```

---

## 10. Conflict Handling

WePlaning stays lightweight, but it still needs conflict rules.

Rules:

- Append-only files may be appended after re-reading the latest version.
- Summary files such as `CURRENT.md`, `THREADS.md`, `TOOLS.md`, and `WePlaning.md` SHOULD be re-read before writing.
- If a file changed since the Agent last read it, the Agent SHOULD merge manually or record a conflict.
- Agents MUST NOT silently overwrite human edits.

Recommended conflict entry in `CHANGES.md`:

```markdown
## <ISO datetime UTC>
- Session: <session_id>
- Agent: <agent>
- Conflict:
  - File: <repo-relative path>
  - Reason: Changed since last read
  - Resolution: <merged / deferred / human review needed>
```

---

## 11. Bootstrap

To initialize WePlaning in a project:

1. Create `.agent-memory/`.
2. Start in Minimal Mode unless the user explicitly requests Standard or Full Mode.
3. Create the Minimal Mode files listed in Section 3.
4. Create the first root session.
5. Set `THREADS.md` mainline session to the root session.
6. Write initial `CURRENT.md`.
7. Record the initialization in `CHANGES.md`.
8. Record initial tools in `TOOLS.md`.
9. Create optional files only when their mode or trigger is enabled.

The first session SHOULD use role `creator`.

---

## 12. Answer Archiving

Important long-form outputs such as design plans, reviews, migration plans, and analysis reports MAY be archived under `notes/`.

Recommended format:

```markdown
# <Title>
Archived: <ISO datetime UTC>
Session: <session_id>
Source: <short context>

<content>
```

After archiving, update `REFERENCES.md` or `CHANGES.md` as appropriate.

---

## 13. Repeat Pattern to Skill

When the same workflow appears at least three times and the Agent performs most of the work, the Agent SHOULD suggest turning it into a Skill or script.

Record candidates in `WePlaning.md`:

```markdown
| Pattern | Count | Agent workload | Last seen | Suggested action |
|:--|:--|:--|:--|:--|
| Release checklist update | 3 | 90% | 2026-06-01 | create-skill |
```

---

## 14. Adapter Minimum Implementation

A minimal WePlaning v2.2 adapter MUST be able to:

1. Read Markdown files under `.agent-memory/`.
2. Create a session file under `sessions/`.
3. Read and update `THREADS.md`.
4. Append to `CHANGES.md`.
5. Read and update `CURRENT.md` during mainline merge.
6. Record tool capabilities in `TOOLS.md` without secrets.
7. Generate a handoff packet.
8. Operate correctly in Minimal Mode without requiring optional files.

Recommended adapter actions:

| Action | Meaning |
|:--|:--|
| `bootstrap` | Create `.agent-memory/` structure. |
| `start-session` | Create session and register it in `THREADS.md`. |
| `close-session` | Close session as `paused`, `merged`, or `abandoned`. |
| `merge-mainline` | Update `CURRENT.md` and mainline pointer. |
| `handoff` | Output handoff packet. |
| `drift-check` | Check memory against project reality. |

Tool-specific triggers such as `/skill ...` belong in adapter documentation, not the core protocol.

---

## 15. Safety Rules

| Rule | Description |
|:--|:--|
| Append history | `CHANGES.md` is append-only. `DECISIONS.md` and `DONE.md`, when enabled, are append-only indexes. |
| No silent overwrite | Agents must not silently overwrite human edits. |
| No secrets | Never write credentials, tokens, private MCP configs, cookies, or passwords. |
| Be honest | Unknown information is `unknown`; unavailable tools are `unavailable`. |
| Keep it short | Memory files are durable signposts, not chat logs. `WePlaning.md` and `CURRENT.md` SHOULD each fit in one screen. |
| Respect mainline | Only accepted state belongs in `CURRENT.md`. |
| Preserve branches | Session files remain even when paused or abandoned. |

---

## 16. Example Flow

Scenario:

1. Agent1 creates a WePlaning project and outline.
2. Agent2 audits the protocol.
3. Agent1 opens a new conversation and edits based on the audit.

Result:

```text
sessions/20260601T040000Z-codex-win-creator-a001.md
  parent: root
  status: merged

sessions/20260601T050000Z-claude-mac-auditor-b001.md
  parent: 20260601T040000Z-codex-win-creator-a001
  status: merged or paused

sessions/20260601T063000Z-codex-win-editor-c001.md
  parent: 20260601T050000Z-claude-mac-auditor-b001
  status: active, then merged
```

`THREADS.md` keeps the tree:

```markdown
Mainline session: 20260601T063000Z-codex-win-editor-c001

| Session ID | Parent | Agent | OS | Role | Status | Summary |
|:--|:--|:--|:--|:--|:--|:--|
| 20260601T040000Z-codex-win-creator-a001 | root | Codex | Windows | creator | merged | Created outline |
| 20260601T050000Z-claude-mac-auditor-b001 | 20260601T040000Z-codex-win-creator-a001 | Claude | macOS | auditor | merged | Audited protocol |
| 20260601T063000Z-codex-win-editor-c001 | 20260601T050000Z-claude-mac-auditor-b001 | Codex | Windows | editor | merged | Edited v2.2 |
```

`CURRENT.md` reflects only the accepted result.

`CHANGES.md` records who changed what.

`TOOLS.md` records which tools each session had available.

---

## Appendix A - v2.1 to v2.2 Changes

Major changes from v2.1:

- Added project collaboration model.
- Added per-session branch files under `sessions/`.
- Added `THREADS.md` for mainline and session tree.
- Added `CHANGES.md` for auditable change history.
- Added `TOOLS.md` for tool capability registry.
- Clarified Session Close vs Mainline Merge.
- Added cross-platform path rules.
- Added lightweight conflict handling.
- Moved tool-specific triggers out of core protocol.

---

> The protocol stays lightweight by using Markdown, but it becomes reliable by separating mainline, session branches, changes, and tools.

---

## Appendix B - Migrating from v2.1 to v2.2

When upgrading a v2.1 project to v2.2, follow this checklist:

1. **Create new directories**
   - `mkdir .agent-memory/sessions/`
   - `mkdir .agent-memory/notes/` only if upgrading directly to Standard or Full Mode, or if archived notes already exist.

2. **Create `THREADS.md`**
   - Set `Mainline session` to a synthetic root session (e.g. `00000000T000000Z-migration-sys-root-0000`).
   - Create a corresponding root session file under `sessions/` with `Status: merged` and `Role: creator`.

3. **Create `CHANGES.md`**
   - Optionally seed with recent entries from `DONE.md` as a historical baseline.
   - Add a migration entry recording the v2.1 → v2.2 upgrade.

4. **Create `TOOLS.md`**
   - Populate from known tool usage in past sessions. Write `unknown` for sessions where tool availability is not certain.

5. **Clean up `CURRENT.md`**
   - If `CURRENT.md` contains scratch-pad notes or in-progress work, move that content to a new session file under `sessions/`.
   - Strip `CURRENT.md` down to accepted mainline state only.
   - Update `Based On` to reference the migration change.

6. **Update headers**
   - Change `Schema version: 2.1` to `Schema version: 2.2` in every enabled memory file for the selected mode.
   - Ensure migration-created session files under `sessions/` declare `Schema version: 2.2`.
   - Archived notes under `notes/` may omit schema headers.
   - Update `WePlaning.md` structure to match the v2.2 signpost format.

7. **Validate**
   - Run Drift Check (Section 7).
   - Run Schema Health Check (Section 8).
   - Record any issues found in `CHANGES.md`.
