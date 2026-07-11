#!/usr/bin/env python3
"""
Genius AV (视听) — Image / video / audio analysis via OpenAI-compatible multimodal API.

Default provider: Xiaomi MiMo (mimo-v2.5, Token Plan).

Usage:
    python vision.py <file_path_or_url> <mode> [--output json|text] [--model MODEL]

Image modes (6):  describe, ocr, ui-review, chart-data, object-detect, compare
Video modes (4):  video-summary, video-ocr, video-review, video-frame-analysis
Audio modes (4):  audio-summary, audio-transcribe, audio-review, audio-scene
Auto-detect:      video / audio / image by extension (URL path suffix also works)
Compare:          python vision.py img1.png compare --compare-with img2.png

For video/audio, ffprobe duration is injected as ground truth when available.

Environment:
    MIMO_API_KEY / VISION_API_KEY / ARK_API_KEY — API key (first found wins)
    VISION_MODEL   — Model name (default: mimo-v2.5)
    VISION_BASE_URL — API base (default: https://token-plan-cn.xiaomimimo.com/v1)
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
    # ── Audio prompts (MiMo input_audio) ───────────────────────────
    "audio-summary": (
        "Provide a comprehensive understanding of this audio. Structure as:\n"
        "(1) Overall content / topic — what is this audio about?\n"
        "(2) Timeline — key segments with approximate timestamps if possible\n"
        "(3) Speakers / voices — how many, gender/age impression, roles if clear\n"
        "(4) Speech content summary (not full verbatim unless short)\n"
        "(5) Non-speech sounds — music, SFX, ambient noise, silence\n"
        "(6) Tone, emotion, and production quality\n"
        "Be detailed and chronological."
    ),
    "audio-transcribe": (
        "Transcribe ALL speech in this audio verbatim.\n"
        "Rules:\n"
        "- Preserve speaker turns if multiple speakers (Speaker A/B or names if known)\n"
        "- Keep original language; do not translate unless asked\n"
        "- Note [music], [noise], [inaudible], [silence] where relevant\n"
        "- Add approximate timestamps for major segments when possible\n"
        "If no speech is present, say so and briefly describe non-speech audio."
    ),
    "audio-review": (
        "You are a senior audio production reviewer. Analyze this recording.\n"
        "Return a structured review:\n"
        "(1) Content clarity — message, structure, pacing\n"
        "(2) Speech quality — intelligibility, diction, levels\n"
        "(3) Technical quality — noise, clipping, reverb, balance, stereo\n"
        "(4) Music/SFX mix — if present, how well it supports content\n"
        "(5) Specific actionable suggestions for improvement\n"
        "Be constructive and detailed."
    ),
    "audio-scene": (
        "Analyze this audio as an acoustic scene. List:\n"
        "(1) Environment / setting inferred from soundscape\n"
        "(2) Distinct sound events in chronological order with timestamps if possible\n"
        "(3) Music: genre, mood, instruments if identifiable\n"
        "(4) Human activity: speech, footsteps, machinery, etc.\n"
        "(5) Overall atmosphere and what story the soundscape tells\n"
        "Be specific and sensory."
    ),
}

# ── File type detection ───────────────────────────────────────────────

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma", ".opus"}

IMAGE_MODES = {
    "describe", "ocr", "ui-review", "chart-data", "object-detect", "compare",
}
VIDEO_MODES = {
    "video-summary", "video-ocr", "video-review", "video-frame-analysis",
}
AUDIO_MODES = {
    "audio-summary", "audio-transcribe", "audio-review", "audio-scene",
}


def _path_suffix(path_or_url: str) -> str:
    clean = path_or_url.split("?", 1)[0].split("#", 1)[0]
    return Path(clean).suffix.lower()


def media_kind(path_or_url: str) -> str:
    """Return 'video' | 'audio' | 'image' from extension (works for URLs too)."""
    suffix = _path_suffix(path_or_url)
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    return "image"


def is_video(file_path: str) -> bool:
    return media_kind(file_path) == "video"


def is_audio(file_path: str) -> bool:
    return media_kind(file_path) == "audio"


def resolve_mode(mode: str, kind: str) -> str:
    """Map generic modes to media-specific defaults when needed."""
    if kind == "audio":
        if mode in AUDIO_MODES:
            return mode
        if mode in ("describe", "video-summary"):
            return "audio-summary"
        if mode in ("ocr", "video-ocr"):
            return "audio-transcribe"
        if mode in ("ui-review", "video-review"):
            return "audio-review"
        if mode == "object-detect":
            return "audio-scene"
        raise ValueError(
            f"Mode '{mode}' is not for audio. Use: {', '.join(sorted(AUDIO_MODES))}"
        )
    if kind == "video":
        if mode in VIDEO_MODES:
            return mode
        if mode == "describe":
            return "video-summary"
        if mode == "ocr":
            return "video-ocr"
        if mode in IMAGE_MODES - {"describe", "ocr"}:
            # allow image-style modes on video still (model may handle)
            return mode
        if mode in AUDIO_MODES:
            raise ValueError(f"Mode '{mode}' is for audio files, got video")
        return mode
    # image
    if mode in AUDIO_MODES or mode in VIDEO_MODES:
        if mode.startswith("video-") and mode != "video-summary":
            raise ValueError(f"Mode '{mode}' requires a video file")
        if mode in AUDIO_MODES:
            raise ValueError(f"Mode '{mode}' requires an audio file")
    return mode


# ── ffprobe duration ──────────────────────────────────────────────────

def get_media_duration(file_path: str) -> float | None:
    """Get media duration in seconds using ffprobe. Returns None on failure."""
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


def get_video_duration(file_path: str) -> float | None:
    return get_media_duration(file_path)


def format_duration(seconds: float) -> str:
    """Format seconds to mm:ss or hh:mm:ss."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ── API Call ──────────────────────────────────────────────────────────────

