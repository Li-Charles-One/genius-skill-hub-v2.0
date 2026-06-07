---
name: genius-skill-creator
description: Create, repair, validate, evaluate, optimize, standardize, or port SKILL.md skill packages. Use for SKILL.md/frontmatter fixes, Skill Hub audits, platform adapter generation, eval/trigger tuning, scaffolding, or cross-agent skill migration.
---

# Genius Skill Creator

Use this skill to turn skill ideas or existing skill folders into valid, useful, tested skill packages. It is the template skill for Genius Skill Hub optimization.

Core modes:

- **System builder:** scaffold folders, write valid `SKILL.md`, generate platform adapters in `agents/`, add scripts/references/assets, and run validation.
- **Evaluation improver:** create realistic test prompts, compare behavior, review outputs, improve instructions, and optimize trigger descriptions.
- **Package optimizer:** reshape requirements, thin the entrypoint, move detailed material into modules, add platform adapters, and define validation/output gates.
- **Adapter standardizer:** map shared skill behavior to any runtime (Reasonix, Codex, Cursor, Claude Code, Trae, CherryStudio, etc.) without inventing unsupported tools. Every adapter answers: which tools are available, what model to use, how to invoke sub-skills, where to install.

Do not treat a skill as finished just because it reads well. A finished skill should be valid, triggerable, lean, resource-aware, and tested enough for its risk.

## BEFORE ANYTHING ELSE: Identify Your Runtime (Every Agent Must Do This)

This skill describes actions in platform-neutral language. Before executing any instruction, you MUST determine which AI agent runtime you are running on, then map the skill's actions to YOUR actual tools.

### Step 1: Detect your runtime

Check your available tools against these fingerprints. Match the FIRST row where every tool in the "Signature tools" column is available to you:

| Runtime | Signature tools | How you invoke sub-skills | Install path |
|---|---|---|---|
| **Reasonix** | `read_file`, `grep`, `glob`, `ls`, `write_file`, `bash`, `task`, `edit_file` | `run_skill({ name: "<skill>", arguments: "..." })` | `~/.reasonix/skills/<name>/` |
| **Codex** | `read_file`, `search_content`, `search_files`, `directory_tree`, `write_file`, `run_command` | `/skill-name` or `$skill-name` in prompt | `.agents/skills/<name>/` |
| **Cursor** | `search_file`, `search_content`, `read_file`, `write`, `execute_command`, `editor_edit_file` | `/<skill-name>` in chat | `.cursor/skills/<name>/` |
| **Claude Code** | `Read`, `Write`, `Edit`, `Grep`, `Glob`, `Bash`, `Task` | `/skill-name` in chat | `.claude/skills/<name>/` or `~/.claude/skills/<name>/` |

If none match, or you're unsure, ask the user: *"Which AI agent are you currently running on? (Reasonix / Codex / Cursor / Claude Code / other)"* Then use the answer to look up the right mapping.

### Step 2: Map this skill's actions to YOUR tools

Every action described in this skill uses neutral language: "read a file," "search code," "run a shell command," "spawn a sub-agent." Translate each one to YOUR runtime's exact tool name. Examples:

| Neutral action | Reasonix | Codex |
|---|---|---|
| read a file | `read_file` | `read_file` |
| search code for a pattern | `grep` | `search_content` |
| list files in a directory | `ls` or `glob` | `directory_tree` or `search_files` |
| run a shell command | `bash` | `run_command` |
| spawn a sub-agent for a task | `task` or `run_skill(...)` | dispatch via prompt instruction |
| validate a YAML/JSON file | `python scripts/validate.py` via `bash` | `python scripts/validate.py` via `run_command` |

### Step 3: Map sub-skill invocations

When this skill says "invoke the writing-plans skill" or "run the brainstorm skill," translate to YOUR runtime's invocation method:

