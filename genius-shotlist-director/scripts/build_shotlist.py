#!/usr/bin/env python3
"""Assemble a Seedance director's shotlist HTML from JSON + the skill template.

Usage:
  python build_shotlist.py --input scenes.json --out path/to/shotlist.html
  python build_shotlist.py --input scenes.json --out shotlist.html --template ../assets/shotlist-template.html

JSON schema:
{
  "title": "Project Name",
  "style_prefix": "Style: ...\\nLighting: ...",
  "scenes": [
    {
      "number": "1",
      "description": "One-line scene description",
      "prompts": [
        {
          "label": "1a",
          "body": "FULL prompt text including Style Prefix + Characters + Scene + CUTs"
        }
      ]
    }
  ]
}
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path


def _skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _default_template() -> Path:
    return _skill_root() / "assets" / "shotlist-template.html"


def escape_pre(text: str) -> str:
    return html.escape(text, quote=False)


def scene_html(scene: dict) -> str:
    number = str(scene.get("number", "")).strip()
    if not number:
        raise ValueError("Each scene requires a non-empty 'number'")
    desc = str(scene.get("description", "")).strip() or "Untitled scene"
    prompts = scene.get("prompts") or []
    if not prompts:
        raise ValueError(f"Scene {number} has no prompts")

    blocks: list[str] = []
    for p in prompts:
        label = str(p.get("label") or number).strip()
        body = str(p.get("body") or "").rstrip()
        if not body:
            raise ValueError(f"Prompt {label} has empty body")
        blocks.append(
            f"""  <div class="prompt-block">
    <div class="prompt-label">
      <span>Prompt {html.escape(label)} · 15s</span>
      <button class="copy-btn" type="button">Copy</button>
    </div>
    <pre class="prompt">{escape_pre(body)}</pre>
  </div>"""
        )

    joined = "\n".join(blocks)
    return f"""<div class="scene">
  <div class="scene-header">
    <input type="checkbox" data-scene="{html.escape(number, quote=True)}">
    <div class="scene-num">{html.escape(number)}.</div>
    <div class="scene-desc">{html.escape(desc)}</div>
  </div>

{joined}
</div>"""


def build(data: dict, template_text: str) -> str:
    title = str(data.get("title") or "Untitled").strip() or "Untitled"
    style = str(data.get("style_prefix") or "").rstrip()
    if not style:
        raise ValueError("style_prefix is required")
    scenes = data.get("scenes") or []
    if not scenes:
        raise ValueError("scenes must be a non-empty list")

    scenes_html = "\n\n".join(scene_html(s) for s in scenes)
    out = template_text
    out = out.replace("{{PROJECT_TITLE}}", html.escape(title))
    out = out.replace("{{STYLE_PREFIX_TEXT}}", escape_pre(style))
    out = out.replace("{{SCENES_HTML}}", scenes_html)
    if "{{" in out and "}}" in out:
        leftover = [t for t in ("{{PROJECT_TITLE}}", "{{STYLE_PREFIX_TEXT}}", "{{SCENES_HTML}}") if t in out]
        if leftover:
            raise RuntimeError(f"Unreplaced placeholders: {leftover}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Seedance shotlist HTML from JSON")
    parser.add_argument("--input", "-i", required=True, help="Path to scenes JSON")
    parser.add_argument("--out", "-o", required=True, help="Output HTML path")
    parser.add_argument(
        "--template",
        "-t",
        default=None,
        help="Template HTML path (default: skill assets/shotlist-template.html)",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    out_path = Path(args.out)
    template_path = Path(args.template) if args.template else _default_template()

    if not input_path.is_file():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 1
    if not template_path.is_file():
        print(f"error: template not found: {template_path}", file=sys.stderr)
        return 1

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON: {e}", file=sys.stderr)
        return 1

    template_text = template_path.read_text(encoding="utf-8")
    try:
        html_out = build(data, template_text)
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_out, encoding="utf-8", newline="\n")
    print(f"GENIUS_RESULT path={out_path.resolve()} scenes={len(data.get('scenes') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
