---
name: genius-skill-creator
description: Create, repair, validate, evaluate, and optimize Codex/Claude-style skills by combining system skill scaffolding with eval-driven iteration. Use when users want to make a new skill, merge or upgrade existing skills, fix skill metadata/frontmatter/openai.yaml/resources, create eval prompts, benchmark skill behavior, improve trigger descriptions, package a skill for a Skill Hub, or audit a folder of skills for validity and duplication.
---

# Genius Skill Creator

Use this skill to turn skill ideas into valid, useful, tested skills. It combines two modes:

- **System builder:** scaffold folders, write valid `SKILL.md`, generate `agents/openai.yaml`, add scripts/references/assets, and run validation.
- **Evaluation improver:** create realistic test prompts, compare behavior, review outputs, improve instructions, and optimize trigger descriptions.

Do not treat a skill as finished just because it reads well. A finished skill should be valid, triggerable, lean, resource-aware, and tested enough for its risk.

## Start Here

Classify the user request:

- **Create:** user wants a new skill.
- **Repair:** a skill fails validation, has bad metadata, duplicate names, broken resources, or stale platform assumptions.
- **Merge:** user wants to combine skills or create a higher-level creator skill.
- **Audit:** user wants a folder of skills checked.
- **Evaluate:** user wants test prompts, benchmark-style comparison, or trigger optimization.
- **Port:** user wants a skill adapted to another agent/runtime.

Then inspect the smallest useful evidence:

- Existing `SKILL.md`.
- `agents/openai.yaml` if present.
- `references/`, `scripts/`, `assets/`, and `evals/`.
- Any local validator, target runtime docs, or user-provided examples.

## Non-Negotiables

Every generated or repaired skill must:

- Include `SKILL.md`.
- Use YAML frontmatter with `name` and `description`.
- Use lowercase hyphen-case names.
- Put trigger conditions in `description`, not only in the body.
- Keep `SKILL.md` concise; move detailed material into directly linked `references/`.
- Include scripts only when they add deterministic value or avoid repeated fragile code.
- Include assets only when they are used in outputs.
- Avoid extra docs such as `README.md`, `CHANGELOG.md`, or install guides unless the target ecosystem explicitly requires them.
- Validate with the best available validator before delivery.

For Codex-style skills, use `scripts/quick_validate.py` and `references/openai_yaml.md`.

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
3. Scaffold or patch:
   - Use `scripts/init_skill.py` for new Codex-style skills when useful.
   - Use direct patching for small repairs.
4. Generate or update `agents/openai.yaml` when the target runtime supports it.
5. Validate.
6. Test with realistic prompts when the skill has meaningful behavioral risk.

## Repair Workflow

Check in this order:

1. `SKILL.md` exists and starts with valid frontmatter.
2. Frontmatter name matches folder name unless a compatibility reason is recorded.
3. No duplicate skill names in the target hub.
4. Description is specific, trigger-focused, and under validator limits.
5. `agents/openai.yaml` has a 25-64 character `short_description` and a `default_prompt` mentioning `$skill-name`.
6. Resource files are directly discoverable from `SKILL.md`.
7. Scripts compile or run a representative help/test command.
8. Placeholder text is intentional, not unfinished skill content.

Use `references/openai_yaml.md` for UI metadata constraints.

## Evaluation Workflow

Use evals when success can be checked or when trigger behavior matters.

1. Draft 2-5 realistic user prompts.
2. Include both should-trigger and should-not-trigger cases for description work.
3. Save prompts to `evals/evals.json` when creating a reusable benchmark.
4. Run skill and baseline comparisons when subagents or separate runs are available.
5. Review outputs for:
   - correctness;
   - unnecessary context load;
   - missing resource use;
   - brittle instructions;
   - trigger false positives or false negatives.
6. Improve the skill, then rerun the same prompts.

When full automation is unavailable, perform a manual eval pass and record findings in the final response.

Read `references/eval-workflow.md` before designing a larger benchmark.

## Description Optimization

The `description` field is the primary trigger surface. Improve it by:

- naming the task type;
- listing concrete trigger contexts;
- naming important file types, tools, or workflows;
- saying when not to use the skill;
- avoiding vague claims like "helps with productivity";
- keeping platform-specific assumptions out unless the skill is platform-specific.

For high-stakes trigger tuning, create 20 prompts: roughly half should trigger, half should not.

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
- `references/openai_yaml.md`: `agents/openai.yaml` constraints.
- `references/eval-workflow.md`: practical eval and trigger optimization workflow.
- `references/consolidation-workflow.md`: merge/consolidate related skills.
- `references/hermes-agent-skill-authoring.md`: Claude/Hermes-style skill authoring reference.
- `evals/evals.json`: seed eval set copied from the evaluation-oriented creator.

## Final Response

Report:

- what changed;
- which skills passed validation;
- which issues remain;
- which tests or evals ran;
- where the generated or repaired skill lives.