| Runtime | How to invoke writing-plans |
|---|---|
| Reasonix | `run_skill({ name: "writing-plans", arguments: "<spec path>" })` |
| Codex | `/writing-plans <spec path>` or mention in prompt |
| Cursor | `/writing-plans <spec path>` |
| Claude Code | `/writing-plans <spec path>` |

### Step 4: Map file paths

When this skill references a file like `references/design-template.md`, compute the full path based on YOUR runtime's skill location and the current skill's install path. The path is relative to the directory containing THIS `SKILL.md`.

### If You Can't Map Something

Mark it as `<!-- unverified -->` in your reasoning and proceed with your best available tool. At the end of your response, report: "Platform mapping: <runtime>. Unverified actions: <list>." This makes the gap visible instead of silently failing.

## Start Here

Classify the user request:

- **Create:** user wants a new skill.
- **Repair:** a skill fails validation, has bad metadata, duplicate names, broken resources, or stale platform assumptions.
- **Merge:** user wants to combine skills or create a higher-level creator skill.
- **Audit:** user wants a folder of skills checked.
- **Evaluate:** user wants test prompts, benchmark-style comparison, or trigger optimization.
- **Port:** user wants a skill adapted to another agent/runtime.
- **Standardize:** user wants a skill or hub to match a reusable template.

Then inspect the smallest useful evidence:

- Existing `SKILL.md`.
- `agents/` directory — each `.yaml` file is one platform's adapter.
- `references/`, `scripts/`, `assets/`, and `evals/`.
- Any local validator, target runtime docs, or user-provided examples.

## Architecture Principle: SKILL.md Is the Universal Standard

`SKILL.md` is a **shared instruction file** that any AI agent can load. It belongs to no single platform. Every platform adapter (`agents/<runtime>.yaml`) is equal — none is the "primary" or "standard."

### The contract

- **`SKILL.md`**: shared logic. No platform tool names, no platform-specific invocation syntax, no assumptions about which agent reads it. References to sub-skills use plain names, not tool-call wrappers.
- **`references/`**: detailed guidance loaded by SKILL.md. Same platform-independence rule.
- **`agents/<runtime>.yaml`**: one file per platform. Contains ONLY what that specific runtime needs: tool allowlist, model preference, sub-agent invocation method, install path conventions.

### How platform adapters work

Every `agents/<runtime>.yaml` answers these questions for its runtime:

| Question | Example (Reasonix) | Example (Codex) |
|---|---|---|
| Which tools map to SKILL.md actions? | `read_file`, `grep`, `glob`, `write_file`, `bash`, `task` | `read_file`, `search_content`, `search_files`, `directory_tree`, `write_file`, `run_command` |
| How to invoke a sub-skill? | `run_skill({ name: "writing-plans" })` | `/writing-plans` |
| Which model to use? | `deepseek-v4-pro` | (Codex infers from YAML metadata) |
| Where to install? | `~/.reasonix/skills/<name>/` | Project-local: `.agents/skills/` |
| How does the agent read the skill? | `shared_instructions` in YAML | Auto-discovers `SKILL.md` in `.agents/skills/` |

**The adapter author's job:** read the runtime's official docs, identify the tool names that match SKILL.md's actions, and write ONLY those mappings. Never guess. Never copy another adapter's tool names.

## Template-First Workflow

For Genius Skill Hub work, use `references/skill-optimization-template.md` as the standard. Do not rewrite every skill at once. Build or repair one skill package, validate it, then reuse the pattern for the next skill.

When optimizing an existing skill:

1. Capture its purpose, trigger scope, non-goals, expected outputs, dependencies, and validation gates.
2. Keep `SKILL.md` as a thin entrypoint: trigger, mode selection, workflow, resource map, and final response contract.
3. Move detailed reusable guidance into `references/`.
4. Keep deterministic or repetitive operations in `scripts/`.
5. Keep runtime-specific metadata in `agents/`; never mix one platform's tool names or invocation syntax into `SKILL.md` or `references/`.
6. Add or update `evals/` when trigger behavior, output quality, or regression risk matters.
7. Validate locally before syncing the complete package to a hub.

