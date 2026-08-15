#!/usr/bin/env python3
"""Extract font-family, border-radius, and hex color counts from scraped page files."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

FONT = re.compile(r"font-family\s*:\s*([^;}{\n]+)", re.I)
RADIUS = re.compile(r"border-radius\s*:\s*([^;}{\n]+)", re.I)
HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")


def first_font(value: str) -> str:
    first = value.split(",")[0].strip().strip("'\"")
    return first


def load_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() != ".json":
        return raw
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    chunks = []

    def walk(obj):
        if isinstance(obj, str):
            chunks.append(obj)
        elif isinstance(obj, dict):
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)

    walk(data)
    return "\n".join(chunks)


def emit(title: str, counter: Counter, limit: int) -> None:
    print(f"## {title}")
    if not counter:
        print("(none)")
        return
    for value, count in counter.most_common(limit):
        print(f"{count:5}  {value}")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: extract_design_signals.py <file> [file...]")
        sys.exit(0)
    paths = [Path(item) for item in sys.argv[1:]]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        print("Missing file(s): " + ", ".join(missing))
        sys.exit(1)
    text = "\n".join(load_text(path) for path in paths)
    fonts = Counter(font for font in (first_font(match) for match in FONT.findall(text)) if font)
    radii = Counter(match.strip() for match in RADIUS.findall(text) if match.strip())
    hexes = Counter(match.lower() for match in HEX.findall(text))
    emit("fonts", fonts, 8)
    emit("border-radius", radii, 8)
    emit("hex", hexes, 20)
    if not fonts and not radii and not hexes:
        print("No CSS signals found. Infer from rendered copy and mark <!-- inferred -->.")


if __name__ == "__main__":
    main()
