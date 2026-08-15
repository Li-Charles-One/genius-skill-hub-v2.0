#!/usr/bin/env python3
"""
Quick validation script for skills
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

MAX_SKILL_NAME_LENGTH = 64
MAX_ENTRYPOINT_LINES = 250
ALLOWED_FRONTMATTER_PROPERTIES = {"name", "description", "license", "allowed-tools", "metadata"}
PLACEHOLDER_PATTERNS = (
    "TODO:",
    "[TODO:",
    "Complete and informative explanation",
    "Replace with actual",
)
NONGOAL_CUES = (re.compile(r"do not", re.I), re.compile(r"not for", re.I), re.compile(r"不要"))


def parse_skill_frontmatter(skill_md):
    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None, content, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None, content, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict):
            return None, content, "Frontmatter must be a YAML dictionary"
    except yaml.YAMLError as e:
        return None, content, f"Invalid YAML in frontmatter: {e}"

    return frontmatter, content, None


def list_skill_frontmatter_names(hub_path):
    names = {}
    hub_path = Path(hub_path)
    if not hub_path.exists():
        return None, f"Hub path not found: {hub_path}"

    for skill_md in sorted(hub_path.glob("*/SKILL.md")):
        frontmatter, _content, error = parse_skill_frontmatter(skill_md)
        if error or not isinstance(frontmatter, dict):
            continue
        name = frontmatter.get("name")
        if isinstance(name, str) and name.strip():
            names.setdefault(name.strip(), []).append(skill_md.parent)

    return names, None


def validate_resources_are_discoverable(skill_path, content):
    missing = []
    discoverable_text = content
    openai_yaml = skill_path / "agents" / "openai.yaml"
    if openai_yaml.exists():
        discoverable_text += "\n" + openai_yaml.read_text(encoding="utf-8")

    for resource_dir_name in ("references", "scripts", "assets", "evals"):
        resource_dir = skill_path / resource_dir_name
        if not resource_dir.exists():
            continue
        for resource_file in sorted(resource_dir.rglob("*")):
            if "__pycache__" in resource_file.parts or resource_file.suffix in {".pyc", ".pyo"}:
                continue
            if resource_file.is_file():
                rel = resource_file.relative_to(skill_path).as_posix()
                if rel not in discoverable_text and rel.replace("/", "\\") not in discoverable_text:
                    missing.append(rel)
    if missing:
        return (
            False,
            "Resource file(s) are not discoverable from SKILL.md: " + ", ".join(missing),
        )
    return True, None


def validate_no_unfinished_placeholders(content):
    found = [pattern for pattern in PLACEHOLDER_PATTERNS if pattern in content]
    if found:
        return False, "Unfinished placeholder text found in SKILL.md: " + ", ".join(found)
    return True, None


def has_nongoal_cue(description):
    return any(pattern.search(description or "") for pattern in NONGOAL_CUES)


def find_junk_paths(skill_path):
    junk = []
    for path in sorted(skill_path.rglob("*")):
        if path.name in {".DS_Store", "__pycache__"}:
            junk.append(path.relative_to(skill_path).as_posix())
    return junk


def validate_skill(skill_path, hub_path=None):
    """Basic validation of a skill. Returns (valid, message, warnings)."""
    skill_path = Path(skill_path)
    warnings = []

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found", warnings

    frontmatter, content, error = parse_skill_frontmatter(skill_md)
    if error:
        return False, error, warnings

    unexpected_keys = set(frontmatter.keys()) - ALLOWED_FRONTMATTER_PROPERTIES
    if unexpected_keys:
        allowed = ", ".join(sorted(ALLOWED_FRONTMATTER_PROPERTIES))
        unexpected = ", ".join(sorted(unexpected_keys))
        return (
            False,
            f"Unexpected key(s) in SKILL.md frontmatter: {unexpected}. Allowed properties are: {allowed}",
            warnings,
        )

    if "name" not in frontmatter:
        return False, "Missing 'name' in frontmatter", warnings
    if "description" not in frontmatter:
        return False, "Missing 'description' in frontmatter", warnings

    name = frontmatter.get("name", "")
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}", warnings
    name = name.strip()
    if name:
        if not re.match(r"^[a-z0-9-]+$", name):
            return (
                False,
                f"Name '{name}' should be hyphen-case (lowercase letters, digits, and hyphens only)",
                warnings,
            )
        if name.startswith("-") or name.endswith("-") or "--" in name:
            return (
                False,
                f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens",
                warnings,
            )
        if len(name) > MAX_SKILL_NAME_LENGTH:
            return (
                False,
                f"Name is too long ({len(name)} characters). "
                f"Maximum is {MAX_SKILL_NAME_LENGTH} characters.",
                warnings,
            )
    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}", warnings
    description = description.strip()
    if description:
        if "<" in description or ">" in description:
            return False, "Description cannot contain angle brackets (< or >)", warnings
        if len(description) > 1024:
            return (
                False,
                f"Description is too long ({len(description)} characters). Maximum is 1024 characters.",
                warnings,
            )

    if hub_path:
        names, error = list_skill_frontmatter_names(hub_path)
        if error:
            return False, error, warnings
        matches = names.get(name, []) if names else []
        current_dir = skill_path.resolve()
        duplicates = [item for item in matches if item.resolve() != current_dir]
        if duplicates:
            paths = ", ".join(str(item) for item in duplicates)
            return False, f"Duplicate skill name '{name}' found in hub: {paths}", warnings

    if name and name != skill_path.name:
        return False, f"Frontmatter name '{name}' must match folder name '{skill_path.name}'", warnings

    agents_dir = skill_path / "agents"
    if agents_dir.exists():
        for agent_file in sorted(agents_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(agent_file.read_text(encoding="utf-8"))
            except yaml.YAMLError as e:
                return False, f"{agent_file.name}: invalid YAML: {e}", warnings
            if not isinstance(data, dict):
                return False, f"{agent_file.name}: YAML root must be a mapping", warnings

            if agent_file.name == "openai.yaml":
                interface = data.get("interface")
                if not isinstance(interface, dict):
                    return False, "openai.yaml: missing interface mapping", warnings
                short_description = interface.get("short_description", "")
                if not isinstance(short_description, str) or not (25 <= len(short_description) <= 64):
                    return False, "openai.yaml: short_description must be 25-64 characters", warnings
                default_prompt = interface.get("default_prompt", "")
                expected_token = f"${name}"
                if not isinstance(default_prompt, str) or expected_token not in default_prompt:
                    return False, f"openai.yaml: default_prompt must mention {expected_token}", warnings

    ok, message = validate_resources_are_discoverable(skill_path, content)
    if not ok:
        return False, message, warnings

    ok, message = validate_no_unfinished_placeholders(content)
    if not ok:
        return False, message, warnings

    line_count = len(content.splitlines())
    if line_count > MAX_ENTRYPOINT_LINES:
        warnings.append(
            f"SKILL.md has {line_count} lines; keep the entrypoint under {MAX_ENTRYPOINT_LINES} lines"
        )
    if not has_nongoal_cue(description):
        warnings.append("description has no non-goal cue (Do not / not for / 不要)")

    junk = find_junk_paths(skill_path)
    if junk:
        return False, "Junk files in package: " + ", ".join(junk), warnings

    if warnings:
        return True, "Skill is valid with warnings.", warnings
    return True, "Skill is valid!", warnings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a skill package.")
    parser.add_argument("skill_directory", help="Skill directory containing SKILL.md")
    parser.add_argument(
        "--hub",
        help="Optional Skill Hub directory for duplicate frontmatter name checks",
    )
    args = parser.parse_args()

    valid, message, warnings = validate_skill(args.skill_directory, args.hub)
    print(message)
    for warning in warnings:
        print(f"[WARN] {warning}")
    sys.exit(0 if valid else 1)
