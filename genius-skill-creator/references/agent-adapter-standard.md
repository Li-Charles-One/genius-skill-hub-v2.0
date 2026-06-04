# Agent Adapter Standard

Use `agents/` for product or runtime metadata. Adapters should not duplicate the whole skill; they should point to shared instructions.

## Directory Convention

```text
agents/
+-- openai.yaml
+-- reasonix.yaml
+-- trae-solo.yaml
+-- cherrystudio.yaml
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

## `agents/trae-solo.yaml`

Purpose: Trae SOLO adapter for using shared skill instructions as SOLO Coder, SOLO Builder, project rule, custom instruction, or MCP-oriented guidance.

Expected shape:

```yaml
runtime: "trae-solo"
display_name: "Readable Name"
description: "Trae SOLO adapter purpose."
integration_style:
  - "solo-coder"
  - "solo-builder"
  - "project-rule"
  - "custom-instruction"
capability_status:
  tool_names: "unverified"
  command_execution: "through Trae SOLO workspace/tool panels when available"
usage:
  default_prompt: "Use skill-name to perform the concrete task."
  shared_instructions:
    - "../SKILL.md"
    - "../references/specific-guide.md"
  output_contract: "Short description of expected final output."
```

Rules:

- treat Trae SOLO as a workflow adapter, not a Codex skill package format;
- map the skill into requirements, plan, files touched, verification, and final handoff;
- do not invent Trae-specific tool names;
- if a real `.trae`, `.trae-cn`, rule, or marketplace package format is discovered in the target workspace, record that evidence before generating files for it.

## `agents/cherrystudio.yaml`

Purpose: CherryStudio adapter for Code Tool, Agent, MCP, or custom assistant use.

Expected shape:

```yaml
runtime: "cherrystudio"
display_name: "Readable Name"
description: "CherryStudio adapter purpose."
integration_style:
  - "code-tool"
  - "agent"
  - "mcp"
  - "custom-assistant"
capability_status:
  code_agents: "verified through Cherry Studio Code Tools docs"
  mcp_permissions: "verified through Cherry Studio Agent docs"
  native_skill_package: "unverified"
usage:
  default_prompt: "Use skill-name to perform the concrete task."
  shared_instructions:
    - "../SKILL.md"
    - "../references/specific-guide.md"
  output_contract: "Short description of expected final output."
```

Rules:

- do not assume CherryStudio has a native Skill Hub package format;
- when using Code Tool, keep instructions portable for the selected CLI agent such as Codex, Claude Code, Gemini CLI, or Qwen Code;
- when using Agent/MCP, describe required permissions and MCP services without recording secrets;
- keep OS-specific command setup outside the adapter unless it is runtime-specific.

## Adapter Quality Bar

An adapter is acceptable when:

- it parses as YAML;
- it does not put runtime keys into `SKILL.md` frontmatter;
- it points to shared instructions instead of duplicating them;
- it records output expectations;
- it avoids secrets, credentials, and machine-private paths.

If a runtime is requested but capabilities are unknown, create a reference note with the evidence gap instead of guessing.

## Evidence Notes

Record source assumptions in adapter files when they affect behavior. Use stable official docs where possible. Current conservative basis:

- Trae SOLO docs describe SOLO mode as a requirements-to-preview/deployment workflow with SOLO Coder, SOLO Builder, task management, tool panels, and DiffView.
- Cherry Studio Code Tools docs describe launching and managing code agents, including Claude Code, Gemini CLI, Qwen Code, and OpenAI Codex.
- Cherry Studio Agent docs describe editing Agent permissions and the tools or MCP services it can use.
