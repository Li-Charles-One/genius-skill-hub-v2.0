---
name: genius-skill-creator
description: Create, repair, validate, evaluate, optimize, standardize, or port Codex/Claude-style skills and Skill Hub packages. Use when users want a new skill, a reusable skill template, metadata/frontmatter fixes, openai.yaml or agent adapter repair, eval prompts, trigger tuning, package audits, multi-Agent skill migration including Trae Solo and CherryStudio, or cross-platform command standards.
---

# Genius Skill Creator

Use this skill to turn skill ideas or existing skill folders into valid, useful, tested skill packages. It is the template skill for Genius Skill Hub optimization.

Core modes:

- **System builder:** scaffold folders, write valid `SKILL.md`, generate `agents/openai.yaml`, add scripts/references/assets, and run validation.
- **Evaluation improver:** create realistic test prompts, compare behavior, review outputs, improve instructions, and optimize trigger descriptions.
- **Package optimizer:** reshape requirements, thin the entrypoint, move detailed material into modules, add multi-Agent adapters, and define validation/output gates.
- **Adapter standardizer:** map shared skill behavior to Codex, Reasonix, Trae Solo, CherryStudio, or another runtime without inventing unsupported tools.

Do not treat a skill as finished just because it reads well. A finished skill should be valid, triggerable, lean, resource-aware, and tested enough for its risk.

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
- `agents/openai.yaml` if present.
- `agents/reasonix.yaml` or other runtime adapters if present.
- `references/`, `scripts/`, `assets/`, and `evals/`.
- Any local validator, target runtime docs, or user-provided examples.

## Template-First Workflow

For Genius Skill Hub work, use `references/skill-optimization-template.md` as the standard. Do not rewrite every skill at once. Build or repair one skill package, validate it, then reuse the pattern for the next skill.

When optimizing an existing skill:

1. Capture its purpose, trigger scope, non-goals, expected outputs, dependencies, and validation gates.
2. Keep `SKILL.md` as a thin entrypoint: trigger, mode selection, workflow, resource map, and final response contract.
3. Move detailed reusable guidance into `references/`.
4. Keep deterministic or repetitive operations in `scripts/`.
5. Keep runtime-specific metadata in `agents/`; never mix Reasonix or other runtime tool lists into Codex frontmatter.
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
- Put product/runtime metadata in `agents/<runtime>.yaml`.
- For multi-Agent skills, keep shared instructions in `SKILL.md` and `references/`, and keep tool/model/runtime specifics in adapters.
- For Trae, deploy as a native Trae Skill under `.trae/skills/` (project) or `~/.trae-cn/skills/` (global) — Trae's SKILL.md format is compatible with Codex format.
- For commands and scripts, consider Windows, macOS, and Linux. Provide OS-specific command variants when syntax differs.
- Avoid extra docs such as `README.md`, `CHANGELOG.md`, or install guides unless the target ecosystem explicitly requires them.
- Validate with the best available validator before delivery.

For Codex-style skills, use `scripts/quick_validate.py` and `references/openai_yaml.md`. For multi-Agent skills, also read `references/agent-adapter-standard.md`. For script or command guidance, read `references/cross-platform-command-standard.md`.

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
   - `agents/` for runtime-specific metadata and adapters.
3. Scaffold or patch:
   - Use `scripts/init_skill.py` for new Codex-style skills when useful.
   - Use direct patching for small repairs.
4. Generate or update `agents/openai.yaml` when the target runtime supports it.
5. Add `agents/reasonix.yaml` or another adapter when the skill should work outside Codex.
6. Add cross-platform command guidance when scripts, shell snippets, or install commands are part of the skill.
7. Validate.
8. Test with realistic prompts when the skill has meaningful behavioral risk.

## Repair Workflow

Check in this order:

1. `SKILL.md` exists and starts with valid frontmatter.
2. Frontmatter name matches folder name unless a compatibility reason is recorded.
3. No duplicate skill names in the target hub.
4. Description is specific, trigger-focused, and under validator limits.
5. `agents/openai.yaml` has a 25-64 character `short_description` and a `default_prompt` mentioning `$skill-name`.
6. Runtime adapters are under `agents/` and parse as YAML.
7. Resource files are directly discoverable from `SKILL.md`.
8. Commands and scripts avoid OS-specific assumptions unless the skill is explicitly platform-specific.
9. Scripts compile or run a representative help/test command.
10. Placeholder text is intentional, not unfinished skill content.

Use `references/openai_yaml.md` for UI metadata constraints.

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
- multi-Agent status: which adapters exist and which are still missing;
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

- `scripts/init_skill.py`: scaffold Codex-style skills.
- `scripts/quick_validate.py`: validate core `SKILL.md` structure.
- `scripts/generate_openai_yaml.py`: generate Codex UI metadata.
- `scripts/validate_evals.py`: validate eval definitions and optionally execute assertions against result JSON.
- `references/skill-optimization-template.md`: package template for reshaping and optimizing skills.
- `references/agent-adapter-standard.md`: multi-Agent adapter conventions.
- `references/cross-platform-command-standard.md`: Windows/macOS/Linux command and script conventions.
- `references/openai_yaml.md`: `agents/openai.yaml` constraints.
- `references/eval-workflow.md`: practical eval and trigger optimization workflow.
- `references/consolidation-workflow.md`: merge/consolidate related skills.
- `evals/evals.json`: reusable eval prompts for creation, optimization, porting, trigger tuning, and audits.

## Final Response

Use the Output Standard above. If no files changed, say that plainly and report only the audit or plan.