## Non-Negotiables

Every generated or repaired skill must:

- Include `SKILL.md`.
- Use YAML frontmatter with `name` and `description`.
- Use lowercase hyphen-case names.
- Put trigger conditions in `description`, not only in the body.
- Keep `SKILL.md` concise; move detailed material into directly linked `references/`.
- Include scripts only when they add deterministic value or avoid repeated fragile code.
- Include assets only when they are used in outputs.
- Put platform-specific metadata in `agents/<runtime>.yaml`. One file per supported runtime.
- For multi-agent skills: shared instructions in `SKILL.md` + `references/`; tool/model/runtime specifics in `agents/<runtime>.yaml`. Every adapter is equal — none is the "default" or "primary."
- For commands and scripts, consider Windows, macOS, and Linux. Provide OS-specific command variants when syntax differs.
- Avoid extra docs such as `README.md`, `CHANGELOG.md`, or install guides unless the target ecosystem explicitly requires them.
- Validate with the best available validator before delivery.

For validation, use `scripts/quick_validate.py` (structural checks) and `references/openai_yaml.md` (Codex adapter format constraints). For multi-agent adapter design, read `references/agent-adapter-standard.md`. For script compatibility, read `references/cross-platform-command-standard.md`.

## Creation Workflow

1. Capture intent:
   - What should the skill enable?
   - When should it trigger?
   - What should it not handle?
   - What output should it produce?
   - What tools, scripts, files, or APIs does it depend on?
2. Choose resources:
   - `references/` for detailed guidance loaded as needed.
   - `scripts/` for deterministic or repetitive operations.
   - `assets/` for output templates, icons, fonts, images, or boilerplate.
   - `evals/` for test prompts and expected outcomes.
   - `agents/` for platform-specific adapter files.
3. Scaffold or patch:
   - Use `scripts/init_skill.py` for new skills when useful.
   - Use `scripts/init_skill.py --adapters <runtime1>,<runtime2>` (e.g. `--adapters openai,reasonix`) when the new skill needs starter adapter templates for specific runtimes.
   - Use direct patching for small repairs.
4. Generate adapter files for each target runtime. Each adapter maps the skill's shared actions to that runtime's specific tools and conventions.
5. Add cross-platform command guidance when scripts, shell snippets, or install commands are part of the skill.
6. Validate.
7. Test with realistic prompts when the skill has meaningful behavioral risk.

## Platform Adapter Design (The Method)

When adding a new runtime adapter:

1. **Research the runtime's actual capabilities.** Check official docs or the latest GitHub source. Never assume "it probably has a tool like X."
2. **Map shared actions to real tools.** For each action the skill needs (read files, search code, run shell, spawn sub-agent), find the runtime's exact tool name. If the runtime lacks a capability, mark the adapter field as `unsupported` and note the fallback.
3. **Write the adapter file.** Put it in `agents/<runtime>.yaml`. Follow the adapter conventions in `references/agent-adapter-standard.md`.
4. **Document the install path.** Where does this runtime look for skills? Write it in the adapter so the install step needs no guesswork.
5. **Test.** Install the skill into a project using that runtime. Verify the skill triggers correctly and all tool calls resolve.

### Common platform install paths (reference)

| Runtime | Config dir | Skill location |
|---|---|---|
| Reasonix | `~/.reasonix/` | `skills/<name>/SKILL.md` |
| Codex | Project: `.agents/` | `skills/<name>/SKILL.md` |
| Cursor | Project: `.cursor/` | `skills/<name>/SKILL.md` |
| Claude Code | Project: `.claude/` or `~/.claude/` | `skills/<name>/SKILL.md` |
| Gemini CLI | Project: `.gemini/` | `skills/<name>/SKILL.md` |
| Trae CN | `~/.trae-cn/` | `skills/<name>/SKILL.md` |

