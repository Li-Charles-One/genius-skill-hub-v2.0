#!/usr/bin/env python3
"""Scan a skill package for secrets, injection-like instructions, and undeclared URLs."""

import argparse
import re
import sys
from pathlib import Path

SKIP_DIR_NAMES = {".git", "__pycache__", "node_modules", ".venv", "venv"}
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".js",
    ".cjs",
    ".mjs",
    ".ts",
    ".json",
    ".yml",
    ".yaml",
    ".txt",
    ".sh",
    ".ps1",
    ".env",
}
SECRET_FILES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519"}
SECRET_SUFFIXES = {".pem", ".p12", ".pfx"}
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
SECRET_VALUES = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgho_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
]
INJECTION = [
    re.compile(r"(?i)ignore (all )?previous instructions"),
    re.compile(r"(?i)do not (tell|inform|reveal) the user"),
    re.compile(r"(?i)hidden instruction"),
    re.compile(r"(?i)you are now (?:a |an |the )?(?:unrestricted|jailbroken)"),
]
ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\ufeff]")
URL = re.compile(r"https?://[^\s)\"'<>]+")
LOCAL_HOSTS = {"example.com", "localhost", "127.0.0.1", "0.0.0.0"}


def iter_files(skill_path):
    for path in skill_path.rglob("*"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.is_file():
            yield path


def is_text(path):
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in SECRET_FILES


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def host_of(url):
    match = re.match(r"https?://([^/]+)", url)
    if not match:
        return ""
    return match.group(1).split(":")[0].lower()


def scan(skill_path):
    skill_path = Path(skill_path)
    findings = []
    declared = ""
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        declared += read_text(skill_md) or ""
    references = skill_path / "references"
    if references.exists():
        for ref in references.rglob("*.md"):
            declared += "\n" + (read_text(ref) or "")

    for path in iter_files(skill_path):
        rel = path.relative_to(skill_path).as_posix()
        if path.name in SECRET_FILES or path.suffix.lower() in SECRET_SUFFIXES:
            findings.append(("HIGH", rel, "secret-like file should not ship in a skill package"))
            continue
        if not is_text(path):
            continue
        text = read_text(path)
        if text is None:
            continue
        if PRIVATE_KEY.search(text):
            findings.append(("HIGH", rel, "private key block"))
        for pattern in SECRET_VALUES:
            if pattern.search(text):
                findings.append(("HIGH", rel, "hardcoded secret-like token"))
                break
        if path.suffix.lower() == ".md":
            for pattern in INJECTION:
                if pattern.search(text):
                    findings.append(("MED", rel, f"injection-like phrase: {pattern.pattern}"))
            if ZERO_WIDTH.search(text):
                findings.append(("MED", rel, "zero-width characters in markdown"))
        if path.suffix.lower() in {".py", ".js", ".cjs", ".mjs", ".ts", ".sh", ".ps1"}:
            for url in URL.findall(text):
                host = host_of(url)
                if not host or host in LOCAL_HOSTS:
                    continue
                if host not in declared.lower() and url not in declared:
                    findings.append(("LOW", rel, f"undeclared URL {url}"))

    return findings


def main():
    parser = argparse.ArgumentParser(description="Security scan a skill package.")
    parser.add_argument("skill_directory", help="Skill directory containing SKILL.md")
    args = parser.parse_args()
    skill_path = Path(args.skill_directory)
    if not skill_path.exists():
        print(f"Skill directory not found: {skill_path}")
        sys.exit(1)

    findings = scan(skill_path)
    if not findings:
        print("Security scan clean.")
        sys.exit(0)

    for level, rel, message in findings:
        print(f"[{level}] {rel}: {message}")
    high_or_med = any(level in {"HIGH", "MED"} for level, _rel, _message in findings)
    sys.exit(1 if high_or_med else 0)


if __name__ == "__main__":
    main()
