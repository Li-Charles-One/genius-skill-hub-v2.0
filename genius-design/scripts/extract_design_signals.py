#!/usr/bin/env python3
"""Scan CSS/HTML/computed-style captures for candidate design signals.

This is a declaration scanner, not a CSS engine: no cascade, import fetch,
or variable resolution.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
EXPORT_HTML_KEYS = {"rawHtml", "html"}
EXPORT_MARKDOWN_KEYS = {"markdown"}
EXPORT_NEST_KEYS = {"data"}

SCRIPT_BLOCK = re.compile(
    r"<script\b[^>]*>.*?</script>|<script\b[^>]*/>",
    re.I | re.S,
)
UNCLOSED_SCRIPT = re.compile(r"<script\b[^>]*>.*$", re.I | re.S)
STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.I | re.S)
INLINE_STYLE = re.compile(r"\bstyle\s*=\s*(['\"])(.*?)\1", re.I | re.S)
LINK_TAG = re.compile(r"<link\b[^>]*>", re.I)
HREF_ATTR = re.compile(r"\bhref\s*=\s*(['\"])(.*?)\1", re.I)
REL_ATTR = re.compile(r"\brel\s*=\s*(['\"])(.*?)\1", re.I)
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
IMPORT_RE = re.compile(
    r"@import\s+(?:url\s*\(\s*)?['\"]?([^'\"\s)]+)['\"]?",
    re.I,
)
KEYFRAMES_RE = re.compile(r"@keyframes\s+([^{]+)", re.I)
HOVER_RE = re.compile(r":(?:hover|focus|focus-visible|active)\b", re.I)
MOBILE_MEDIA_RE = re.compile(
    r"@media[^{]*\b(?:max-width|min-width|pointer|hover)\b",
    re.I,
)
DECL_RE = re.compile(
    r"(?:^|[;{])\s*(?!https?\b|data\b)(-?[a-zA-Z_][\w-]*)\s*:\s*([^;{}]+)",
    re.M,
)
COLOR_TOKEN = re.compile(
    r"#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b"
    r"|oklch\([^()]*\)"
    r"|oklab\([^()]*\)"
    r"|color-mix\([^()]*\)"
    r"|hsla?\([^()]*\)"
    r"|rgba?\([^()]*\)"
    r"|lch\([^()]*\)"
    r"|lab\([^()]*\)"
    r"|var\s*\(\s*--[^)]+\)",
    re.I,
)
VAR_TOKEN = re.compile(r"var\s*\(\s*--[^)]+\)", re.I)

TYPOGRAPHY = {
    "font",
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "font-stretch",
    "font-variation-settings",
    "font-feature-settings",
    "line-height",
    "letter-spacing",
    "word-spacing",
    "text-align",
    "text-transform",
    "text-decoration",
    "text-underline-offset",
}
LAYOUT = {
    "display",
    "position",
    "flex",
    "flex-direction",
    "flex-wrap",
    "justify-content",
    "align-items",
    "align-content",
    "align-self",
    "grid",
    "grid-template-columns",
    "grid-template-rows",
    "grid-template-areas",
    "grid-gap",
    "gap",
    "row-gap",
    "column-gap",
    "place-items",
    "float",
    "overflow",
    "z-index",
    "width",
    "height",
    "max-width",
    "min-width",
    "max-height",
    "min-height",
    "inset",
    "top",
    "right",
    "bottom",
    "left",
    "border",
    "border-width",
    "border-style",
    "aspect-ratio",
}
SPACING = {
    "margin",
    "margin-top",
    "margin-right",
    "margin-bottom",
    "margin-left",
    "margin-inline",
    "margin-block",
    "padding",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "padding-inline",
    "padding-block",
}
RADIUS = {
    "border-radius",
    "border-top-left-radius",
    "border-top-right-radius",
    "border-bottom-left-radius",
    "border-bottom-right-radius",
}
SHADOW = {"box-shadow", "text-shadow", "filter", "drop-shadow"}
MOTION = {
    "transition",
    "transition-property",
    "transition-duration",
    "transition-timing-function",
    "transition-delay",
    "animation",
    "animation-name",
    "animation-duration",
    "animation-timing-function",
    "animation-delay",
    "animation-iteration-count",
}
COLOR_PROPS = {
    "color",
    "background",
    "background-color",
    "background-image",
    "border-color",
    "border-top-color",
    "border-right-color",
    "border-bottom-color",
    "border-left-color",
    "outline-color",
    "fill",
    "stroke",
    "caret-color",
    "accent-color",
    "text-decoration-color",
    "column-rule-color",
    "box-shadow",
    "text-shadow",
    "border",
    "outline",
}


def _compact(value: str) -> str:
    return " ".join(value.split()).strip()


def _normalize_color(token: str) -> str:
    text = _compact(token)
    if text.startswith("#"):
        return text.lower()
    return text


def _kind_for(prop: str) -> str | None:
    if prop.startswith("--"):
        return "custom-property"
    if prop in MOTION:
        return "motion"
    if prop in RADIUS:
        return "radius"
    if prop in SHADOW:
        return "shadow"
    if prop in TYPOGRAPHY:
        return "typography"
    if prop in SPACING:
        return "spacing"
    if prop in LAYOUT:
        return "layout"
    if prop in COLOR_PROPS:
        return "color"
    return None


def _emit(
    signals: list[dict[str, Any]],
    *,
    source: str,
    file: str,
    kind: str,
    property: str,
    value: str,
    selector: str | None = None,
    viewport: Any = None,
    state: Any = None,
) -> None:
    item: dict[str, Any] = {
        "source": source,
        "file": file,
        "kind": kind,
        "property": property,
        "value": value,
    }
    if selector is not None:
        item["selector"] = selector
    if viewport is not None:
        item["viewport"] = viewport
    if state is not None:
        item["state"] = state
    signals.append(item)


class Scan:
    def __init__(self) -> None:
        self.signals: list[dict[str, Any]] = []
        self.color_counts: Counter[str] = Counter()
        self.external: list[dict[str, str]] = []
        self.unresolved_vars: list[str] = []
        self.saw_hover = False
        self.saw_mobile = False
        self.saw_motion = False
        self.saw_markdown = False
        self.saw_computed = False
        self.file_notes: list[str] = []

    def note_var(self, token: str) -> None:
        compact = _compact(token)
        if compact not in self.unresolved_vars:
            self.unresolved_vars.append(compact)

    def add_external(self, file: str, url: str) -> None:
        url = url.strip()
        if not url:
            return
        item = {"file": file, "url": url}
        if item not in self.external:
            self.external.append(item)

    def add_colors_from(self, value: str, *, count: bool) -> None:
        for raw in COLOR_TOKEN.findall(value):
            token = _normalize_color(raw)
            if VAR_TOKEN.fullmatch(token) or token.lower().startswith("var("):
                self.note_var(token)
            if count:
                self.color_counts[token] += 1

    def mark_css_context(self, text: str, viewport: Any = None) -> None:
        if HOVER_RE.search(text):
            self.saw_hover = True
        if MOBILE_MEDIA_RE.search(text):
            self.saw_mobile = True
        if isinstance(viewport, dict):
            width = viewport.get("width")
            if isinstance(width, (int, float)) and width <= 768:
                self.saw_mobile = True


def strip_scripts(html: str) -> str:
    html = SCRIPT_BLOCK.sub("", html)
    html = UNCLOSED_SCRIPT.sub("", html)
    return html


def stylesheet_hrefs(html: str) -> list[str]:
    hrefs: list[str] = []
    for tag in LINK_TAG.findall(html):
        rel_match = REL_ATTR.search(tag)
        rel = (rel_match.group(2) if rel_match else "").lower().split()
        if "stylesheet" not in rel:
            continue
        href_match = HREF_ATTR.search(tag)
        if href_match:
            hrefs.append(href_match.group(2).strip())
    return hrefs


def scan_css(
    scan: Scan,
    text: str,
    *,
    file: str,
    source: str,
    count_colors: bool,
    selector: str | None = None,
    viewport: Any = None,
    state: Any = None,
) -> None:
    cleaned = CSS_COMMENT.sub("", text)
    scan.mark_css_context(cleaned, viewport)
    for match in IMPORT_RE.finditer(cleaned):
        scan.add_external(file, match.group(1))
    for match in KEYFRAMES_RE.finditer(cleaned):
        name = _compact(match.group(1))
        if name:
            scan.saw_motion = True
            _emit(
                scan.signals,
                source=source,
                file=file,
                kind="motion",
                property="@keyframes",
                value=name,
                selector=selector,
                viewport=viewport,
                state=state,
            )
    for match in DECL_RE.finditer(cleaned):
        prop = match.group(1)
        value = _compact(match.group(2))
        if not value:
            continue
        kind = _kind_for(prop)
        has_color = bool(COLOR_TOKEN.search(value))
        if kind is None and not has_color and not prop.startswith("--"):
            continue
        if kind is None and has_color:
            kind = "color"
        if kind is None:
            continue
        if kind == "motion":
            scan.saw_motion = True
        if VAR_TOKEN.search(value):
            for token in VAR_TOKEN.findall(value):
                scan.note_var(token)
        _emit(
            scan.signals,
            source=source,
            file=file,
            kind=kind,
            property=prop,
            value=value,
            selector=selector,
            viewport=viewport,
            state=state,
        )
        color_prop = prop in COLOR_PROPS or kind == "color" or has_color
        if color_prop:
            scan.add_colors_from(value, count=count_colors)


def scan_html(scan: Scan, html: str, *, file: str, count_colors: bool) -> None:
    stripped = strip_scripts(html)
    for href in stylesheet_hrefs(stripped):
        scan.add_external(file, href)
    for block in STYLE_BLOCK.findall(stripped):
        scan_css(
            scan,
            block,
            file=file,
            source="html-inline",
            count_colors=count_colors,
        )
    remainder = STYLE_BLOCK.sub("", stripped)
    for match in INLINE_STYLE.finditer(remainder):
        scan_css(
            scan,
            match.group(2),
            file=file,
            source="html-inline",
            count_colors=count_colors,
        )


def is_computed_capture(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    elements = data.get("elements")
    if not isinstance(elements, list):
        return False
    if "schema_version" in data or "viewport" in data or "state" in data:
        if not elements:
            return True
    return any(
        isinstance(el, dict) and "selector" in el and "properties" in el
        for el in elements
    )


def collect_export_chunks(
    obj: Any, html_chunks: list[str], md_chunks: list[str]
) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in EXPORT_HTML_KEYS and isinstance(value, str):
                html_chunks.append(value)
            elif key in EXPORT_MARKDOWN_KEYS and isinstance(value, str):
                md_chunks.append(value)
            elif key in EXPORT_NEST_KEYS:
                collect_export_chunks(value, html_chunks, md_chunks)
    elif isinstance(obj, list):
        for item in obj:
            collect_export_chunks(item, html_chunks, md_chunks)


def scan_computed(scan: Scan, data: dict[str, Any], *, file: str) -> None:
    scan.saw_computed = True
    viewport = data.get("viewport")
    state = data.get("state")
    if isinstance(state, str) and HOVER_RE.search(":" + state):
        scan.saw_hover = True
    scan.mark_css_context("", viewport)
    for element in data.get("elements") or []:
        if not isinstance(element, dict):
            continue
        selector = element.get("selector")
        properties = element.get("properties")
        if not isinstance(properties, dict):
            continue
        el_state = element.get("state", state)
        el_viewport = element.get("viewport", viewport)
        if isinstance(el_state, str) and HOVER_RE.search(":" + el_state):
            scan.saw_hover = True
        scan.mark_css_context("", el_viewport)
        for prop, raw in properties.items():
            if not isinstance(prop, str):
                continue
            value = _compact(str(raw))
            kind = _kind_for(prop) or ("color" if COLOR_TOKEN.search(value) else "other")
            if kind == "motion":
                scan.saw_motion = True
            if VAR_TOKEN.search(value):
                for token in VAR_TOKEN.findall(value):
                    scan.note_var(token)
            _emit(
                scan.signals,
                source="computed-style",
                file=file,
                kind=kind,
                property=prop,
                value=value,
                selector=selector if isinstance(selector, str) else None,
                viewport=el_viewport,
                state=el_state,
            )
            if prop in COLOR_PROPS or COLOR_TOKEN.search(value):
                scan.add_colors_from(value, count=False)


def looks_like_html(text: str) -> bool:
    start = text.lstrip()[:200].lower()
    return start.startswith("<!doctype") or start.startswith("<html") or bool(
        re.search(r"</?(?:html|head|body|style|link|div)\b", text[:4000], re.I)
    )


def looks_like_css(text: str) -> bool:
    return bool(DECL_RE.search(CSS_COMMENT.sub("", text))) and not looks_like_html(text)


def process_file(scan: Scan, path: Path, label: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()

    if suffix == ".json" or text.lstrip().startswith("{") or text.lstrip().startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = None
        else:
            if is_computed_capture(data):
                scan_computed(scan, data, file=label)
                return
            html_chunks: list[str] = []
            md_chunks: list[str] = []
            collect_export_chunks(data, html_chunks, md_chunks)
            if html_chunks or md_chunks:
                for chunk in html_chunks:
                    scan_html(scan, chunk, file=label, count_colors=True)
                if md_chunks and not html_chunks:
                    scan.saw_markdown = True
                    scan.file_notes.append(
                        f"{label}: markdown/prose in page export was not treated as CSS evidence"
                    )
                return
            scan.file_notes.append(
                f"{label}: JSON had no computed-style elements and no extractable html/rawHtml/markdown content; "
                "unrelated metadata was not scanned for colors"
            )
            return

    if suffix in {".md", ".markdown", ".txt"}:
        scan.saw_markdown = True
        scan.file_notes.append(
            f"{label}: markdown/prose-only file; body-text hex was not treated as CSS evidence"
        )
        return

    if suffix in {".css"} or (suffix not in {".html", ".htm"} and looks_like_css(text)):
        scan_css(scan, text, file=label, source="css-source", count_colors=True)
        return

    if suffix in {".html", ".htm"} or looks_like_html(text):
        scan_html(scan, text, file=label, count_colors=True)
        return

    scan.file_notes.append(
        f"{label}: no CSS, HTML, or computed-style capture recognized"
    )


def limitations(scan: Scan) -> list[str]:
    notes = [
        "Unresolved var(...) values are not expanded.",
        "External stylesheets are listed but not fetched unless passed as another file argument.",
        "Cascade, specificity, and media/container queries are not resolved.",
        "Color frequencies count candidate occurrences, not visual prominence.",
    ]
    if not scan.saw_hover:
        notes.append("No hover/focus/active state was present in the input.")
    if not scan.saw_mobile:
        notes.append("No mobile/small-viewport evidence was present in the input.")
    if not scan.saw_motion:
        notes.append("No motion (transition/animation/@keyframes) was present in the input.")
    if scan.unresolved_vars:
        notes.append(
            "Unresolved var(...) values observed: " + ", ".join(scan.unresolved_vars)
        )
    if scan.external:
        notes.append(
            "External stylesheets were not downloaded: "
            + ", ".join(item["url"] for item in scan.external)
        )
    notes.extend(scan.file_notes)
    if not scan.signals:
        notes.append("No design signals were found in the supplied files.")
    return notes


def extract(paths: list[tuple[str, Path]]) -> dict[str, Any]:
    scan = Scan()
    for label, path in paths:
        process_file(scan, path, label)
    return {
        "schema_version": SCHEMA_VERSION,
        "files": [label for label, _ in paths],
        "signals": scan.signals,
        "external_stylesheets": scan.external,
        "color_counts": dict(scan.color_counts.most_common()),
        "limitations": limitations(scan),
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print("Usage: extract_design_signals.py <file> [file...]")
        return 0
    pairs = [(item, Path(item)) for item in args]
    missing = [label for label, path in pairs if not path.is_file()]
    if missing:
        print("Missing file(s): " + ", ".join(missing), file=sys.stderr)
        return 1
    payload = extract(pairs)
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
