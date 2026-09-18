#!/usr/bin/env python3
"""Validate DESIGN.md against Output Contract v1."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MODES = frozenset({"brand-template", "reverse-engineer", "recommendation"})
THEMES = frozenset({"light", "dark"})
DIAL_KEYS = ("DESIGN_VARIANCE", "MOTION_INTENSITY", "VISUAL_DENSITY")
COLOR_ROLES = (
    "background",
    "surface",
    "text",
    "text-muted",
    "accent",
    "border",
    "focus",
)
TYPE_KEYS = (
    "font-body",
    "font-heading",
    "size-body",
    "size-heading",
    "line-height-body",
    "line-height-heading",
)
SPACE_KEYS = ("small", "medium", "large")
EVIDENCE_KINDS = frozenset({"Observed", "Inferred", "Recommended"})
OBSERVED_METHODS = frozenset(
    {"computed-style", "screenshot", "supplied-guideline", "css-source", "catalog"}
)
REQUIRED_H2 = (
    "Design Read",
    "Colors",
    "Typography",
    "Spacing and Shape",
    "Layout",
    "Components",
)
OPTIONAL_H2 = (
    "Decisions and Overrides",
    "Motion",
    "Imagery",
    "Accessibility",
    "Honesty and Refusals",
    "Anti-Patterns",
    "Sources and Inference",
    "Pre-Ship Checklist",
)
SUBSTANTIVE_MIN = 80
CHECKLIST_ITEMS = (
    "Brief fidelity",
    "Rule priority",
    "Evidence",
    "Dials",
    "Color and themes",
    "Type and spacing",
    "Rhythm",
    "Components",
    "Accessibility",
    "Motion and assets",
    "Honesty and anti-patterns",
    "Handoff",
)
UNKNOWN_TOKEN_KEYS = frozenset({"value", "status", "reason"})
UNFINISHED_RE = re.compile(
    r"(?:^|(?<=\s))(?:TODO|TBD|FIXME|REPLACE_ME)\b|#xxxxxx\b|<[a-z]+-[a-z0-9-]+>",
    re.I,
)
KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
H2_RE = re.compile(r"(?m)^##(?!#)[ \t]+(.+?)\s*$")
CHECK_RE = re.compile(
    r"(?m)^\s*[-*]\s*\[([ xX])\]\s*\*\*(.+?)\*\*\s*:?\s*(.*)$"
)


def yaml_install_hint() -> str:
    if sys.platform == "win32":
        return "PyYAML is required. Install with: python -m pip install PyYAML"
    return "PyYAML is required. Install with: python3 -m pip install PyYAML"


def _import_yaml():
    try:
        import yaml
    except ImportError as exc:
        raise ImportError(yaml_install_hint()) from exc
    return yaml


def _unique_loader(yaml):
    class UniqueKeyLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            if not isinstance(node, yaml.nodes.MappingNode):
                raise yaml.constructor.ConstructorError(
                    None,
                    None,
                    f"expected a mapping node, but found {node.id}",
                    node.start_mark,
                )
            self.flatten_mapping(node)
            mapping = {}
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                if key in mapping:
                    raise yaml.constructor.ConstructorError(
                        "while constructing a mapping",
                        node.start_mark,
                        f"found duplicate key {key!r}",
                        key_node.start_mark,
                    )
                mapping[key] = self.construct_object(value_node, deep=deep)
            return mapping

    return UniqueKeyLoader


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _unfinished(value: str) -> bool:
    return not value.strip() or bool(UNFINISHED_RE.search(value.strip()))


def _need_str(value, label: str, fails: list[str]) -> str | None:
    if not isinstance(value, str):
        fails.append(f"{label} must be a nonempty string")
        return None
    if _unfinished(value):
        fails.append(f"{label} is empty or still a template marker")
        return None
    return value


def _need_map(value, label: str, fails: list[str]):
    if not isinstance(value, dict):
        fails.append(f"{label} must be a mapping")
        return None
    return value


def _need_list(value, label: str, fails: list[str]):
    if not isinstance(value, list):
        fails.append(f"{label} must be a list")
        return None
    return value


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1 :])
    return None, text


def _h2_sections(body: str) -> dict[str, str]:
    matches = list(H2_RE.finditer(body))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections.setdefault(title, body[start:end])
    return sections


def _is_unknown_token(value) -> bool:
    if not isinstance(value, dict):
        return False
    if set(value.keys()) - UNKNOWN_TOKEN_KEYS:
        return False
    return (
        "value" in value
        and value.get("value") is None
        and value.get("status") == "unknown"
        and isinstance(value.get("reason"), str)
        and bool(value["reason"].strip())
        and not _unfinished(value["reason"])
    )


def _check_token_value(value, label: str, fails: list[str], warns: list[str]) -> None:
    if _is_unknown_token(value):
        warns.append(f"{label} is an explicit unknown token")
        return
    if isinstance(value, bool) or value is None:
        fails.append(f"{label} must be a nonempty string or number, never a boolean")
        return
    if isinstance(value, (int, float)):
        return
    if isinstance(value, str):
        if _unfinished(value):
            fails.append(f"{label} is empty or still a template marker")
        return
    fails.append(
        f"{label} must be a nonempty string or number, or "
        "{value: null, status: unknown, reason: ...}"
    )


def _check_token_map(mapping, label: str, required: tuple[str, ...], fails, warns) -> None:
    data = _need_map(mapping, label, fails)
    if data is None:
        return
    for key in data:
        if not isinstance(key, str) or not KEBAB_RE.fullmatch(key):
            fails.append(f"{label} token name {key!r} must be lowercase kebab-case")
    for key in required:
        if key not in data:
            fails.append(f"{label} missing required token {key!r}")
            continue
        _check_token_value(data[key], f"{label}.{key}", fails, warns)
    for key, value in data.items():
        if key in required:
            continue
        _check_token_value(value, f"{label}.{key}", fails, warns)


def _check_colors(colors, themes: list[str], fails, warns) -> None:
    data = _need_map(colors, "tokens.colors", fails)
    if data is None:
        return
    declared = set(themes)
    found = set(data)
    for extra in sorted(found - declared):
        fails.append(f"tokens.colors has undeclared theme {extra!r}")
    for theme in themes:
        if theme not in data:
            fails.append(f"tokens.colors missing declared theme {theme!r}")
            continue
        _check_token_map(
            data[theme], f"tokens.colors.{theme}", COLOR_ROLES, fails, warns
        )


def _check_components(components, fails) -> None:
    data = _need_map(components, "components", fails)
    if data is None:
        return
    if not data:
        fails.append("components must contain at least one named component")
        return
    for name, spec in data.items():
        label = f"components.{name}"
        item = _need_map(spec, label, fails)
        if item is None:
            continue
        interactive = item.get("interactive")
        if not isinstance(interactive, bool):
            fails.append(f"{label}.interactive must be a boolean")
        states = item.get("states")
        if not isinstance(states, list) or not states:
            fails.append(f"{label}.states must be a nonempty list")
            continue
        seen: list[str] = []
        valid = True
        for index, state in enumerate(states):
            if not isinstance(state, str) or _unfinished(state):
                fails.append(f"{label}.states[{index}] must be a nonempty string")
                valid = False
                continue
            if state in seen:
                fails.append(f"{label}.states has duplicate {state!r}")
            else:
                seen.append(state)
        if not valid:
            continue
        if "default" not in seen:
            fails.append(f"{label}.states must include default")
        if interactive is True and "focus-visible" not in seen:
            fails.append(f"{label} is interactive and must include focus-visible")


def _check_evidence(evidence, fails) -> bool:
    rows = _need_list(evidence, "evidence", fails)
    if rows is None:
        return False
    if not rows:
        fails.append("evidence must contain at least one record")
        return False
    ids: list[str] = []
    has_observed = False
    for index, record in enumerate(rows):
        label = f"evidence[{index}]"
        item = _need_map(record, label, fails)
        if item is None:
            continue
        rec_id = _need_str(item.get("id"), f"{label}.id", fails)
        if rec_id is not None:
            if rec_id in ids:
                fails.append(f"{label}.id {rec_id!r} is not unique")
            else:
                ids.append(rec_id)
        kind = item.get("kind")
        if kind not in EVIDENCE_KINDS:
            fails.append(
                f"{label}.kind must be one of {sorted(EVIDENCE_KINDS)}"
            )
        else:
            if kind == "Observed":
                has_observed = True
        _need_str(item.get("source"), f"{label}.source", fails)
        _need_str(item.get("claim"), f"{label}.claim", fails)
        if kind == "Observed":
            method = item.get("method")
            if method not in OBSERVED_METHODS:
                fails.append(
                    f"{label}.method must be one of {sorted(OBSERVED_METHODS)}"
                )
            _need_str(item.get("locator"), f"{label}.locator", fails)
    return has_observed


def _check_pair_list(value, label: str, first: str, second: str, fails) -> list:
    rows = _need_list(value, label, fails)
    if rows is None:
        return []
    valid = []
    for index, record in enumerate(rows):
        item_label = f"{label}[{index}]"
        item = _need_map(record, item_label, fails)
        if item is None:
            continue
        a = _need_str(item.get(first), f"{item_label}.{first}", fails)
        b = _need_str(item.get(second), f"{item_label}.{second}", fails)
        if a is not None and b is not None:
            valid.append(item)
    return valid


def _check_frontmatter(data, fails, warns) -> int | None:
    if not isinstance(data, dict):
        fails.append("YAML frontmatter must be a mapping")
        return None
    version = data.get("schema_version", None)
    if not _is_int(version) or version != 1:
        fails.append("schema_version must be integer 1 (booleans are not integers)")
    _need_str(data.get("name"), "name", fails)
    mode = data.get("mode")
    if mode not in MODES:
        fails.append(f"mode must be one of {sorted(MODES)}")
    _need_str(data.get("design_read"), "design_read", fails)

    scope = _need_map(data.get("scope"), "scope", fails)
    themes: list[str] = []
    if scope is not None:
        _need_str(scope.get("page_kind"), "scope.page_kind", fails)
        _need_str(scope.get("audience"), "scope.audience", fails)
        raw_themes = scope.get("themes")
        if not isinstance(raw_themes, list) or not raw_themes:
            fails.append("scope.themes must be a nonempty list")
        else:
            seen = []
            for index, theme in enumerate(raw_themes):
                if theme not in THEMES:
                    fails.append(
                        f"scope.themes[{index}] must be one of {sorted(THEMES)}"
                    )
                    continue
                if theme in seen:
                    fails.append(f"scope.themes has duplicate {theme!r}")
                else:
                    seen.append(theme)
            themes = seen

    motion_intensity = None
    dials = _need_map(data.get("dial_values"), "dial_values", fails)
    if dials is not None:
        for key in DIAL_KEYS:
            value = dials.get(key, None)
            if not _is_int(value) or not 1 <= value <= 10:
                fails.append(
                    f"dial_values.{key} must be an integer from 1 to 10 "
                    "(booleans are not integers)"
                )
            elif key == "MOTION_INTENSITY":
                motion_intensity = value

    layout = _need_map(data.get("layout"), "layout", fails)
    if layout is not None:
        _need_str(layout.get("rhythm"), "layout.rhythm", fails)
        regions = layout.get("regions")
        if not isinstance(regions, list) or not regions:
            fails.append("layout.regions must be a nonempty list of strings")
        else:
            for index, region in enumerate(regions):
                _need_str(region, f"layout.regions[{index}]", fails)
        _need_str(layout.get("rationale"), "layout.rationale", fails)

    tokens = _need_map(data.get("tokens"), "tokens", fails)
    if tokens is not None:
        _check_colors(tokens.get("colors"), themes, fails, warns)
        _check_token_map(
            tokens.get("typography"), "tokens.typography", TYPE_KEYS, fails, warns
        )
        _check_token_map(
            tokens.get("spacing"), "tokens.spacing", SPACE_KEYS, fails, warns
        )

    _check_components(data.get("components"), fails)
    has_observed = _check_evidence(data.get("evidence"), fails)
    unknowns = _check_pair_list(
        data.get("unknowns"), "unknowns", "subject", "reason", fails
    )
    _check_pair_list(data.get("exceptions"), "exceptions", "rule", "reason", fails)
    if mode == "reverse-engineer" and not has_observed and not unknowns:
        fails.append(
            "reverse-engineer mode needs at least one Observed evidence record, "
            "or unknown records explaining why no observation was available"
        )
    return motion_intensity


def _check_sections(body: str, fails, warns, motion_intensity: int | None = None) -> None:
    sections = _h2_sections(body)
    for title in REQUIRED_H2:
        if title not in sections:
            fails.append(f"missing required heading ## {title}")
            continue
        content = re.sub(r"\s+", " ", sections[title]).strip()
        if len(content) < SUBSTANTIVE_MIN:
            fails.append(f"## {title} needs substantive content")
    for title in OPTIONAL_H2:
        if title not in sections:
            continue
        content = re.sub(r"\s+", " ", sections[title]).strip()
        if len(content) < SUBSTANTIVE_MIN:
            fails.append(f"## {title} needs substantive content")
    if "Accessibility" not in sections:
        warns.append("## Accessibility absent")
    if (
        motion_intensity is not None
        and motion_intensity >= 4
        and "Motion" not in sections
    ):
        warns.append(
            f"MOTION_INTENSITY is {motion_intensity} (>= 4) but ## Motion is absent"
        )
    checklist = sections.get("Pre-Ship Checklist", "")
    if not checklist:
        return
    found: list[str] = []
    for match in CHECK_RE.finditer(checklist):
        checked = match.group(1).lower() == "x"
        name = match.group(2).strip().rstrip(":").strip()
        rest = match.group(3).strip()
        if name not in CHECKLIST_ITEMS:
            fails.append(f"unknown Pre-Ship Checklist item {name!r}")
            continue
        if name in found:
            fails.append(f"duplicate Pre-Ship Checklist item {name!r}")
            continue
        found.append(name)
        na = re.match(r"(?i)N/A\b(.*)$", rest)
        if na is not None:
            tail = na.group(1).strip()
            if not tail.startswith(":") or not tail[1:].strip():
                fails.append(
                    f"Pre-Ship Checklist item {name!r} is N/A without a reason"
                )
        if not checked:
            warns.append(f"Pre-Ship Checklist item {name!r} is unchecked")
    missing = [name for name in CHECKLIST_ITEMS if name not in found]
    if missing:
        fails.append(
            "Pre-Ship Checklist missing items: " + ", ".join(missing)
        )
    if len(found) != len(CHECKLIST_ITEMS) and not missing:
        fails.append("Pre-Ship Checklist must contain exactly the 12 named items")


def lint_text(text: str) -> tuple[list[str], list[str]]:
    yaml = _import_yaml()
    fails: list[str] = []
    warns: list[str] = []
    yaml_text, body = split_frontmatter(text)
    if yaml_text is None:
        fails.append("missing YAML frontmatter between --- lines")
        _check_sections(body, fails, warns)
        return fails, warns
    try:
        data = yaml.load(yaml_text, Loader=_unique_loader(yaml))
    except yaml.YAMLError as exc:
        fails.append(f"malformed YAML frontmatter: {exc}")
        _check_sections(body, fails, warns)
        return fails, warns
    motion_intensity = _check_frontmatter(data, fails, warns)
    _check_sections(body, fails, warns, motion_intensity)
    return fails, warns


def lint_path(path: Path) -> tuple[list[str], list[str]]:
    path = Path(path)
    if not path.is_file():
        return [f"File not found: {path}"], []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"Cannot read {path}: {exc}"], []
    try:
        return lint_text(text)
    except ImportError as exc:
        return [str(exc)], []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lint DESIGN.md against Output Contract v1"
    )
    parser.add_argument("path", help="Path to DESIGN.md")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()
    try:
        _import_yaml()
    except ImportError:
        print(yaml_install_hint(), file=sys.stderr)
        sys.exit(2)
    fails, warns = lint_path(Path(args.path))
    if args.json:
        print(
            json.dumps(
                {"fails": fails, "warns": warns, "ok": not fails},
                ensure_ascii=False,
            )
        )
    else:
        for item in fails:
            print(f"FAIL  {item}")
        for item in warns:
            print(f"WARN  {item}")
        if not fails and not warns:
            print("DESIGN.md lint clean.")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