Check each runtime's latest docs — these paths change.

## Repair Workflow

Check in this order:

1. `SKILL.md` exists and starts with valid frontmatter.
2. Frontmatter name matches folder name unless a compatibility reason is recorded.
3. No duplicate skill names in the target hub.
4. Description is specific, trigger-focused, and under validator limits.
5. At least one `agents/<runtime>.yaml` exists if the skill targets a specific platform. Adaptable skills may ship with multiple adapters or none (for skills with zero platform dependencies).
6. Platform adapters under `agents/` parse as valid YAML and use the runtime's documented tool names.
7. No platform-specific tool names or invocation syntax leak into `SKILL.md` or `references/`.
8. Resource files are directly discoverable from `SKILL.md`.
9. Commands and scripts avoid OS-specific assumptions unless the skill is explicitly platform-specific.
10. Scripts compile or run a representative help/test command.
11. Placeholder text is intentional, not unfinished skill content.

For Codex adapter format constraints, see `references/openai_yaml.md`.

## Evaluation Workflow

Use evals when success can be checked or when trigger behavior matters.

1. Draft realistic user prompts.
2. Include both should-trigger and should-not-trigger cases for description work.
3. Save prompts to `evals/evals.json` when creating a reusable benchmark.
4. Run skill and baseline comparisons when subagents or separate runs are available.
5. Review outputs for correctness, unnecessary context load, missing resource use, brittle instructions, trigger false positives, and overfitting.
6. Improve the skill, then rerun the same prompts.

When full automation is unavailable, perform a manual eval pass and record findings in the final response.

Read `references/eval-workflow.md` before designing a larger benchmark.

## Output Standard

When delivering skill work, report:

- requirement summary: what the skill is for, when it triggers, and what it does not handle;
- architecture changes: entrypoint, references, scripts, assets, evals, and agents;
- validation: exact checks run and pass/fail status;
- platform status: which adapters exist, which are missing, and which have unverified mappings;
- remaining risks or follow-up work;
- package location.

## Description Optimization

The `description` field is the primary trigger surface. Improve it by:

- naming the task type;
- listing concrete trigger contexts;
- naming important file types, tools, or workflows;
- saying when not to use the skill;
- avoiding vague claims like "helps with productivity";
- keeping platform-specific assumptions out unless the skill is platform-specific.

For high-stakes trigger tuning, create roughly half should-trigger prompts and half should-not-trigger prompts.

## Porting And Evidence

When adapting a skill to another agent/runtime:

- Detect local commands, tool names, folder conventions, and script support when possible.
- For open-source runtimes, check official docs or the latest official GitHub source.
- Mark unknown capabilities as `unverified`.
- Do not copy another agent's tool names without evidence.

Record important evidence in a reference file when it will affect future maintenance.

## Resource Map

- `scripts/init_skill.py`: scaffold skill folders and optional platform adapter templates.
- `scripts/quick_validate.py`: validate core `SKILL.md` structure.
- `scripts/generate_openai_yaml.py`: generate `agents/openai.yaml` for Codex-compatible runtimes.
- `scripts/validate_evals.py`: validate eval definitions and optionally execute assertions against result JSON.
- `references/skill-optimization-template.md`: package template for reshaping and optimizing skills.
- `references/agent-adapter-standard.md`: platform adapter conventions.
- `references/cross-platform-command-standard.md`: Windows/macOS/Linux command and script conventions.
- `references/openai_yaml.md`: `agents/openai.yaml` format constraints.
- `references/eval-workflow.md`: practical eval and trigger optimization workflow.
- `references/consolidation-workflow.md`: merge/consolidate related skills.
- `evals/evals.json`: reusable eval prompts for creation, optimization, porting, trigger tuning, and audits.

## Final Response

Use the Output Standard above. If no files changed, say that plainly and report only the audit or plan.
