#!/usr/bin/env python3
"""
Genius Vision — Universal image analysis via doubao (豆包) vision API.

Usage:
    python3 vision.py <image_path_or_url> <mode> [--output json|text] [--model MODEL]

Modes: describe, ocr, ui-review, chart-data, object-detect

Environment:
    ARK_API_KEY    — Volcengine Ark API key (required)
    VISION_MODEL   — Model name (default: doubao-seed-2.0-lite)
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Installing httpx...", file=sys.stderr)
    os.system(f"{sys.executable} -m pip install httpx -q")
    import httpx


# ── Prompts ──────────────────────────────────────────────────────────────

PROMPTS = {
    "describe": (
        "Provide a detailed description of this image. Include: main subject, "
        "setting/background, colors/style, any text visible, notable objects, "
        "and overall composition."
    ),
    "ocr": (
        "Extract all text visible in this image verbatim. Preserve structure "
        "and formatting (headers, lists, columns, tables). If no text is found, say so."
    ),
    "ui-review": (
        "You are a senior UI/UX design reviewer. Analyze this interface mockup or design. "
        "Return a structured review:\n"
        "(1) Strengths — what works well\n"
        "(2) Issues — usability or design problems with severity (high/medium/low)\n"
        "(3) Specific actionable suggestions for improvement\n"
        "Be constructive and detailed."
    ),
    "chart-data": (
        "Extract all data from this chart or graph. List: chart type, title, "
        "axis labels, all data points/series with values, and a brief summary "
        "of the trend or key insight."
    ),
    "object-detect": (
        "List all distinct objects, people, animals, and activities in this image. "
        "For each, describe what it is, its approximate location (top-left, center, "
        "bottom-right, etc.), and any notable attributes."
    ),
}


# ── API Call ──────────────────────────────────────────────────────────────

def load_api_key() -> str:
    """Load ARK_API_KEY from env or .env file."""
    key = os.environ.get("ARK_API_KEY")
    if key:
        return key
    # Try .env file
    env_paths = [
        Path(__file__).parent / ".env",
        Path.home() / ".hermes" / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("ARK_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def encode_image(image_path: str) -> tuple[str, str]:
    """Encode local image to base64. Returns (base64_data, media_type)."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    suffix = path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    media_type = media_types.get(suffix, "image/png")

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, media_type


def analyze_image(
    image_input: str,
    mode: str = "describe",
    model: str = None,
    api_key: str = None,
    base_url: str = None,
) -> str:
    """Analyze an image using doubao vision API."""
    api_key = api_key or load_api_key()
    if not api_key:
        raise ValueError("ARK_API_KEY not found. Set env var or create .env file.")

    model = model or os.environ.get("VISION_MODEL", "doubao-seed-2.0-lite")
    base_url = base_url or os.environ.get(
        "VISION_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3"
    )

    prompt = PROMPTS.get(mode, PROMPTS["describe"])

    # Build message content
    content = []

    # Handle URL vs local file — prefer base64 for reliability
    if image_input.startswith(("http://", "https://")):
        # Try URL first, but warn about potential failures
        content.append({
            "type": "image_url",
            "image_url": {"url": image_input}
        })
    else:
        b64_data, media_type = encode_image(image_input)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{media_type};base64,{b64_data}"}
        })

    content.append({"type": "text", "text": prompt})

    # API call
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": content}
        ],
        "max_tokens": 4096,
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        if resp.status_code != 200:
            error_body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
            error_msg = error_body.get("error", {}).get("message", resp.text[:300])
            raise RuntimeError(f"API error {resp.status_code}: {error_msg}")
        data = resp.json()

    return data["choices"][0]["message"]["content"]


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Genius Vision — Image analysis via doubao"
    )
    parser.add_argument("image", help="Image path or URL")
    parser.add_argument(
        "mode",
        nargs="?",
        default="describe",
        choices=list(PROMPTS.keys()),
        help="Analysis mode (default: describe)",
    )
    parser.add_argument(
        "--output", "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Model override (default: from env or doubao-seed-2.0-lite)",
    )
    parser.add_argument(
        "--api-key", "-k",
        default=None,
        help="API key override",
    )
    args = parser.parse_args()

    try:
        result = analyze_image(
            args.image,
            mode=args.mode,
            model=args.model,
            api_key=args.api_key,
        )

        if args.output == "json":
            output = json.dumps({
                "mode": args.mode,
                "image": args.image,
                "result": result,
            }, ensure_ascii=False, indent=2)
        else:
            output = f"## {args.mode.replace('-', ' ').title()} Analysis\n\n{result}"

        print(output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
