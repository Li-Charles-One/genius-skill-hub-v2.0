#!/usr/bin/env python3
"""
Skill Initializer - Creates a new skill from template

Usage:
    init_skill.py <skill-name> --path <path> [--resources scripts,references,assets,evals] [--examples] [--adapters openai,reasonix,trae-solo,cherrystudio] [--interface key=value]

Examples:
    init_skill.py my-new-skill --path skills/public
    init_skill.py my-new-skill --path skills/public --resources scripts,references
    init_skill.py my-api-helper --path skills/private --resources scripts --examples
    init_skill.py custom-skill --path /custom/location
    init_skill.py my-skill --path skills/public --interface short_description="Short UI label"
    init_skill.py portable-skill --path skills/public --adapters openai,reasonix,trae-solo
"""

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_openai_yaml import write_openai_yaml

MAX_SKILL_NAME_LENGTH = 64
ALLOWED_RESOURCES = {"scripts", "references", "assets", "evals"}
ALLOWED_ADAPTERS = {"openai", "reasonix", "trae-solo", "cherrystudio"}
DEFAULT_ADAPTERS = ["openai"]

SKILL_TEMPLATE = """---
name: {skill_name}
description: "Use whenever the user needs {skill_name} work. Trigger on create, repair, or run requests for {skill_name}. Do not use for unrelated coding or documentation."
---

# {skill_title}

## Overview

(fill: 1-2 sentences on what this skill enables.)

## Start Here

Classify the request this skill handles:

- (fill: mode 1)
- (fill: mode 2)

Then inspect the smallest useful evidence:

- (fill: files or context this skill must read first)

## Non-Negotiables

- (fill: hard rule 1)
- (fill: hard rule 2)

## Workflow

1. Classify the request using the modes above.
2. (fill: first domain action)
3. Validate the result with the smallest reliable check.

## Gotchas

None known.

## Resource Map

{agent_resource_map}

## Final Response

Report what changed, validation run, remaining risks, and where the skill package lives.
"""

EXAMPLE_SCRIPT = '''#!/usr/bin/env python3
"""
Example helper script for {skill_name}

This is a placeholder script that can be executed directly.
Replace with actual implementation or delete if not needed.

Example real scripts from other skills:
- pdf/scripts/fill_fillable_fields.py - Fills PDF form fields
- pdf/scripts/convert_pdf_to_images.py - Converts PDF pages to images
"""

def main():
    print("This is an example script for {skill_name}")
    # TODO: Add actual script logic here
    # This could be data processing, file conversion, API calls, etc.

if __name__ == "__main__":
    main()
'''

EXAMPLE_REFERENCE = """# Reference Documentation for {skill_title}

This is a placeholder for detailed reference documentation.
Replace with actual reference content or delete if not needed.

Example real reference docs from other skills:
- product-management/references/communication.md - Comprehensive guide for status updates
- product-management/references/context_building.md - Deep-dive on gathering context
- bigquery/references/ - API references and query examples

## When Reference Docs Are Useful

Reference docs are ideal for:
- Comprehensive API documentation
- Detailed workflow guides
- Complex multi-step processes
- Information too lengthy for main SKILL.md
- Content that's only needed for specific use cases

## Structure Suggestions

### API Reference Example
- Overview
- Authentication
- Endpoints with examples
- Error codes
- Rate limits

### Workflow Guide Example
- Prerequisites
- Step-by-step instructions
- Common patterns
- Troubleshooting
- Best practices
"""

EXAMPLE_ASSET = """# Example Asset File

This placeholder represents where asset files would be stored.
Replace with actual asset files (templates, images, fonts, etc.) or delete if not needed.

Asset files are NOT intended to be loaded into context, but rather used within
the output Codex produces.

Example asset files from other skills:
- Brand guidelines: logo.png, slides_template.pptx
- Frontend builder: hello-world/ directory with HTML/React boilerplate
- Typography: custom-font.ttf, font-family.woff2
- Data: sample_data.csv, test_dataset.json

## Common Asset Types

- Templates: .pptx, .docx, boilerplate directories
- Images: .png, .jpg, .svg, .gif
- Fonts: .ttf, .otf, .woff, .woff2
- Boilerplate code: Project directories, starter files
- Icons: .ico, .svg
- Data files: .csv, .json, .xml, .yaml

Note: This is a text placeholder. Actual assets can be any file type.
"""

EXAMPLE_EVALS = """{{
  "skill_name": "{skill_name}",
  "evals": [
    {{
      "id": "basic-trigger",
      "prompt": "Concrete user request that should trigger this skill.",
      "trigger_expected": true,
      "expected_output": "What good behavior looks like.",
      "files": [],
      "assertions": [
        {{"type": "contains", "value": "{skill_name}"}}
      ]
    }}
  ]
}}
"""

