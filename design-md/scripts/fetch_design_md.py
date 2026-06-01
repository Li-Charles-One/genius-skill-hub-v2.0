#!/usr/bin/env python3
"""Fetch a DESIGN.md from awesome-design-md GitHub repo."""
import sys
import urllib.request
import os

BRANDS = {
    "apple": "apple", "claude": "claude", "stripe": "stripe", "vercel": "vercel",
    "figma": "figma", "notion": "notion", "linear": "linear.app", "spotify": "spotify",
    "nike": "nike", "tesla": "tesla", "airbnb": "airbnb", "shopify": "shopify",
    "cursor": "cursor", "supabase": "supabase", "posthog": "posthog",
    "resend": "resend", "mintlify": "mintlify", "raycast": "raycast",
    "webflow": "webflow", "framer": "framer", "miro": "miro",
    "coinbase": "coinbase", "revolut": "revolut", "wise": "wise",
    "ibm": "ibm", "nvidia": "nvidia", "spacex": "spacex",
    "starbucks": "starbucks", "bmw": "bmw", "ferrari": "ferrari",
    "lamborghini": "lamborghini", "uber": "uber", "pinterest": "pinterest",
    "playstation": "playstation", "theverge": "theverge", "wired": "wired",
    "xiai": "x.ai", "ollama": "ollama", "replicate": "replicate",
    "runwayml": "runwayml", "together": "together.ai", "elevenlabs": "elevenlabs",
    "hashicorp": "hashicorp", "mongodb": "mongodb", "sentry": "sentry",
    "sanity": "sanity", "clickhouse": "clickhouse", "composio": "composio",
    "cal": "cal", "intercom": "intercom", "zapier": "zapier",
    "airtable": "airtable", "clay": "clay", "minimax": "minimax",
    "mistral": "mistral.ai", "voltagent": "voltagent", "openai": "openai",
    "binance": "binance", "kraken": "kraken", "mastercard": "mastercard",
    "meta": "meta", "vodafone": "vodafone", "renault": "renault",
    "bugatti": "bugatti", "bmw-m": "bmw-m",
}

BASE_URL = "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md"

def fetch(brand: str, output: str = "DESIGN.md"):
    slug = BRANDS.get(brand.lower(), brand.lower())
    url = f"{BASE_URL}/{slug}/DESIGN.md"
    try:
        urllib.request.urlretrieve(url, output)
        size = os.path.getsize(output)
        print(f"✅ Downloaded {brand} → {output} ({size} bytes)")
    except Exception as e:
        print(f"❌ Failed to fetch '{brand}': {e}")
        print(f"   URL: {url}")
        sys.exit(1)

def list_brands():
    print("Available brands:")
    for name in sorted(BRANDS.keys()):
        print(f"  - {name}")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: fetch_design_md.py <brand> [output_path]")
        print("       fetch_design_md.py --list")
        sys.exit(0)
    if sys.argv[1] == "--list":
        list_brands()
    else:
        brand = sys.argv[1]
        output = sys.argv[2] if len(sys.argv) > 2 else "DESIGN.md"
        fetch(brand, output)
