#!/usr/bin/env python3
"""Fetch a DESIGN.md from VoltAgent, Design.md Store, or Refero Styles."""
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
from design_io import atomic_write_bytes, unique_backup

SOURCE_URL = "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md"
STORE_PACK_URL = "https://designmd-store.com/packs"
STORE_SITEMAP_URL = "https://designmd-store.com/sitemap.xml"
REFERO_API = "https://styles.refero.design/api/styles"
USER_AGENT = "genius-design/2.5"
REFERO_PAGE_DELAY = 0.25
DOWNLOAD_RE = re.compile(r"/api/download/([0-9a-f-]{36})", re.I)
SITEMAP_PACK_RE = re.compile(
    r"https://designmd-store\.com/packs/([a-z0-9-]+)", re.I
)

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

STORE_ALIASES = {
    "booking.com": "booking",
    "bookingcom": "booking",
    "disney+": "disneyplus",
    "disney-plus": "disneyplus",
    "new-york-times": "nytimes",
    "ny-times": "nytimes",
    "next.js": "nextjs",
    "next-js": "nextjs",
    "tailwind": "tailwindcss",
    "the-verge": "theverge",
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


def store_slug(brand: str) -> str:
    key = normalize(brand)
    if key in STORE_ALIASES:
        return STORE_ALIASES[key]
    if key in ALIASES:
        key = ALIASES[key]
    for suffix in (".app", ".ai", ".com"):
        if key.endswith(suffix):
            key = key[: -len(suffix)]
            break
    return key


def looks_like_design_md(text: str) -> bool:
    start = text.lstrip()
    if start.startswith("<!DOCTYPE") or start[:20].lower().startswith("<html"):
        return False
    return start.startswith("---") or start.startswith("#")


def http_get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        status = getattr(response, "status", 200)
        if status >= 400:
            raise OSError(f"HTTP {status}")
        return response.read()


def download_design_md(url: str) -> bytes:
    data = http_get(url)
    text = data.decode("utf-8", errors="replace")
    if not looks_like_design_md(text):
        raise OSError("response is not a DESIGN.md")
    return data


def fetch_voltagent(slug: str) -> bytes:
    return download_design_md(f"{SOURCE_URL}/{slug}/DESIGN.md")


def fetch_store(slug: str) -> bytes:
    html = http_get(f"{STORE_PACK_URL}/{slug}").decode("utf-8", errors="replace")
    match = DOWNLOAD_RE.search(html)
    if not match:
        raise OSError("pack page has no /api/download UUID")
    return download_design_md(
        f"https://designmd-store.com/api/download/{match.group(1)}"
    )


def list_store_packs() -> list[str]:
    xml = http_get(STORE_SITEMAP_URL).decode("utf-8", errors="replace")
    slugs = sorted(set(SITEMAP_PACK_RE.findall(xml)))
    return slugs


def scrub(text: str) -> str:
    return (text or "").replace("\u2014", " - ").replace("\u2013", "-").strip()


def hostname(url: str) -> str:
    host = urlparse(url or "").netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def refero_catalog() -> list[dict]:
    page = 1
    items: list[dict] = []
    while True:
        payload = json.loads(http_get(f"{REFERO_API}?page={page}").decode("utf-8"))
        items.extend(payload.get("styles") or [])
        nxt = payload.get("nextPage")
        if not nxt:
            break
        page = int(nxt)
        time.sleep(REFERO_PAGE_DELAY)
    return items


def refero_match(brand: str, items: list[dict]) -> Optional[dict]:
    key = normalize(brand)
    for item in items:
        if normalize(item.get("siteName") or "") == key:
            return item
    for item in items:
        host = hostname(item.get("url") or "")
        if host == key or host.startswith(key + ".") or host.split(".")[0] == key:
            return item
    if len(key) < 4:
        return None
    for item in items:
        if key in normalize(item.get("siteName") or ""):
            return item
    return None


def yaml_quote(value: str) -> str:
    return json.dumps(scrub(value), ensure_ascii=False)


def synthesize_refero_md(detail: dict) -> bytes:
    style = detail.get("style") or {}
    full = style.get("fullResult") or {}
    ds = full.get("designSystem") or {}
    meta = full.get("meta") or {}
    site = scrub(style.get("siteName") or "Unknown")
    url = scrub(style.get("url") or meta.get("url") or "")
    north = scrub(style.get("northStar") or "")
    extracted = scrub(meta.get("extractedAt") or style.get("createdAt") or "")
    theme = scrub(ds.get("theme") or style.get("colorScheme") or "")
    fonts = ds.get("fonts") or style.get("fonts") or []
    colors = ds.get("colors") or []
    dos = ds.get("dos") or []
    donts = ds.get("donts") or []
    tags = ds.get("tags") or []
    slug = normalize(site) or hostname(url).split(".")[0] or "refero"

    color_yaml = []
    color_rows = []
    for color in colors:
        name = scrub(color.get("name") or color.get("role") or "unnamed")
        hex_value = scrub(color.get("hex") or "")
        role = scrub(color.get("role") or "")
        group = scrub(color.get("group") or "")
        key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "color"
        color_yaml.append(
            f"  {key}:\n    hex: {yaml_quote(hex_value)}\n    role: {yaml_quote(role or group or name)}"
        )
        color_rows.append(f"| {name} | {hex_value} | {role} | {group} |")

    font_list = ", ".join(scrub(font) for font in fonts if font) or "unspecified"
    do_lines = "\n".join(f"- {scrub(item)}" for item in dos) or "- (none listed)"
    dont_lines = "\n".join(f"- {scrub(item)}" for item in donts) or "- (none listed)"
    tag_line = ", ".join(scrub(tag) for tag in tags) or "none"

    body = f"""---
version: alpha
name: {yaml_quote(site)}
slug: {yaml_quote(slug)}
source: {yaml_quote(url)}
extractedAt: {yaml_quote(extracted)}
refero_id: {yaml_quote(style.get("id") or "")}
description: {yaml_quote(north)}
theme: {yaml_quote(theme)}
tags: {yaml_quote(tag_line)}
colors:
{chr(10).join(color_yaml) if color_yaml else "  none: {{}}"}
typography:
  families: {yaml_quote(font_list)}
---

# {site}

Observed from Refero Styles extraction. Not an official brand design system.

**Source:** {url}

**North star (Refero):** {north}

## Colors

| Name | Hex | Role | Group |
|---|---|---|---|
{chr(10).join(color_rows) if color_rows else "| (none) | | | |"}

## Typography

Families observed: {font_list}

## Do's

{do_lines}

## Don'ts

{dont_lines}

## Provenance

- Catalog: Refero Styles (https://styles.refero.design)
- Style id: {style.get("id") or "unknown"}
- Claims above are Observed from Refero's `designSystem` JSON, not live-site facts.
"""
    return body.encode("utf-8")


def fetch_refero(brand: str) -> tuple[bytes, str]:
    items = refero_catalog()
    match = refero_match(brand, items)
    if not match:
        raise OSError(f"no Refero style named '{brand}'")
    detail = json.loads(http_get(f"{REFERO_API}/{match['id']}").decode("utf-8"))
    style = detail.get("style") or {}
    if not style.get("northStar"):
        style["northStar"] = match.get("northStar")
    if not style.get("url"):
        style["url"] = match.get("url")
    detail["style"] = style
    return synthesize_refero_md(detail), scrub(match.get("siteName") or match["id"])


def fetch(brand: str, output: str = "DESIGN.md", source: str = "auto") -> None:
    vt_slug = resolve_slug(brand)
    st_slug = store_slug(brand)
    errors = []
    data = None
    used = None
    used_slug = None

    try_voltagent = source in ("auto", "voltagent")
    try_store = source in ("auto", "store")
    try_refero = source in ("auto", "refero")

    if try_refero:
        try:
            data, used_slug = fetch_refero(brand)
            used = "refero"
        except (OSError, urllib.error.URLError, TimeoutError, ValueError, KeyError) as error:
            errors.append(f"refero {brand}: {error}")
            if source == "refero":
                print(f"Failed to fetch '{brand}' from Refero: {error}")
                sys.exit(1)

    if data is None and try_store:
        try:
            data = fetch_store(st_slug)
            used = "designmd-store"
            used_slug = st_slug
        except (OSError, urllib.error.URLError, TimeoutError) as error:
            errors.append(f"store {st_slug}: {error}")
            if source == "store":
                print(f"Failed to fetch '{brand}' from Design.md Store: {error}")
                sys.exit(1)

    if data is None and try_voltagent:
        try:
            data = fetch_voltagent(vt_slug)
            used = "voltagent"
            used_slug = vt_slug
        except (OSError, urllib.error.URLError, TimeoutError) as error:
            errors.append(f"voltagent {vt_slug}: {error}")
            if source == "voltagent":
                print(f"Failed to fetch '{brand}' from VoltAgent: {error}")
                sys.exit(1)

    if data is None:
        detail = "; ".join(errors) if errors else "unknown error"
        print(f"Failed to fetch '{brand}': {detail}")
        sys.exit(1)

    dest = Path(output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    backup = unique_backup(dest)
    atomic_write_bytes(dest, data)
    extra = f"; backup {backup}" if backup else ""
    print(
        f"Wrote staged catalog snapshot of {brand} ({used_slug}) from {used} -> {dest} "
        f"({len(data)} bytes){extra}. Not a delivered DESIGN.md."
    )


def list_brands() -> None:
    print(f"VoltAgent brands ({len(SLUGS)}):")
    for slug in sorted(SLUGS):
        print(f"  - {slug}")
    print("VoltAgent aliases:")
    for alias, slug in sorted(ALIASES.items()):
        if alias != slug:
            print(f"  - {alias} -> {slug}")
    try:
        store = list_store_packs()
        print(f"Design.md Store packs ({len(store)}):")
        for slug in store:
            print(f"  - {slug}")
    except (OSError, urllib.error.URLError, TimeoutError) as error:
        print(f"Design.md Store packs: unavailable ({error})")
    try:
        refero = refero_catalog()
        print(f"Refero Styles ({len(refero)}):")
        for item in sorted(refero, key=lambda row: (row.get("siteName") or "").lower()):
            host = hostname(item.get("url") or "")
            print(f"  - {item.get('siteName')} ({host})")
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as error:
        print(f"Refero Styles: unavailable ({error})")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: fetch_design_md.py <brand> [output_path]")
        print("       fetch_design_md.py --source voltagent|store|refero <brand> [output_path]")
        print("       fetch_design_md.py --list")
        sys.exit(0)
    source = "auto"
    if "--source" in args:
        index = args.index("--source")
        if index + 1 >= len(args) or args[index + 1] not in (
            "auto",
            "voltagent",
            "store",
            "refero",
        ):
            print("Usage: --source voltagent|store|refero")
            sys.exit(2)
        source = args[index + 1]
        del args[index : index + 2]
    if not args:
        print("Usage: fetch_design_md.py <brand> [output_path]")
        sys.exit(2)
    if args[0] == "--list":
        list_brands()
    else:
        fetch(args[0], args[1] if len(args) > 1 else "DESIGN.md", source=source)