REASONIX_ADAPTER_TEMPLATE = """runtime: "reasonix"
display_name: "{skill_title}"
description: "Reasonix adapter for using {skill_name}."
run_as: "subagent"
model: "deepseek-v4-pro" # default; override per project when the Reasonix runtime supports it
allowed_tools:
  - run_skill
  - bash
  - read_file
  - write_file
  - edit_file
  - grep
  - glob
  - ls
  - task
capability_status:
  verified_tools: "run_skill and Bash(...) from local reasonix.toml"
  unverified_tools: "read_file, write_file, edit_file, grep, glob, ls, task follow the hub fingerprint"
  do_not_copy: "Codex names such as search_content, directory_tree, run_command"
usage:
  default_prompt: "Use {skill_name} for the concrete task."
  shared_instructions:
    - "../SKILL.md"
  output_contract: "Report requirement summary, files changed, validation results, and remaining risks."
"""

TRAE_SOLO_ADAPTER_TEMPLATE = """runtime: "trae-solo"
display_name: "{skill_title}"
description: "Trae IDE / Trae SOLO adapter for porting {skill_name} as a native Trae Skill, project rule, or custom instruction."
integration_style:
  - "native-skill"
  - "project-rule"
  - "user-rule"
  - "custom-instruction"
capability_status:
  native_skill_package: "verified - Trae supports native SKILL.md with YAML frontmatter under .trae/skills/ or ~/.trae-cn/skills/"
  skill_format: "SKILL.md with name and description frontmatter plus markdown body"
  skill_discovery: "on-demand - descriptions are matched before full content loads"
  tool_names: "use Trae IDE built-in tools; do not invent runtime-specific tool names"
skill_deployment:
  project_path: ".trae/skills/{skill_name}/SKILL.md"
  global_path_windows: "%USERPROFILE%/.trae-cn/skills/{skill_name}/SKILL.md"
  global_path_unix: "~/.trae-cn/skills/{skill_name}/SKILL.md"
  agents_compat_path: ".agents/skills/{skill_name}/SKILL.md"
usage:
  default_prompt: "Use {skill_name} as a native Trae Skill or project rule."
  shared_instructions:
    - "../SKILL.md"
  output_contract: "Return Trae deployment path, generated files or rule text, validation results, and remaining risks."
"""

CHERRYSTUDIO_ADAPTER_TEMPLATE = """runtime: "cherrystudio"
display_name: "{skill_title}"
description: "CherryStudio adapter for using {skill_name} through Code Tool, Agent, MCP, or custom assistant workflows."
integration_style:
  - "code-tool"
  - "agent"
  - "mcp"
  - "custom-assistant"
capability_status:
  code_agents: "verified through Cherry Studio Code Tools docs"
  mcp_permissions: "verified through Cherry Studio Agent docs"
  native_skill_package: "unverified"
  tool_names: "use the selected code agent or MCP service capabilities; do not invent CherryStudio-native tool names"
usage:
  default_prompt: "Use {skill_name} for CherryStudio Code Tool, Agent, MCP, or custom assistant workflows."
  shared_instructions:
    - "../SKILL.md"
  output_contract: "Return integration style, code-agent or MCP assumptions, validation results, and unverified capabilities."
"""

ADAPTER_TEMPLATES = {
    "reasonix": ("reasonix.yaml", REASONIX_ADAPTER_TEMPLATE),
    "trae-solo": ("trae-solo.yaml", TRAE_SOLO_ADAPTER_TEMPLATE),
    "cherrystudio": ("cherrystudio.yaml", CHERRYSTUDIO_ADAPTER_TEMPLATE),
}

AGENT_RESOURCE_MAP = {
    "openai": "`agents/openai.yaml`: Codex/UI metadata.",
    "reasonix": "`agents/reasonix.yaml`: Reasonix runtime adapter metadata.",
    "trae-solo": "`agents/trae-solo.yaml`: Trae native skill and rule adapter metadata.",
    "cherrystudio": "`agents/cherrystudio.yaml`: CherryStudio Code Tool/Agent/MCP adapter metadata.",
}


def normalize_skill_name(skill_name):
    """Normalize a skill name to lowercase hyphen-case."""
    normalized = skill_name.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized


def title_case_skill_name(skill_name):
    """Convert hyphenated skill name to Title Case for display."""
    return " ".join(word.capitalize() for word in skill_name.split("-"))