KEY_ENV_NAMES = ("MIMO_API_KEY", "VISION_API_KEY", "ARK_API_KEY")
DEFAULT_MODEL = "mimo-v2.5"
DEFAULT_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"


def load_dotenv_map() -> dict:
    """Parse first existing .env into a name→value map."""
    env_paths = [
        Path(__file__).parent / ".env",
        Path.home() / ".hermes" / ".env",
    ]
    out = {}
    for env_path in env_paths:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            out[name.strip()] = value.strip().strip('"').strip("'")
        break
    return out


def load_api_key() -> str:
    """Load API key: per-name env then .env (MIMO > VISION > ARK)."""
    file_keys = load_dotenv_map()
    for name in KEY_ENV_NAMES:
        key = os.environ.get(name) or file_keys.get(name)
        if key:
            return key
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
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".flac": "audio/flac",
        ".m4a": "audio/mp4", ".ogg": "audio/ogg", ".aac": "audio/aac",
        ".wma": "audio/x-ms-wma", ".opus": "audio/opus",
    }
    media_type = media_types.get(suffix, "image/png")

    file_size = path.stat().st_size
    max_size = 50 * 1024 * 1024  # 50MB (MiMo base64 limit)
    if file_size > max_size:
        raise ValueError(
            f"File too large: {file_size / 1024 / 1024:.1f}MB "
            f"(max {max_size / 1024 / 1024:.0f}MB base64). "
            "Compress, trim, or use a public URL (audio URL up to 100MB)."
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
    """Analyze image / video / audio via MiMo multimodal API.

    Auto-detects kind by extension. Local files → base64 data-URI;
    public URLs pass through. Audio uses input_audio; video uses video_url;
    images use image_url.
    """
    api_key = api_key or load_api_key()
    if not api_key:
        raise ValueError(
            "API key not found. Set MIMO_API_KEY (or VISION_API_KEY / ARK_API_KEY) "
            "or create scripts/.env."
        )

    model = model or os.environ.get("VISION_MODEL", DEFAULT_MODEL)
    base_url = (
        base_url or os.environ.get("VISION_BASE_URL", DEFAULT_BASE_URL)
    ).rstrip("/")

    kind = media_kind(media_input)
    # URL without clear extension: infer from mode
    if media_input.startswith(("http://", "https://")) and _path_suffix(media_input) == "":
        if mode in AUDIO_MODES:
            kind = "audio"
        elif mode in VIDEO_MODES or mode.startswith("video-"):
            kind = "video"

    mode = resolve_mode(mode, kind)
    prompt = PROMPTS.get(mode, PROMPTS["describe"])

    is_video_input = kind == "video"
    is_audio_input = kind == "audio"
    timeout = 180 if (is_video_input or is_audio_input) else 60

    actual_duration = None
    is_local = not media_input.startswith(("http://", "https://"))
    if is_local and (is_video_input or is_audio_input):
        actual_duration = get_media_duration(media_input)
        if actual_duration is not None:
            label = "AUDIO" if is_audio_input else "VIDEO"
            dur_str = format_duration(actual_duration)
            prompt = (
                f"[{label} GROUND TRUTH — actual duration: {dur_str} "
                f"({actual_duration:.1f}s), verified by ffprobe. "
                f"Use this as your timing reference for all timestamps.]\n\n"
                + prompt
            )

    content = []

    def media_part(url: str, part_kind: str) -> dict:
        if part_kind == "audio":
            # MiMo audio understanding: type input_audio, field data
            return {
                "type": "input_audio",
                "input_audio": {"data": url},
            }
        if part_kind == "video":
            part = {
                "type": "video_url",
                "video_url": {"url": url},
            }
            if model.startswith("mimo"):
                part["fps"] = float(os.environ.get("VISION_VIDEO_FPS", "2"))
                part["media_resolution"] = os.environ.get(
                    "VISION_VIDEO_RESOLUTION", "default"
                )
            return part
        return {
            "type": "image_url",
            "image_url": {"url": url},
        }

    if media_input.startswith(("http://", "https://")):
        content.append(media_part(media_input, kind))
    else:
        b64_data, mime = encode_file(media_input)
        content.append(media_part(f"data:{mime};base64,{b64_data}", kind))

    if mode == "compare" and compare_with:
        if compare_with.startswith(("http://", "https://")):
            content.append(media_part(compare_with, "image"))
        else:
            b64_data2, mime2 = encode_file(compare_with)
            content.append(media_part(f"data:{mime2};base64,{b64_data2}", "image"))

    content.append({"type": "text", "text": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "api-key": api_key,
        "Content-Type": "application/json",
    }
    max_out = int(os.environ.get("VISION_MAX_TOKENS", "32768"))
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_completion_tokens": max_out,
        "max_tokens": max_out,
    }
    # MiMo: always force deep thinking
    if model.startswith("mimo"):
        payload["thinking"] = {"type": "enabled"}

    if is_video_input or is_audio_input:
        timeout = max(timeout, 300)

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

    message = data["choices"][0]["message"]
    result_text = message.get("content") or ""
    if not result_text and message.get("reasoning_content"):
        result_text = message["reasoning_content"]
    show_think = os.environ.get("VISION_SHOW_THINKING", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
    if show_think and message.get("reasoning_content") and message.get("content"):
        result_text = (
            f"<thinking>\n{message['reasoning_content']}\n</thinking>\n\n"
            f"{message['content']}"
        )

    if (is_video_input or is_audio_input) and actual_duration is not None:
        footer_parts = [f"ffprobe 实测: **{format_duration(actual_duration)}**"]
        dur_patterns = [
            r'(?:total\s+)?duration[:\s]*(\d+)[:：](\d+)(?:[:：](\d+))?',
            r'总时长[：:\s]*(\d+)[:：](\d+)(?:[:：](\d+))?',
            r'(?:视频|音频)\s*时长[：:\s]*(\d+)[:：](\d+)(?:[:：](\d+))?',
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
            footer_parts.append(f"模型声称: `{claimed}`")
        footer_parts.append("（以此为基准校验模型时间戳准确性）")
        result_text += "\n\n---\n⏱ **时长校验** — " + " | ".join(footer_parts)

    return result_text


# ── CLI ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Genius AV (视听) — image/video/audio via MiMo mimo-v2.5"
    )
    parser.add_argument("file", help="Image/video/audio path or URL")
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
