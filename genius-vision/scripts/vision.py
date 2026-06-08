#!/usr/bin/env python3
"""
Genius Vision — Universal image & video analysis via doubao (豆包) vision API.

Usage:
    python vision.py <file_path_or_url> <mode> [--output json|text] [--model MODEL]

Image modes (6):  describe, ocr, ui-review, chart-data, object-detect, compare
Video modes (4):  video-summary, video-ocr, video-review, video-frame-analysis
Auto-detect:      .mp4/.mov/.avi/.mkv/.webm → video; otherwise → image
Compare:          python vision.py img1.png compare --compare-with img2.png

For videos, ffprobe is used to get actual duration, which is injected into the
prompt as ground truth and displayed in the output for verification.

Environment:
    ARK_API_KEY    — Volcengine Ark API key (required)
    VISION_MODEL   — Model name (default: doubao-seed-2.0-lite-260428)
"""

import argparse
import base64
import json
import os
import re
import subprocess
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
    # ── Image prompts ──────────────────────────────────────────────
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
        "(2) Timeline breakdown — key segments with timestamps\n"
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
    "video-frame-analysis": (
        "You are a professional storyboard analyst. Analyze this video shot-by-shot "
        "and output a structured storyboard in the EXACT format below.\n\n"
        "CRITICAL RULES:\n"
        "- Output EVERY shot. Do NOT skip or merge shots. Each camera cut = a new shot.\n"
        "- Number shots sequentially starting from 1.\n"
        "- Duration must be in seconds (e.g. 3.5s). Sum of all shot durations must "
        "approximately equal the total video duration given above.\n\n"
        "FOR EACH SHOT, output exactly these 7 fields:\n\n"
        "---\n"
        "## Shot N\n"
        "- **镜号**: N\n"
        "- **时长**: X.Xs\n"
        "- **景别**: 远景/全景/中景/近景/特写/大特写 (pick one)\n"
        "- **画面内容**: Describe exactly what is visible in this shot — subject, "
        "action, composition, lighting, color palette. Be specific and visual.\n"
        "- **摄影机运动**: Static / Pan left-right / Tilt up-down / Zoom in-out / "
        "Dolly / Handheld / Crane / Drone / etc. Describe direction and speed.\n"
        "- **场景**: Where does this shot take place? (e.g. 户外街道/客厅/卧室/产品特写棚)\n"
        "- **对白/旁白**: Transcribe any spoken words verbatim. If none, write '无'.\n"
        "- **屏显文字**: Any text/graphics/subtitles overlaid on screen. If none, write '无'.\n\n"
        "After all shots, append a summary:\n"
        "- **总镜数**: N\n"
        "- **总时长**: X.Xs\n"
        "- **整体风格**: 1-2 sentence style description"
    ),
}

# ── File type detection ───────────────────────────────────────────────

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}


def is_video(file_path: str) -> bool:
    """Detect if a local file is a video by extension."""
    return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS


# ── ffprobe duration ──────────────────────────────────────────────────

def get_video_duration(file_path: str) -> float | None:
    """Get video duration in seconds using ffprobe. Returns None on failure."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", file_path],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass
    return None


def format_duration(seconds: float) -> str:
    """Format seconds to mm:ss or hh:mm:ss."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ── API Call ──────────────────────────────────────────────────────────────

def load_api_key() -> str:
    """Load ARK_API_KEY from env or .env file."""
    key = os.environ.get("ARK_API_KEY")
    if key:
        return key
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
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif",
        ".webp": "image/webp", ".bmp": "image/bmp",
        ".mp4": "video/mp4", ".mov": "video/quicktime",
        ".avi": "video/x-msvideo", ".mkv": "video/x-matroska",
        ".webm": "video/webm", ".flv": "video/x-flv",
        ".wmv": "video/x-ms-wmv", ".m4v": "video/mp4",
    }
    media_type = media_types.get(suffix, "image/png")

    file_size = path.stat().st_size
    max_size = 50 * 1024 * 1024  # 50MB
    if file_size > max_size:
        raise ValueError(
            f"File too large: {file_size / 1024 / 1024:.1f}MB "
            f"(max {max_size / 1024 / 1024:.0f}MB). "
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
    images use image_url type. Both are base64-encoded.

    For videos, ffprobe duration is injected into the prompt as ground truth.
    For 'compare' mode, pass a second image via compare_with.
    """
    api_key = api_key or load_api_key()
    if not api_key:
        raise ValueError("ARK_API_KEY not found. Set env var or create .env file.")

    model = model or os.environ.get("VISION_MODEL", "doubao-seed-2.0-lite-260428")
    base_url = base_url or os.environ.get(
        "VISION_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding/v3"
    )

    prompt = PROMPTS.get(mode, PROMPTS["describe"])

    # Detect media type
    is_video_input = (
        not media_input.startswith(("http://", "https://")) and is_video(media_input)
    )
    media_type_name = "video_url" if is_video_input else "image_url"
    timeout = 180 if is_video_input else 60

    # For video: get ground-truth duration via ffprobe, inject into prompt
    actual_duration = None
    if is_video_input:
        actual_duration = get_video_duration(media_input)
        if actual_duration is not None:
            dur_str = format_duration(actual_duration)
            prompt = (
                f"[VIDEO GROUND TRUTH — actual duration: {dur_str} "
                f"({actual_duration:.1f}s), verified by ffprobe. "
                f"Use this as your timing reference for all timestamps.]\n\n"
                + prompt
            )

    # Build message content
    content = []

    if media_input.startswith(("http://", "https://")):
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
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 4096,
    }

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        if resp.status_code != 200:
            try:
                error_body = resp.json()
                error_msg = error_body.get("error", {}).get("message", resp.text[:300])
            except Exception:
                error_msg = resp.text[:300]
            raise RuntimeError(f"API error {resp.status_code}: {error_msg}")
        data = resp.json()

    result_text = data["choices"][0]["message"]["content"]

    # Duration comparison footer for video modes
    if is_video_input and actual_duration is not None:
        footer_parts = [f"ffprobe 实测: **{format_duration(actual_duration)}**"]
        # Try to extract claimed duration from response
        dur_patterns = [
            r'(?:total\s+)?duration[:\s]*(\d+)[:：](\d+)(?:[:：](\d+))?',
            r'总时长[：:\s]*(\d+)[:：](\d+)(?:[:：](\d+))?',
            r'(?:视频\s*)?时长[：:\s]*(\d+)[:：](\d+)(?:[:：](\d+))?',
        ]
        claimed = None
        for pat in dur_patterns:
            m = re.search(pat, result_text, re.IGNORECASE)
            if m:
                claimed = f"{m.group(1)}:{m.group(2)}"
                if m.group(3):
                    claimed += f":{m.group(3)}"
                break
        if claimed:
            footer_parts.append(f"豆包声称: `{claimed}`")
        footer_parts.append("（以此为基准校验豆包时间戳准确性）")
        result_text += "\n\n---\n⏱ **时长校验** — " + " | ".join(footer_parts)

    return result_text


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
        help="Analysis mode",
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
        help="Model override",
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
