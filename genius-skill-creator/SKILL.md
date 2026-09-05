---
name: genius-skill-creator
description: Create, repair, audit, evaluate, optimize, port, or merge SKILL.md skill packages. Use whenever the user wants to turn a workflow, conversation, or folder into a skill, or to fix, audit, eval, or port an existing SKILL.md package — including frontmatter, Skill Hub audits, adapters, trigger tuning, and scaffolding. Do not use for ordinary app code, README writing, product debugging, or code translation.
---

# Genius Skill Creator

Turn skill ideas or existing folders into valid, useful, tested skill packages. This is the Genius Skill Hub optimization template.

A finished skill is valid, triggerable, lean, resource-aware, and tested enough for its risk. Readable prose is not enough.

## Start Here

Classify the request as exactly one mode:

- **Create:** new skill package.
- **Repair:** validation, metadata, broken resources, or stale platform assumptions.
- **Audit:** inspect a skill or folder; lead with findings; do not pretend files changed.
- **Evaluate:** test prompts, trigger tuning, or benchmark comparison.
- **Optimize:** thin the entrypoint, reshape modules, or align to the hub template.
- **Port:** adapt a skill to another runtime.
- **Merge:** combine overlapping skills.

Then inspect the smallest useful evidence: `SKILL.md`, `agents/`, `references/`, `scripts/`, `assets/`, `evals/`, plus any local validator or runtime docs.

Before the first tool-mapped action, read `references/runtime-mapping.md` and map this skill's neutral actions to your runtime. If you cannot map something, mark it unverified and report the gap at the end.

## Architecture

`SKILL.md` is the shared instruction file. It belongs to no platform. Adapters in `agents/` are equal.

- Shared logic lives in `SKILL.md` and `references/`.
- Runtime tool names, install paths, and invocation syntax live in `references/runtime-mapping.md` and `agents/<runtime>.yaml`.
- Do not copy one runtime's tool names into another adapter.

Use `references/skill-optimization-template.md` as the package standard. Repair one skill, validate, then reuse the pattern.

## Non-Negotiables

Every generated or repaired skill must:

- Include `SKILL.md` with YAML `name` and `description`.
- Use lowercase hyphen-case names that match the folder name.
- Put trigger conditions and non-goals in `description`.
- Keep `SKILL.md` thin; move detail into linked `references/`.
- Add scripts and assets only when they are used.
- Put runtime metadata in `agents/<runtime>.yaml`.
- Support Windows, macOS, and Linux when commands or scripts ship.
- Skip extra README, changelog, or install docs unless the target ecosystem requires them.
- Include a Gotchas section. "None known" is valid; invented gotchas are not.
- Validate with `scripts/quick_validate.py` and `scripts/security_scan.py` before delivery.

## Workflows

### Create

1. Read `references/capture-intent.md`. Harvest the conversation and artifacts first. Confirm one hypothesis, then fill purpose, trigger, non-goals, outputs, and dependencies.
2. Scaffold with `scripts/init_skill.py` when useful (`--adapters` for starter adapters).
3. Replace every `(fill: ...)` marker. Make the description a bit pushy and keep non-goals as near misses.
4. Fill Gotchas with real environment traps, or leave "None known".
5. Add only the resources the skill needs.
6. Run `scripts/quick_validate.py` and `scripts/security_scan.py`. If behavior is risky, use `references/eval-run-loop.md`.

### Repair

Check in this order: frontmatter, name/folder match, hub duplicates, description quality, adapter YAML, no runtime leakage in shared files, resource discoverability, portable commands, scripts run, no unfinished placeholders, security scan.

### Audit

Inspect the same evidence as Repair, then run `scripts/security_scan.py`. Report findings first. If no files changed, say so.

### Evaluate

For trigger tuning, read `references/eval-workflow.md`. For checkable behavior, read `references/eval-run-loop.md` and compare with-skill against a baseline in the conversation. Do not treat string matches on this creator's own reply as proof the new skill works.

### Optimize

Audit is read-only. For Optimize, state the limited file scope before editing, then validate only that scope; do not perform unrelated refactors.

1. Capture the six requirement fields in the optimization template.
2. Keep `SKILL.md` as trigger, mode routing, workflow, resource map, and output contract.
3. Move reusable detail into `references/`.
4. Keep deterministic work in `scripts/`.
5. Keep runtime facts in `agents/` and `references/runtime-mapping.md`.
6. Update evals when trigger or output risk changes.
7. Check referenced resources and script entrypoints exist, adapters match declared runtimes, and description triggers align with evals.
8. Validate before hub sync.

### Port

Read `references/agent-adapter-standard.md`. Research the runtime. Map only verified tools. Mark gaps unverified. Do not invent tool names.

### Merge

Read `references/consolidation-workflow.md`. Inventory overlap, pick a structure, merge unique content, mark deprecated skills, then delete only after the replacement works.

## Minimum acceptance matrix

Every repair or optimization checks: a positive trigger, a negative trigger, the output contract, and honest failure handling. A passing structural validator alone is not completion.

## Gotchas

- `quick_validate.py` passing does not mean the generated skill works. Run `references/eval-run-loop.md` when output is checkable.
- Reasonix adapter tool names are unverified except those marked verified in `references/runtime-mapping.md`. Do not copy Codex names into that adapter.
- Security scan LOW findings (undeclared URLs) do not fail the scan; HIGH and MED do.

## Output Standard

Report:

- requirement summary: purpose, trigger, and non-goals;
- architecture changes;
- validation and security scan pass/fail;
- platform status: adapters present, missing, or unverified;
- remaining risks;
- package location.

## Resource Map

- `scripts/init_skill.py`: scaffold folders and optional adapters.
- `scripts/quick_validate.py`: structural checks; warns on fat entrypoints and missing non-goals; fails on junk files.
- `scripts/security_scan.py`: secrets, injection-like instructions, undeclared script URLs.
- `scripts/generate_openai_yaml.py`: Codex/UI `agents/openai.yaml`.
- `scripts/validate_evals.py`: eval definition and optional result assertions.
- `references/skill-optimization-template.md`: package template.
- `references/runtime-mapping.md`: runtime fingerprints, install paths, action mapping.
- `references/agent-adapter-standard.md`: adapter conventions.
- `references/cross-platform-command-standard.md`: Windows/macOS/Linux commands.
- `references/openai_yaml.md`: `agents/openai.yaml` constraints.
- `references/eval-workflow.md`: trigger evals and description craft.
- `references/eval-run-loop.md`: with-skill vs baseline behavior comparison.
- `references/capture-intent.md`: harvest a session or artifacts before scaffolding.
- `references/consolidation-workflow.md`: merge overlapping skills.
- `evals/evals.json`: creation, optimization, porting, trigger, and audit prompts.
- `agents/openai.yaml`, `agents/reasonix.yaml`, `agents/opencode.yaml`, `agents/trae-solo.yaml`, `agents/cherrystudio.yaml`.

## Final Response

Use the Output Standard. If no files changed, say that plainly and report only the audit or plan.