def parse_resources(raw_resources):
    if not raw_resources:
        return []
    resources = [item.strip() for item in raw_resources.split(",") if item.strip()]
    invalid = sorted({item for item in resources if item not in ALLOWED_RESOURCES})
    if invalid:
        allowed = ", ".join(sorted(ALLOWED_RESOURCES))
        print(f"[ERROR] Unknown resource type(s): {', '.join(invalid)}")
        print(f"   Allowed: {allowed}")
        sys.exit(1)
    deduped = []
    seen = set()
    for resource in resources:
        if resource not in seen:
            deduped.append(resource)
            seen.add(resource)
    return deduped


def parse_adapters(raw_adapters):
    if not raw_adapters:
        return list(DEFAULT_ADAPTERS)
    adapters = [item.strip() for item in raw_adapters.split(",") if item.strip()]
    invalid = sorted({item for item in adapters if item not in ALLOWED_ADAPTERS})
    if invalid:
        allowed = ", ".join(sorted(ALLOWED_ADAPTERS))
        print(f"[ERROR] Unknown adapter(s): {', '.join(invalid)}")
        print(f"   Allowed: {allowed}")
        sys.exit(1)
    deduped = []
    seen = set()
    for adapter in adapters:
        if adapter not in seen:
            deduped.append(adapter)
            seen.add(adapter)
    return deduped


RESOURCE_MAP_LINES = {
    "scripts": "`scripts/`: deterministic helpers.",
    "references": "`references/`: detailed guidance loaded on demand.",
    "assets": "`assets/`: files used in generated output.",
    "evals": "`evals/evals.json`: trigger and behavior prompts.",
}


def format_agent_resource_map(adapters, resources=None):
    lines = [f"- {AGENT_RESOURCE_MAP[adapter]}" for adapter in adapters]
    for resource in resources or []:
        lines.append(f"- {RESOURCE_MAP_LINES[resource]}")
    if not lines:
        return "- (fill: list references/scripts/assets/evals that actually exist.)"
    return "\n".join(lines)


def create_adapter_files(skill_dir, skill_name, skill_title, adapters, interface_overrides):
    if interface_overrides and "openai" not in adapters:
        print("[ERROR] --interface can only be used when the openai adapter is selected.")
        return False

    if "openai" in adapters:
        result = write_openai_yaml(skill_dir, skill_name, interface_overrides)
        if not result:
            return False

    agents_dir = skill_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    for adapter in adapters:
        if adapter == "openai":
            continue
        file_name, template = ADAPTER_TEMPLATES[adapter]
        output_path = agents_dir / file_name
        output_path.write_text(
            template.format(skill_name=skill_name, skill_title=skill_title),
            encoding="utf-8",
        )
        print(f"[OK] Created agents/{file_name}")

    return True


def create_resource_dirs(skill_dir, skill_name, skill_title, resources, include_examples):
    for resource in resources:
        resource_dir = skill_dir / resource
        resource_dir.mkdir(exist_ok=True)
        if resource == "scripts":
            if include_examples:
                example_script = resource_dir / "example.py"
                example_script.write_text(EXAMPLE_SCRIPT.format(skill_name=skill_name), encoding="utf-8")
                example_script.chmod(0o755)
                print("[OK] Created scripts/example.py")
            else:
                print("[OK] Created scripts/")
        elif resource == "references":
            if include_examples:
                example_reference = resource_dir / "api_reference.md"
                example_reference.write_text(EXAMPLE_REFERENCE.format(skill_title=skill_title), encoding="utf-8")
                print("[OK] Created references/api_reference.md")
            else:
                print("[OK] Created references/")
        elif resource == "assets":
            if include_examples:
                example_asset = resource_dir / "example_asset.txt"
                example_asset.write_text(EXAMPLE_ASSET, encoding="utf-8")
                print("[OK] Created assets/example_asset.txt")
            else:
                print("[OK] Created assets/")
        elif resource == "evals":
            if include_examples:
                example_evals = resource_dir / "evals.json"
                example_evals.write_text(EXAMPLE_EVALS.format(skill_name=skill_name), encoding="utf-8")
                print("[OK] Created evals/evals.json")
            else:
                print("[OK] Created evals/")


