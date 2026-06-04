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

Purpose: Trae IDE / Trae SOLO adapter for porting skills as native Trae Skills, project rules, user rules, or custom instructions.

Trae has verified native SKILL.md support:

- Project skills: `.trae/skills/<skill-name>/SKILL.md`
- Global skills (Windows): `%USERPROFILE%/.trae-cn/skills/<skill-name>/SKILL.md`
- Global skills (macOS/Linux): `~/.trae-cn/skills/<skill-name>/SKILL.md`
- `.agents/skills/` compatibility for Agent Skills ecosystem
- SKILL.md format: YAML frontmatter (`name`, `description`) + markdown body
- On-demand loading: agent scans descriptions first, loads full content only when task matches
- Subdirectories supported: `examples/`, `templates/`, `resources/`
- Creation: AI conversation, manual UI, or `.zip` import
- Rules system: `user_rules.md` (global), `project_rules.md` (project-level, `.trae/rules/`), 20KB limit
- Rule priority: user input > custom agent prompt > user_rules.md > project_rules.md

Expected shape:

```yaml
runtime: "trae-solo"
display_name: "Readable Name"
description: "Trae IDE / SOLO adapter purpose."
integration_style:
  - "native-skill"
  - "project-rule"
  - "user-rule"
  - "custom-instruction"
capability_status:
  native_skill_package: "verified — Trae supports native SKILL.md with YAML frontmatter"
  skill_format: "SKILL.md with name + description frontmatter plus markdown body"
  skill_discovery: "on-demand — scans descriptions first, loads full content when matched"
  agents_skills_compat: "verified — .agents/skills/ directory supported"
  rules_system: "user_rules.md (global), project_rules.md (project-level); 20000 byte limit"
  tool_names: "use Trae IDE built-in tools; do not invent tool names"
  docs_url_skill: "https://docs.trae.cn/ide/skills"
  docs_url_rules: "https://docs.trae.cn/ide/rules"
skill_deployment:
  project_path: ".trae/skills/<skill-name>/SKILL.md"
  global_path_windows: "%USERPROFILE%/.trae-cn/skills/<skill-name>/SKILL.md"
  global_path_unix: "~/.trae-cn/skills/<skill-name>/SKILL.md"
  agents_compat_path: ".agents/skills/<skill-name>/SKILL.md"
usage:
  default_prompt: "Use skill-name to port or optimize as a native Trae Skill."
  porting_strategy: |
    1. Keep SKILL.md frontmatter with name and description — same format as Codex.
    2. Move detailed guidance into subdirectories — Trae supports them natively.
    3. For project rules, generate project_rules.md snippet from non-negotiable rules.
    4. For global skills, deploy to ~/.trae-cn/skills/<name>/SKILL.md.
    5. Trae SKILL.md format is compatible with Codex SKILL.md format.
  shared_instructions:
    - "../SKILL.md"
    - "../references/specific-guide.md"
  output_contract: "Return requirement summary, Trae skill type, deployment path, files changed, and validation results."
```

Rules:

- Trae has native SKILL.md support — treat it as a first-class skill platform, not just a workflow adapter;
- SKILL.md frontmatter format (`name`, `description`) is compatible with Codex format;
- Use `description` for trigger matching — Trae's on-demand loading depends on it;
- Subdirectories are supported but optional — use only when the skill needs them;
- For skills that also need project-level rules, generate a `project_rules.md` snippet from the skill's non-negotiable rules;
- Global skills go under `~/.trae-cn/skills/`, project skills under `.trae/skills/`;
- Trae also supports `.agents/skills/` for Agent Skills ecosystem compatibility;
- Do not invent Trae-specific tool names beyond what the IDE provides natively.

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
