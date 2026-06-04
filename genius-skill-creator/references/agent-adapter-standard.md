# Agent Adapter Standard

Use `agents/` for product or runtime metadata. Adapters should not duplicate the whole skill; they should point to shared instructions.

## Directory Convention

```text
agents/
+-- openai.yaml
+-- reasonix.yaml
+-- <runtime>.yaml
```

`SKILL.md` remains the shared entrypoint. `references/` remains the shared knowledge base.

## `agents/openai.yaml`

Purpose: UI and Codex product metadata.

Expected fields:

```yaml
interface:
  display_name: "Readable Name"
  short_description: "25 to 64 character UI description"
  icon_small: "./assets/icon-small.svg"
  icon_large: "./assets/icon-large.png"
  default_prompt: "Use $skill-name to perform a concrete task."
```

Rules:

- quote string values;
- keep `short_description` between 25 and 64 characters;
- make `default_prompt` mention `$skill-name`;
- keep icon paths relative to the skill folder.

## `agents/reasonix.yaml`

Purpose: Reasonix runtime adapter.

Expected shape:

```yaml
runtime: "reasonix"
display_name: "Readable Name"
description: "Runtime-specific adapter purpose."
run_as: "subagent"
model: "deepseek-v4-pro"
allowed_tools:
  - read_file
  - search_content
  - search_files
  - directory_tree
  - get_file_info
  - glob
  - write_file
  - run_command
usage:
  default_prompt: "Use skill-name for the concrete task."
  shared_instructions:
    - "../SKILL.md"
    - "../references/specific-guide.md"
  output_contract: "Short description of expected final output."
```

Only list tools that are verified for the target runtime. Mark uncertain capabilities as absent rather than inventing tool names.

## Adapter Quality Bar

An adapter is acceptable when:

- it parses as YAML;
- it does not put runtime keys into `SKILL.md` frontmatter;
- it points to shared instructions instead of duplicating them;
- it records output expectations;
- it avoids secrets, credentials, and machine-private paths.

If a runtime is requested but capabilities are unknown, create a reference note with the evidence gap instead of guessing.
