#!/usr/bin/env python3
"""Fetch a DESIGN.md from VoltAgent/awesome-design-md."""
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

SOURCE_URL = "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md"

SLUGS = {
    "airbnb",
    "airtable",
    "apple",
    "binance",
    "bmw",
    "bmw-m",
    "bugatti",
    "cal",
    "claude",
    "clay",
    "clickhouse",
    "cohere",
    "coinbase",
    "composio",
    "cursor",
    "dell-1996",
    "elevenlabs",
    "expo",
    "ferrari",
    "figma",
    "framer",
    "hashicorp",
    "hp",
    "ibm",
    "intercom",
    "kraken",
    "lamborghini",
    "linear.app",
    "lovable",
    "mastercard",
    "meta",
    "minimax",
    "mintlify",
    "miro",
    "mistral.ai",
    "mongodb",
    "nike",
    "notion",
    "nvidia",
    "ollama",
    "opencode.ai",
    "pinterest",
    "playstation",
    "posthog",
    "raycast",
    "renault",
    "replicate",
    "resend",
    "revolut",
    "runwayml",
    "sanity",
    "sentry",
    "shopify",
    "slack",
    "spacex",
    "spotify",
    "starbucks",
    "stripe",
    "supabase",
    "superhuman",
    "tesla",
    "theverge",
    "together.ai",
    "uber",
    "vercel",
    "vodafone",
    "voltagent",
    "warp",
    "webflow",
    "wired",
    "wise",
    "x.ai",
    "zapier",
}

ALIASES = {
    "bmw-m": "bmw-m",
    "bmwm": "bmw-m",
    "cal.com": "cal",
    "cal-com": "cal",
    "calcom": "cal",
    "dell": "dell-1996",
    "dell1996": "dell-1996",
    "linear": "linear.app",
    "mistral": "mistral.ai",
    "mistral-ai": "mistral.ai",
    "opencode": "opencode.ai",
    "opencode-ai": "opencode.ai",
    "opencodeai": "opencode.ai",
    "the-verge": "theverge",
    "together": "together.ai",
    "x.ai": "x.ai",
    "xai": "x.ai",
    "xiai": "x.ai",
}


def normalize(brand: str) -> str:
    return brand.strip().lower().replace(" ", "-").replace("_", "-")


def resolve_slug(brand: str) -> str:
    key = normalize(brand)
    if key in ALIASES:
        return ALIASES[key]
    if key in SLUGS:
        return key
    return key


def looks_like_design_md(text: str) -> bool:
    start = text.lstrip()
    if start.startswith("<!DOCTYPE") or start[:20].lower().startswith("<html"):
        return False
    return start.startswith("---") or start.startswith("#")


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "genius-design/2.1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        status = getattr(response, "status", 200)
        if status >= 400:
            raise OSError(f"HTTP {status}")
        data = response.read()
    text = data.decode("utf-8", errors="replace")
    if not looks_like_design_md(text):
        raise OSError("response is not a DESIGN.md")
    return data


def backup_if_exists(path: Path) -> Optional[Path]:
    if not path.exists() or path.stat().st_size == 0:
        return None
    backup = path.with_name(path.name + ".bak")
    backup.write_bytes(path.read_bytes())
    return backup


def fetch(brand: str, output: str = "DESIGN.md") -> None:
    slug = resolve_slug(brand)
    url = f"{SOURCE_URL}/{slug}/DESIGN.md"
    try:
        data = download(url)
    except (OSError, urllib.error.URLError, TimeoutError) as error:
        print(f"Failed to fetch '{brand}' (slug={slug}) from {url}: {error}")
        sys.exit(1)
    dest = Path(output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    backup = backup_if_exists(dest)
    dest.write_bytes(data)
    extra = f"; backed up {backup}" if backup else ""
    print(f"Downloaded {brand} ({slug}) -> {dest} ({len(data)} bytes){extra}")


def list_brands() -> None:
    print(f"Available brands ({len(SLUGS)}):")
    for slug in sorted(SLUGS):
        print(f"  - {slug}")
    print("Aliases:")
    for alias, slug in sorted(ALIASES.items()):
        if alias != slug:
            print(f"  - {alias} -> {slug}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: fetch_design_md.py <brand> [output_path]")
        print("       fetch_design_md.py --list")
        sys.exit(0)
    if sys.argv[1] == "--list":
        list_brands()
    else:
        fetch(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "DESIGN.md")
