#!/usr/bin/env python3
"""Fail closed on mechanically checkable DESIGN.md pre-ship problems."""
import argparse
import re
import sys
from pathlib import Path

CREAM_HEX = {
    "#f5f1ea",
    "#f7f5f1",
    "#fbf8f1",
    "#efeae0",
    "#ece6db",
    "#faf7f1",
    "#e8dfcb",
    "#b08947",
    "#b6553a",
    "#9a2436",
}
BANNED_SERIFS = ("fraunces", "instrument_serif", "instrument serif")
BUZZWORDS = (
    "streamline",
    "empower",
    "supercharge",
    "leverage",
    "unleash",
    "transform",
    "seamless",
    "world-class",
    "enterprise-grade",
    "next-generation",
    "cutting-edge",
    "game-changer",
    "mission-critical",
    "elevate",
    "next-gen",
)


def lint(text: str):
    fails = []
    warns = []
    if "—" in text or "–" in text:
        fails.append("em/en dash present; use commas, colons, or periods")
    if not re.search(r"anti-?patterns", text, re.I):
        fails.append("missing Anti-Patterns section")
    if not re.search(r"pre-?ship|checklist", text, re.I):
        fails.append("missing Pre-Ship Checklist")
    if not re.search(r"DESIGN_VARIANCE|dial_values", text):
        fails.append("missing dial values")
    lower = text.lower()
    cream = [hex_value for hex_value in CREAM_HEX if hex_value in lower]
    if cream:
        fails.append("banned cream/brass hex: " + ", ".join(cream))
    for font in BANNED_SERIFS:
        if font in lower:
            warns.append(f"display serif present: {font} (allowed only if the brand template or brief names it)")
    if re.search(r"\bInter\b", text) and "explicit" not in lower:
        warns.append("Inter present without an explicit-justification cue")
    for word in BUZZWORDS:
        if re.search(rf"\b{re.escape(word)}\b", lower):
            warns.append(f"AI buzzword: {word}")
    if re.search(r"#000000\b", text, re.I):
        warns.append("pure #000000")
    if re.search(r"#ffffff\b", text, re.I):
        warns.append("pure #ffffff")
    return fails, warns


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint a generated DESIGN.md")
    parser.add_argument("path", help="Path to DESIGN.md")
    args = parser.parse_args()
    path = Path(args.path)
    if not path.is_file():
        print(f"File not found: {path}")
        sys.exit(1)
    fails, warns = lint(path.read_text(encoding="utf-8"))
    for item in fails:
        print(f"FAIL  {item}")
    for item in warns:
        print(f"WARN  {item}")
    if fails:
        print(f"{len(fails)} failure(s). Fix before delivering.")
        sys.exit(1)
    if warns:
        print(f"{len(warns)} warning(s). Review before delivering.")
        sys.exit(0)
    print("DESIGN.md lint clean.")


if __name__ == "__main__":
    main()
