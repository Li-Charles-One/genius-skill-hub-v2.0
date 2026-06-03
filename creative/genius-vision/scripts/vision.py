#!/usr/bin/env python3
"""
Genius Vision — Universal image & video analysis via doubao (豆包) vision API.

Usage:
    python vision.py <file_path_or_url> <mode> [--output json|text] [--model MODEL]

Image modes:  describe, ocr, ui-review, chart-data, object-detect, compare
Video modes:  video-summary, video-ocr, video-review
Auto-detect:  .mp4/.mov/.avi/.mkv/.webm → video; otherwise → image
Compare:     python vision.py img1.png compare --compare-with img2.png

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
    "compare": (
        "Compare these two images. List:\n"
        "(1) What is the same in both images\n"
        "(2) What is different between them\n"
        "(3) If applicable, which version is better and why\n"
        "Be specific and objective."
    ),
    # ── Video prompts ──────────────────────────────────────────────
    "video-summary": (
        "Provide a comprehensive summary of this video. Structure your response as:\n"
        "(1) Overall topic / what the video is about\n"
        "(2) Timeline breakdown — key segments with timestamps (approximate)\n"
        "(3) Key people, objects, or scenes shown\n"
        "(4) Any text or captions visible on screen\n"
        "(5) Audio/speech content if discernible\n"
        "(6) Overall tone, style, and production quality\n"
        "Be detailed and chronological."
    ),
    "video-ocr": (
        "Extract ALL text visible anywhere in this video, organized chronologically.\n"
        "For each piece of text, note the approximate timestamp when it appears.\n"
        "Include: presentation slides, captions, subtitles, signs, UI labels, logos, "
        "watermarks, and any overlaid graphics text.\n"
        "If no text is found, say so."
    ),
    "video-review": (
        "You are a senior video production reviewer. Analyze this video or screen recording.\n"
        "Return a structured review:\n"
        "(1) Content & clarity — is the message clear and well-paced?\n"
        "(2) Visual quality — composition, lighting, color, stability\n"
        "(3) Audio quality — clarity, levels, background noise\n"
        "(4) Editing & flow — transitions, pacing, engagement\n"
        "(5) Specific actionable suggestions for improvement\n"
        "Be constructive and detailed."
    ),
}

# ── File type detection ───────────────────────────────────────────────

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}

def is_video(file_path: str) -> bool:
    """Detect if a local file is a video by extension."""
    return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS


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


def encode_file(file_path: str) -> tuple[str, str]:
    """Encode local image or video to base64. Returns (base64_data, media_type)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        ".flv": "video/x-flv",
        ".wmv": "video/x-ms-wmv",
        ".m4v": "video/mp4",
    }
    media_type = media_types.get(suffix, "image/png")

    file_size = path.stat().st_size
    max_size = 50 * 1024 * 1024  # 50MB
    if file_size > max_size:
        raise ValueError(
            f"File too large: {file_size / 1024 / 1024:.1f}MB (max {max_size / 1024 / 1024:.0f}MB). "
            "Consider compressing or trimming the video."
        )

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, media_type


def analyze_media(
    media_input: str,
    mode: str = "describe",
    model: str = None,
    api_key: str = None,
    base_url: str = None,
    compare_with: str = None,
) -> str:
    """Analyze an image or video using doubao vision API.

    Auto-detects video by file extension. Videos use video_url type;
    images use image_url type. Both are base64-encoded for reliability.

    For 'compare' mode, pass a second image via compare_with.
    """
    api_key = api_key or load_api_key()
    if not api_key:
        raise ValueError("ARK_API_KEY not found. Set env var or create .env file.")

    model = model or os.environ.get("VISION_MODEL", "doubao-seed-2.0-lite")
    base_url = base_url or os.environ.get(
        "VISION_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3"
    )

    prompt = PROMPTS.get(mode, PROMPTS["describe"])

    # Detect media type
    is_video_input = not media_input.startswith(("http://", "https://")) and is_video(media_input)
    media_type_name = "video_url" if is_video_input else "image_url"
    timeout = 120 if is_video_input else 60  # videos take longer

    # Build message content
    content = []

    if media_input.startswith(("http://", "https://")):
        # Remote URL — download first, then base64 encode
        try:
            resp = httpx.get(media_input, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/png")
            if "/" not in content_type:
                content_type = "image/png"
            b64_data = base64.b64encode(resp.content).decode("utf-8")
            content.append({
                "type": media_type_name,
                media_type_name: {"url": f"data:{content_type};base64,{b64_data}"}
            })
        except Exception as e:
            raise RuntimeError(f"Failed to download from URL: {e}")
    else:
        # Local file
        b64_data, media_type = encode_file(media_input)
        content.append({
            "type": media_type_name,
            media_type_name: {"url": f"data:{media_type};base64,{b64_data}"}
        })

    # Second image for compare mode
    if mode == "compare" and compare_with:
        b64_data2, media_type2 = encode_file(compare_with)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{media_type2};base64,{b64_data2}"}
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

    with httpx.Client(timeout=timeout) as client:
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
        description="Genius Vision — Image & video analysis via doubao"
    )
    parser.add_argument("file", help="Image/video path or URL")
    parser.add_argument(
        "mode",
        nargs="?",
        default="describe",
        choices=list(PROMPTS.keys()),
        help="Analysis mode (default: describe; video modes: video-summary, video-ocr, video-review)",
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
    parser.add_argument(
        "--compare-with", "-c",
        default=None,
        help="Second image for 'compare' mode",
    )
    args = parser.parse_args()

    try:
        result = analyze_media(
            args.file,
            mode=args.mode,
            model=args.model,
            api_key=args.api_key,
            compare_with=args.compare_with,
        )

        if args.output == "json":
            output = json.dumps({
                "mode": args.mode,
                "file": args.file,
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
