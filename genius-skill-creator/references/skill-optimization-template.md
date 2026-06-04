# Skill Optimization Template

Use this template when creating or optimizing a skill package in Genius Skill Hub.

## Requirement Shape

Every skill should be explainable in six fields:

| Field | Required answer |
|:--|:--|
| Purpose | What user job does this skill make easier? |
| Trigger scope | Which user requests should invoke it? |
| Non-goals | Which nearby requests should not invoke it? |
| Inputs | What files, prompts, APIs, or project context does it need? |
| Outputs | What should the agent produce or change? |
| Validation | How can success be checked? |

If these fields are unclear, stop and ask before editing. Do not hide ambiguity by writing generic instructions.

## Package Architecture

Target shape:

```text
<skill>/
+-- SKILL.md                 Thin entrypoint: trigger, mode routing, workflow, resource map
+-- agents/
|   +-- openai.yaml          Codex/UI metadata
|   +-- reasonix.yaml        Reasonix/runtime adapter when supported
+-- references/              Detailed reusable guidance, loaded only when needed
+-- scripts/                 Deterministic helpers and validators
+-- evals/                   Trigger and behavior test prompts
+-- assets/                  Templates, icons, report files, or other output assets
```

Use only the directories the skill actually needs. `agents/openai.yaml` is expected for Skill Hub UI metadata. Add other adapters when the skill is intended to run on another Agent.

## Thin Entrypoint Rules

`SKILL.md` should contain:

- frontmatter with `name` and trigger-focused `description`;
- a short overview;
- a mode or request classifier when the skill has multiple workflows;
- non-negotiable rules;
- workflow steps;
- a resource map with direct file names;
- final response/output standard.

Move long examples, platform-specific details, deep references, and reusable templates out of `SKILL.md`.

## Module Rules

- `references/` owns detailed knowledge and long-form guidance.
- `scripts/` owns repeated deterministic work.
- `evals/` owns reusable prompts and expected outcomes.
- `agents/` owns runtime-specific metadata, tool lists, model choices, and adapter prompts.
- `assets/` owns files used in generated output.

Dependencies should point inward from the entrypoint to modules. Do not make runtime adapters the source of shared workflow truth.

## Multi-Agent Standard

Shared behavior belongs in `SKILL.md` and `references/`. Runtime-specific facts belong in `agents/<runtime>.yaml`.

At minimum, a multi-Agent skill should record:

- runtime name;
- display name;
- adapter purpose;
- invocation style;
- model, when fixed by the runtime;
- allowed tools or capabilities, only when verified;
- shared instruction files;
- expected output format.

Read `agent-adapter-standard.md` before adding a new adapter.

## Output Contract

For skill creation, repair, audit, or optimization, final output should include:

- requirement summary;
- files changed;
- architecture/module changes;
- adapters added or verified;
- validation commands and results;
- evals or manual checks run;
- remaining risks or next step.

For audit-only work, lead with findings and avoid pretending changes were made.

## Validation Gates

Run the smallest set that proves the change:

- `python scripts/quick_validate.py <skill-dir>`;
- parse every `agents/*.yaml`;
- run `node --check` or language syntax checks for changed scripts;
- run representative script smoke tests when scripts changed;
- run or manually review evals when trigger/output behavior changed.

When syncing to Skill Hub, validate both the local source package and the synced package.
