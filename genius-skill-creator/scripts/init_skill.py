#!/usr/bin/env python3
"""
Skill Initializer - Creates a new skill from template

Usage:
    init_skill.py <skill-name> --path <path> [--resources scripts,references,assets,evals] [--interface key=value]

Examples:
    init_skill.py my-new-skill --path skills/public
    init_skill.py my-new-skill --path skills/public --resources scripts,references,evals
    init_skill.py my-skill --path skills/public --interface short_description="Short UI label"
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

STARTER_EVALS = """{{
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
    }},
    {{
      "id": "near-miss",
      "prompt": "Nearby user request that should not trigger this skill.",
      "trigger_expected": false,
      "expected_output": "Does not use {skill_name}.",
      "files": [],
      "assertions": [
        {{"type": "not_contains", "value": "{skill_name}"}}
      ]
    }}
  ]
}}
"""

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


RESOURCE_MAP_LINES = {
    "agents": "`agents/openai.yaml`: Codex/UI metadata.",
    "scripts": "`scripts/`: deterministic helpers.",
    "references": "`references/`: detailed guidance loaded on demand.",
    "assets": "`assets/`: files used in generated output.",
    "evals": "`evals/evals.json`: trigger and behavior prompts.",
}


def format_resource_map(resources):
    return "\n".join(f"- {RESOURCE_MAP_LINES[resource]}" for resource in ["agents", *resources])


def create_resource_dirs(skill_dir, skill_name, resources):
    for resource in resources:
        resource_dir = skill_dir / resource
        resource_dir.mkdir(exist_ok=True)
        if resource == "evals":
            (resource_dir / "evals.json").write_text(STARTER_EVALS.format(skill_name=skill_name), encoding="utf-8")
            print("[OK] Created evals/evals.json")
        else:
            print(f"[OK] Created {resource}/")


def init_skill(skill_name, path, resources, interface_overrides):
    """
    Initialize a new skill directory with template SKILL.md.

    Args:
        skill_name: Name of the skill
        path: Path where the skill directory should be created
        resources: Resource directories to create
        interface_overrides: key=value overrides for agents/openai.yaml

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
        agent_resource_map=format_resource_map(resources),
    )

    skill_md_path = skill_dir / "SKILL.md"
    try:
        skill_md_path.write_text(skill_content, encoding="utf-8")
        print("[OK] Created SKILL.md")
    except Exception as e:
        print(f"[ERROR] Error creating SKILL.md: {e}")
        return None

    # Create agents/openai.yaml.
    try:
        if not write_openai_yaml(skill_dir, skill_name, interface_overrides):
            return None
    except Exception as e:
        print(f"[ERROR] Error creating agents/openai.yaml: {e}")
        return None

    # Create resource directories if requested
    if resources:
        try:
            create_resource_dirs(skill_dir, skill_name, resources)
        except Exception as e:
            print(f"[ERROR] Error creating resource directories: {e}")
            return None

    # Print next steps
    print(f"\n[OK] Skill '{skill_name}' initialized successfully at {skill_dir}")
    print("\nNext steps:")
    print("1. Edit SKILL.md to replace (fill: ...) markers and tighten the description")
    if resources:
        resource_labels = ", ".join(f"{resource}/" for resource in resources)
        print(f"2. Add resources to {resource_labels} as needed")
    else:
        print("2. Create resource directories only if needed (scripts/, references/, assets/, evals/)")
    print("3. Review agents/openai.yaml")
    print("4. Run quick_validate.py and security_scan.py")
    print("5. Forward-test complex skills with realistic user requests to ensure they work as intended")

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

    path = args.path

    print(f"Initializing skill: {skill_name}")
    print(f"   Location: {path}")
    print(f"   Resources: {', '.join(resources) if resources else 'none (create as needed)'}")
    print()

    result = init_skill(skill_name, path, resources, args.interface)

    if result:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