def init_skill(skill_name, path, resources, include_examples, interface_overrides, adapters):
    """
    Initialize a new skill directory with template SKILL.md.

    Args:
        skill_name: Name of the skill
        path: Path where the skill directory should be created
        resources: Resource directories to create
        include_examples: Whether to create example files in resource directories
        adapters: Agent/runtime adapter metadata files to create

    Returns:
        Path to created skill directory, or None if error
    """
    # Determine skill directory path
    skill_dir = Path(path).resolve() / skill_name

    # Check if directory already exists
    if skill_dir.exists():
        print(f"[ERROR] Skill directory already exists: {skill_dir}")
        return None

    # Create skill directory
    try:
        skill_dir.mkdir(parents=True, exist_ok=False)
        print(f"[OK] Created skill directory: {skill_dir}")
    except Exception as e:
        print(f"[ERROR] Error creating directory: {e}")
        return None

    # Create SKILL.md from template
    skill_title = title_case_skill_name(skill_name)
    skill_content = SKILL_TEMPLATE.format(
        skill_name=skill_name,
        skill_title=skill_title,
            agent_resource_map=format_agent_resource_map(adapters, resources),
    )

    skill_md_path = skill_dir / "SKILL.md"
    try:
        skill_md_path.write_text(skill_content, encoding="utf-8")
        print("[OK] Created SKILL.md")
    except Exception as e:
        print(f"[ERROR] Error creating SKILL.md: {e}")
        return None

    # Create selected adapter metadata files.
    try:
        if not create_adapter_files(skill_dir, skill_name, skill_title, adapters, interface_overrides):
            return None
    except Exception as e:
        print(f"[ERROR] Error creating adapter metadata: {e}")
        return None

    # Create resource directories if requested
    if resources:
        try:
            create_resource_dirs(skill_dir, skill_name, skill_title, resources, include_examples)
        except Exception as e:
            print(f"[ERROR] Error creating resource directories: {e}")
            return None

    # Print next steps
    print(f"\n[OK] Skill '{skill_name}' initialized successfully at {skill_dir}")
    print("\nNext steps:")
    print("1. Edit SKILL.md to replace (fill: ...) markers and tighten the description")
    if resources:
        resource_labels = ", ".join(f"{resource}/" for resource in resources)
        if include_examples:
            print(f"2. Customize or delete the example files in {resource_labels}")
        else:
            print(f"2. Add resources to {resource_labels} as needed")
    else:
        print("2. Create resource directories only if needed (scripts/, references/, assets/, evals/)")
    adapter_labels = ", ".join(f"agents/{adapter}.yaml" if adapter != "openai" else "agents/openai.yaml" for adapter in adapters)
    print(f"3. Review generated adapter metadata: {adapter_labels}")
    print("4. Add or remove agents/<runtime>.yaml when runtime support changes")
    print("5. Run the validator when ready to check the skill structure")
    print(
        "6. Forward-test complex skills with realistic user requests to ensure they work as intended"
    )

    return skill_dir


def main():
    parser = argparse.ArgumentParser(
        description="Create a new skill directory with a SKILL.md template.",
    )
    parser.add_argument("skill_name", help="Skill name (normalized to hyphen-case)")
    parser.add_argument("--path", required=True, help="Output directory for the skill")
    parser.add_argument(
        "--resources",
        default="",
        help="Comma-separated list: scripts,references,assets,evals",
    )
    parser.add_argument(
        "--examples",
        action="store_true",
        help="Create example files inside the selected resource directories",
    )
    parser.add_argument(
        "--adapters",
        default="openai",
        help="Comma-separated adapters to create: openai,reasonix,trae-solo,cherrystudio",
    )
    parser.add_argument(
        "--interface",
        action="append",
        default=[],
        help="Interface override in key=value format (repeatable)",
    )
    args = parser.parse_args()

    raw_skill_name = args.skill_name
    skill_name = normalize_skill_name(raw_skill_name)
    if not skill_name:
        print("[ERROR] Skill name must include at least one letter or digit.")
        sys.exit(1)
    if len(skill_name) > MAX_SKILL_NAME_LENGTH:
        print(
            f"[ERROR] Skill name '{skill_name}' is too long ({len(skill_name)} characters). "
            f"Maximum is {MAX_SKILL_NAME_LENGTH} characters."
        )
        sys.exit(1)
    if skill_name != raw_skill_name:
        print(f"Note: Normalized skill name from '{raw_skill_name}' to '{skill_name}'.")

    resources = parse_resources(args.resources)
    adapters = parse_adapters(args.adapters)
    if args.examples and not resources:
        print("[ERROR] --examples requires --resources to be set.")
        sys.exit(1)

    path = args.path

    print(f"Initializing skill: {skill_name}")
    print(f"   Location: {path}")
    if resources:
        print(f"   Resources: {', '.join(resources)}")
        if args.examples:
            print("   Examples: enabled")
    else:
        print("   Resources: none (create as needed)")
    print(f"   Adapters: {', '.join(adapters)}")
    print()

    result = init_skill(skill_name, path, resources, args.examples, args.interface, adapters)

    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
