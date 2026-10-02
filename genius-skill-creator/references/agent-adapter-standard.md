# Agent Adapter Standard

Use `agents/` for product or runtime metadata. Adapters point to shared instructions; they never duplicate the skill.

## Directory Convention

```text
agents/
+-- openai.yaml        Codex/UI metadata (expected in every hub skill)
+-- <runtime>.yaml     Only when a runtime needs metadata beyond SKILL.md
```

`SKILL.md` remains the shared entrypoint. `references/` remains the shared knowledge base. Claude Code, OpenCode, and Codex all load `SKILL.md` natively, so most skills need only `openai.yaml`.

## `agents/openai.yaml`

Purpose: UI and Codex product metadata. Generate it with `scripts/generate_openai_yaml.py`; the full field list and constraints are in `openai_yaml.md`. The hub validator enforces two of them: `short_description` is 25–64 characters, and `default_prompt` mentions `$skill-name`.

## `agents/<runtime>.yaml`

Add one only when the runtime needs facts that `SKILL.md` cannot carry, such as a verified tool allow list or install path. Expected shape:

```yaml
runtime: "opencode"
display_name: "Readable Name"
description: "Runtime-specific adapter purpose."
allowed_tools:          # only tools verified in that runtime
  - Read
  - Bash
capability_status:
  verified_tools: "where and how the tool list was verified"
  install_path: "runtime skill path"
usage:
  default_prompt: "Use skill-name for the concrete task."
  shared_instructions:
    - "../SKILL.md"
  output_contract: "Short description of expected final output."
```

Take tool names from `runtime-mapping.md` or the runtime's current docs. If a runtime is requested but its capabilities are unknown, record the evidence gap in the adapter instead of guessing.

## Adapter Quality Bar

An adapter is acceptable when:

- it parses as YAML;
- it does not put runtime keys into `SKILL.md` frontmatter;
- it points to shared instructions instead of duplicating them;
- it lists only verified tools;
- it records output expectations;
- it avoids secrets, credentials, and machine-private paths.
