#!/usr/bin/env python3
"""
Genius AV (视听) — Image / video / audio analysis.

Built-in providers:
  cpa     (default) — Gemini native generateContent via CPA
  google            — Official Google Gemini API
  mimo              — Xiaomi MiMo OpenAI-compatible chat.completions

Custom providers: set {NAME}_BASE_URL / {NAME}_API_KEY / {NAME}_MODEL
  and optional {NAME}_API_STYLE=gemini|openai

Usage:
    python vision.py --list-providers
    python vision.py <file_or_url> <mode> [--provider cpa|google|mimo|custom]
    python vision.py https://www.youtube.com/watch?v=... video-summary

Image modes (6):  describe, ocr, ui-review, chart-data, object-detect, compare
Video modes (4):  video-summary, video-ocr, video-review, video-frame-analysis
Audio modes (4):  audio-summary, audio-transcribe, audio-review, audio-scene
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Installing httpx...", file=sys.stderr)
    os.system(f"{sys.executable} -m pip install httpx -q")
    import httpx

# Local base64: leave headroom under MiMo ~50MB encoded limit (×1.33).
MAX_RAW_BYTES = int(os.environ.get("VISION_MAX_RAW_MB", "35")) * 1024 * 1024
# Re-encode local media when larger than this (analysis proxy, not master).
PROXY_TRIGGER_BYTES = int(os.environ.get("VISION_PROXY_TRIGGER_MB", "20")) * 1024 * 1024
PROXY_SCALE = int(os.environ.get("VISION_PROXY_SCALE", "1280"))
PROXY_AUDIO_K = os.environ.get("VISION_PROXY_AUDIO_K", "64k")
# Large still images: max long-edge px for analysis proxy.
PROXY_IMAGE_MAX_EDGE = int(os.environ.get("VISION_PROXY_IMAGE_MAX_EDGE", "2048"))
PROXY_DIR = Path(tempfile.gettempdir()) / "genius-omni-proxy"


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


def is_youtube_url(url: str) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    host = url.split("://", 1)[1].split("/", 1)[0].lower()
    return host in {
        "youtube.com", "www.youtube.com", "m.youtube.com",
        "youtu.be", "www.youtu.be", "music.youtube.com",
    } or "youtube.com" in host


def media_kind(path_or_url: str) -> str:
    """Return 'video' | 'audio' | 'image' from extension (works for URLs too)."""
    if is_youtube_url(path_or_url):
        return "video"
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


# ── Analysis proxies (HEVC GPU → H.264 → CPU; audio AAC; image scale) ──

def _ffmpeg_bin() -> str:
    return os.environ.get("FFMPEG_BIN", "ffmpeg")


def _proxy_dir() -> Path:
    PROXY_DIR.mkdir(parents=True, exist_ok=True)
    return PROXY_DIR


def _encoder_attempts(scale: int | None = None) -> list[tuple[str, list[str]]]:
    """Ordered encoder recipes: HEVC GPU → H.264 GPU → libx264."""
    del scale  # scale applied via -vf in make_video_proxy
    return [
        (
            "hevc_qsv",
            ["-c:v", "hevc_qsv", "-global_quality", "28", "-look_ahead", "0"],
        ),
        (
            "hevc_nvenc",
            ["-c:v", "hevc_nvenc", "-preset", "p1", "-cq", "28", "-b:v", "0"],
        ),
        (
            "hevc_amf",
            ["-c:v", "hevc_amf", "-quality", "speed", "-qp_i", "28", "-qp_p", "28"],
        ),
        (
            "h264_qsv",
            ["-c:v", "h264_qsv", "-global_quality", "28", "-look_ahead", "0"],
        ),
        (
            "h264_nvenc",
            ["-c:v", "h264_nvenc", "-preset", "p1", "-cq", "28", "-b:v", "0"],
        ),
        (
            "h264_amf",
            ["-c:v", "h264_amf", "-quality", "speed", "-qp_i", "28", "-qp_p", "28"],
        ),
        (
            "libx264",
            ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "32"],
        ),
    ]


def make_video_proxy(
    src: str,
    scale: int | None = None,
) -> tuple[str, str]:
    """Build a smaller video analysis proxy. Returns (path, encoder_name).

    Preference: HEVC GPU → H.264 GPU → libx264. Requires ffmpeg on PATH.
    """
    scale = scale or PROXY_SCALE
    src_path = Path(src)
    if not src_path.is_file():
        raise FileNotFoundError(f"File not found: {src}")

    out_dir = _proxy_dir()
    stamp = int(time.time() * 1000)
    last_err = ""

    for name, vcodec in _encoder_attempts(scale):
        out = out_dir / f"{src_path.stem}.{stamp}.{name}.mp4"
        cmd = [
            _ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src_path),
            "-vf", f"scale={scale}:-2",
            *vcodec,
            "-c:a", "aac", "-b:a", PROXY_AUDIO_K,
            "-movflags", "+faststart",
            str(out),
        ]
        try:
            t0 = time.perf_counter()
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            elapsed = time.perf_counter() - t0
            if proc.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
                last_err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
                if out.exists():
                    out.unlink(missing_ok=True)
                continue
            size = out.stat().st_size
            print(
                f"[genius-omni] video proxy via {name}: "
                f"{size / 1024 / 1024:.1f}MB in {elapsed:.1f}s → {out}",
                file=sys.stderr,
            )
            if size > MAX_RAW_BYTES:
                print(
                    f"[genius-omni] proxy still {size / 1024 / 1024:.1f}MB "
                    f"(>{MAX_RAW_BYTES / 1024 / 1024:.0f}MB), trying next encoder…",
                    file=sys.stderr,
                )
                continue
            return str(out), name
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            last_err = str(e)
            if out.exists():
                out.unlink(missing_ok=True)
            continue

    if scale > 720:
        return make_video_proxy(src, scale=720)

    raise RuntimeError(
        f"Failed to build video proxy (HEVC/H.264 GPU → libx264). Last error: {last_err[:400]}"
    )


def _make_video_proxy_h264_only(src: str, scale: int | None = None) -> tuple[str, str]:
    """H.264-only video proxy for API codec fallback."""
    scale = scale or PROXY_SCALE
    src_path = Path(src)
    out_dir = _proxy_dir()
    stamp = int(time.time() * 1000)
    h264_chain = [c for c in _encoder_attempts() if c[0].startswith("h264") or c[0] == "libx264"]
    last_err = ""
    for name, vcodec in h264_chain:
        out = out_dir / f"{src_path.stem}.{stamp}.{name}.mp4"
        cmd = [
            _ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src_path),
            "-vf", f"scale={scale}:-2",
            *vcodec,
            "-c:a", "aac", "-b:a", PROXY_AUDIO_K,
            "-movflags", "+faststart",
            str(out),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if proc.returncode == 0 and out.is_file() and out.stat().st_size > 0:
                print(
                    f"[genius-omni] video proxy via {name}: "
                    f"{out.stat().st_size / 1024 / 1024:.1f}MB → {out}",
                    file=sys.stderr,
                )
                return str(out), name
            last_err = (proc.stderr or f"exit {proc.returncode}").strip()
            if out.exists():
                out.unlink(missing_ok=True)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            last_err = str(e)
    if scale > 720:
        return _make_video_proxy_h264_only(src, scale=720)
    raise RuntimeError(f"H.264 proxy failed: {last_err[:400]}")


def make_audio_proxy(src: str) -> tuple[str, str]:
    """Re-encode large audio to AAC m4a for base64 upload. Returns (path, codec)."""
    src_path = Path(src)
    if not src_path.is_file():
        raise FileNotFoundError(f"File not found: {src}")
    out = _proxy_dir() / f"{src_path.stem}.{int(time.time() * 1000)}.proxy.m4a"
    cmd = [
        _ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src_path),
        "-vn", "-c:a", "aac", "-b:a", PROXY_AUDIO_K,
        str(out),
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
        if out.exists():
            out.unlink(missing_ok=True)
        err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        raise RuntimeError(f"Audio proxy failed: {err[:400]}")
    print(
        f"[genius-omni] audio proxy aac/{PROXY_AUDIO_K}: "
        f"{out.stat().st_size / 1024 / 1024:.1f}MB in {time.perf_counter() - t0:.1f}s → {out}",
        file=sys.stderr,
    )
    if out.stat().st_size > MAX_RAW_BYTES:
        # second pass lower rate
        out2 = _proxy_dir() / f"{src_path.stem}.{int(time.time() * 1000)}.proxy32.m4a"
        cmd2 = [
            _ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src_path),
            "-vn", "-c:a", "aac", "-b:a", "32k", "-ac", "1",
            str(out2),
        ]
        proc2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=600)
        if proc2.returncode == 0 and out2.is_file() and out2.stat().st_size > 0:
            out.unlink(missing_ok=True)
            print(
                f"[genius-omni] audio proxy aac/32k mono: "
                f"{out2.stat().st_size / 1024 / 1024:.1f}MB → {out2}",
                file=sys.stderr,
            )
            return str(out2), "aac-32k"
    return str(out), "aac"


def make_image_proxy(src: str, max_edge: int | None = None) -> tuple[str, str]:
    """Downscale large still image to JPEG for base64 upload. Returns (path, tag)."""
    max_edge = max_edge or PROXY_IMAGE_MAX_EDGE
    src_path = Path(src)
    if not src_path.is_file():
        raise FileNotFoundError(f"File not found: {src}")
    out = _proxy_dir() / f"{src_path.stem}.{int(time.time() * 1000)}.proxy.jpg"
    # scale so long edge <= max_edge; always re-encode jpeg q=3 (~high quality)
    vf = (
        f"scale='if(gt(iw\\,ih)\\,min({max_edge}\\,iw)\\,-2)':"
        f"'if(gt(ih\\,iw)\\,min({max_edge}\\,ih)\\,-2)'"
    )
    cmd = [
        _ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src_path),
        "-vf", vf,
        "-frames:v", "1",
        "-q:v", "3",
        str(out),
    ]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
        if out.exists():
            out.unlink(missing_ok=True)
        err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()
        raise RuntimeError(f"Image proxy failed: {err[:400]}")
    print(
        f"[genius-omni] image proxy max_edge={max_edge}: "
        f"{out.stat().st_size / 1024 / 1024:.1f}MB in {time.perf_counter() - t0:.1f}s → {out}",
        file=sys.stderr,
    )
    if out.stat().st_size > MAX_RAW_BYTES and max_edge > 1280:
        return make_image_proxy(src, max_edge=1280)
    return str(out), f"jpeg-{max_edge}"


def ensure_media_under_limit(
    path: str,
    kind: str,
    force_proxy: bool = False,
    prefer_h264: bool = False,
) -> str:
    """Return path suitable for base64 upload; may create analysis proxy."""
    p = Path(path)
    size = p.stat().st_size
    needs = force_proxy or size > PROXY_TRIGGER_BYTES or size > MAX_RAW_BYTES
    if not needs:
        return path

    reason = "forced" if force_proxy else f"{size / 1024 / 1024:.1f}MB > trigger"
    if kind == "video":
        print(f"[genius-omni] compressing video ({reason})…", file=sys.stderr)
        if prefer_h264:
            proxy, _ = _make_video_proxy_h264_only(path)
        else:
            proxy, _ = make_video_proxy(path)
        return proxy
    if kind == "audio":
        print(f"[genius-omni] compressing audio ({reason})…", file=sys.stderr)
        proxy, _ = make_audio_proxy(path)
        return proxy
    if kind == "image":
        print(f"[genius-omni] compressing image ({reason})…", file=sys.stderr)
        proxy, _ = make_image_proxy(path)
        return proxy
    return path


# ── API Call ──────────────────────────────────────────────────────────────
#
# Built-in packs + any custom provider via env:
#   VISION_PROVIDER=myrelay
#   MYRELAY_BASE_URL=https://...
#   MYRELAY_API_KEY=...
#   MYRELAY_MODEL=...
#   MYRELAY_API_STYLE=gemini|openai   # optional; auto if omitted
#
# api_style:
#   gemini  → /v1beta/models/{model}:generateContent (inline_data / YouTube file_data)
#   openai  → /chat/completions (image_url / video_url / input_audio)

BUILTIN_PROVIDERS = {
    "cpa": {
        "base_url": "https://cpa-jp.charles-ai.space/v1",
        "model": "gemini-3.6-flash-high",
        "api_style": "gemini",
        "key_envs": ("CPA_API_KEY", "VISION_CPA_API_KEY", "VISION_API_KEY"),
        "note": "CPA Gemini relay (native generateContent)",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1",
        "model": "gemini-3.6-flash",
        "api_style": "gemini",
        "key_envs": ("GOOGLE_API_KEY", "GEMINI_API_KEY", "VISION_API_KEY"),
        "note": "Official Google Gemini API",
    },
    "mimo": {
        "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
        "model": "mimo-v2.5",
        "api_style": "openai",
        "key_envs": ("MIMO_API_KEY", "VISION_API_KEY", "ARK_API_KEY"),
        "note": "Xiaomi MiMo Token Plan (OpenAI-compatible)",
    },
}
# Back-compat alias used by older docs / imports
PROVIDERS = BUILTIN_PROVIDERS
DEFAULT_PROVIDER = "cpa"
DEFAULT_MODEL = BUILTIN_PROVIDERS[DEFAULT_PROVIDER]["model"]
DEFAULT_BASE_URL = BUILTIN_PROVIDERS[DEFAULT_PROVIDER]["base_url"]


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


def _env_or_file(name: str, file_keys: dict) -> str:
    return (os.environ.get(name) or file_keys.get(name) or "").strip()


def _infer_api_style(pid: str, model: str, base_url: str) -> str:
    """Heuristic when API style not set explicitly."""
    m = (model or "").lower()
    b = (base_url or "").lower()
    if pid in ("cpa", "google"):
        return "gemini"
    if "generativelanguage.googleapis.com" in b or "googleapis.com/v1beta" in b:
        return "gemini"
    if m.startswith("gemini") and ("charles-ai" in b or "googleapis" in b or "mimo" not in b):
        # Gemini on Google-like hosts → native; pure OpenAI relays may still need openai
        if "openrouter" in b or "openai.com" in b or "api.openai.com" in b:
            return "openai"
        if "googleapis" in b or "charles-ai" in b or pid == "cpa":
            return "gemini"
    if m.startswith("mimo") or "xiaomimimo" in b:
        return "openai"
    return "openai"


def provider_conf(pid: str | None = None) -> dict:
    """Resolve full provider config (builtin or custom env pack)."""
    file_keys = load_dotenv_map()
    pid = (pid or resolve_provider(None)).strip().lower()
    p = pid.upper()
    builtin = BUILTIN_PROVIDERS.get(pid, {})

    base_url = (
        _env_or_file(f"{p}_BASE_URL", file_keys)
        or (builtin.get("base_url") or "")
    )
    model = (
        _env_or_file(f"{p}_MODEL", file_keys)
        or (builtin.get("model") or "")
    )
    style = (
        _env_or_file(f"{p}_API_STYLE", file_keys)
        or _env_or_file("VISION_API_STYLE", file_keys)
        or builtin.get("api_style")
        or ""
    ).strip().lower()

    key_envs = list(builtin.get("key_envs") or ())
    # Always accept {PID}_API_KEY and VISION_API_KEY
    for extra in (f"{p}_API_KEY", "VISION_API_KEY"):
        if extra not in key_envs:
            key_envs.append(extra)

    if not style:
        style = _infer_api_style(pid, model, base_url)
    if style not in ("gemini", "openai"):
        raise ValueError(
            f"Invalid API style '{style}' for provider '{pid}'. Use gemini or openai."
        )

    if not base_url or not model:
        if pid not in BUILTIN_PROVIDERS:
            raise ValueError(
                f"Unknown provider '{pid}'. Built-ins: {', '.join(sorted(BUILTIN_PROVIDERS))}. "
                f"For a custom provider set {p}_BASE_URL, {p}_API_KEY, {p}_MODEL "
                f"(optional {p}_API_STYLE=gemini|openai)."
            )
        if not base_url:
            base_url = builtin["base_url"]
        if not model:
            model = builtin["model"]

    return {
        "id": pid,
        "base_url": base_url.rstrip("/"),
        "model": model,
        "api_style": style,
        "key_envs": tuple(key_envs),
        "note": builtin.get("note") or f"custom provider '{pid}'",
        "builtin": pid in BUILTIN_PROVIDERS,
    }


def list_providers() -> list[dict]:
    """Return builtin packs + active custom if configured."""
    file_keys = load_dotenv_map()
    rows = []
    for pid, conf in BUILTIN_PROVIDERS.items():
        live = provider_conf(pid)
        rows.append({
            "id": pid,
            "builtin": True,
            "model": live["model"],
            "base_url": live["base_url"],
            "api_style": live["api_style"],
            "note": conf.get("note", ""),
            "has_key": bool(load_api_key(pid)),
        })
    # surface active custom provider if not builtin
    active = resolve_provider(None)
    if active not in BUILTIN_PROVIDERS:
        live = provider_conf(active)
        rows.append({
            "id": active,
            "builtin": False,
            "model": live["model"],
            "base_url": live["base_url"],
            "api_style": live["api_style"],
            "note": live["note"],
            "has_key": bool(load_api_key(active)),
        })
    return rows


def resolve_provider(name: str | None = None) -> str:
    """Resolve provider id: arg → VISION_PROVIDER → default (cpa).

    Explicit CLI/name is always accepted (config validated later).
    Env-only custom ids need {ID}_BASE_URL (and model/key) in env/.env.
    """
    file_keys = load_dotenv_map()
    explicit = name is not None and str(name).strip() != ""
    raw = name or _env_or_file("VISION_PROVIDER", file_keys) or DEFAULT_PROVIDER
    pid = str(raw).strip().lower() or DEFAULT_PROVIDER
    if pid in BUILTIN_PROVIDERS or explicit:
        return pid
    # Env-selected custom: require minimal pack definition
    p = pid.upper()
    has_base = bool(_env_or_file(f"{p}_BASE_URL", file_keys))
    has_model = bool(
        _env_or_file(f"{p}_MODEL", file_keys)
        or _env_or_file("VISION_MODEL", file_keys)
    )
    has_key = bool(
        _env_or_file(f"{p}_API_KEY", file_keys)
        or _env_or_file("VISION_API_KEY", file_keys)
    )
    if not (has_base and (has_model or has_key)):
        known = ", ".join(sorted(BUILTIN_PROVIDERS))
        raise ValueError(
            f"Unknown provider '{pid}'. Built-ins: {known}. "
            f"Or define custom: {p}_BASE_URL + {p}_API_KEY + {p}_MODEL "
            f"(optional {p}_API_STYLE=gemini|openai)."
        )
    return pid


def load_api_key(provider: str | None = None) -> str:
    """Load API key for active provider (env then .env)."""
    file_keys = load_dotenv_map()
    conf = provider_conf(provider)
    for env_name in conf["key_envs"]:
        key = _env_or_file(env_name, file_keys)
        if key:
            return key
    return ""


def resolve_endpoint(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> tuple[str, str, str, str]:
    """Return (provider_id, base_url, model, api_key).

    Precedence: CLI → {PROVIDER}_* → VISION_* (only for active provider) → pack defaults.
    """
    file_keys = load_dotenv_map()
    pid = resolve_provider(provider)
    conf = provider_conf(pid)
    p = pid.upper()
    active_pid = resolve_provider(None)

    def pick(cli_val: str | None, prov_env: str, global_env: str, default: str) -> str:
        if cli_val:
            return cli_val
        prov = _env_or_file(prov_env, file_keys)
        if prov:
            return prov
        if pid == active_pid:
            glob = _env_or_file(global_env, file_keys)
            if glob:
                return glob
        return default

    resolved_model = pick(model, f"{p}_MODEL", "VISION_MODEL", conf["model"])
    resolved_base = pick(base_url, f"{p}_BASE_URL", "VISION_BASE_URL", conf["base_url"])
    resolved_key = api_key or load_api_key(pid)
    return pid, resolved_base.rstrip("/"), resolved_model, resolved_key


def resolve_api_style(
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> str:
    conf = provider_conf(provider)
    if model or base_url:
        return _infer_api_style(
            conf["id"],
            model or conf["model"],
            base_url or conf["base_url"],
        ) if not (
            _env_or_file(f"{conf['id'].upper()}_API_STYLE", load_dotenv_map())
            or _env_or_file("VISION_API_STYLE", load_dotenv_map())
            or BUILTIN_PROVIDERS.get(conf["id"], {}).get("api_style")
        ) else conf["api_style"]
    return conf["api_style"]


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
    if file_size > MAX_RAW_BYTES:
        raise ValueError(
            f"File too large: {file_size / 1024 / 1024:.1f}MB "
            f"(max ~{MAX_RAW_BYTES / 1024 / 1024:.0f}MB raw for base64). "
            "vision.py auto-proxies oversize local media "
            f"(>{PROXY_TRIGGER_BYTES / 1024 / 1024:.0f}MB): "
            "video HEVC→H.264, audio AAC, image JPEG downscale. "
            "Or pass a public URL (video ≤300MB, audio ≤100MB)."
        )

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, media_type


def _gemini_api_root(base_url: str) -> str:
    """Map OpenAI-style .../v1 base to host root for /v1beta/... routes."""
    u = base_url.rstrip("/")
    if u.endswith("/v1"):
        return u[: -len("/v1")]
    if u.endswith("/v1beta/openai"):
        return u[: -len("/v1beta/openai")]
    if u.endswith("/openai"):
        return u[: -len("/openai")]
    return u


def _http_proxy() -> str | None:
    return (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("ALL_PROXY")
        or os.environ.get("all_proxy")
        or None
    )


def _gemini_inline_part(path: str, part_kind: str) -> dict:
    b64, mime = encode_file(path)
    return {"inline_data": {"mime_type": mime, "data": b64}}


def _gemini_media_part(path_or_url: str, part_kind: str) -> dict:
    if is_youtube_url(path_or_url):
        return {
            "file_data": {
                "file_uri": path_or_url,
                "mime_type": "video/*",
            }
        }
    if path_or_url.startswith(("http://", "https://")):
        # Public direct media URL via file_data (best-effort on CPA)
        mime = {
            "image": "image/jpeg",
            "video": "video/mp4",
            "audio": "audio/mpeg",
        }.get(part_kind, "application/octet-stream")
        suffix = _path_suffix(path_or_url)
        if suffix:
            try:
                # reuse encode_file mime table via a dummy — map common suffixes
                mime_map = {
                    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                    ".gif": "image/gif", ".webp": "image/webp",
                    ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
                    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
                    ".flac": "audio/flac", ".ogg": "audio/ogg",
                }
                mime = mime_map.get(suffix, mime)
            except Exception:
                pass
        return {"file_data": {"file_uri": path_or_url, "mime_type": mime}}
    return _gemini_inline_part(path_or_url, part_kind)


def _extract_gemini_text(data: dict, show_think: bool = False) -> str:
    texts = []
    thoughts = []
    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            if not isinstance(part, dict):
                continue
            if part.get("text"):
                if part.get("thought"):
                    thoughts.append(part["text"])
                else:
                    texts.append(part["text"])
    result = "\n".join(texts).strip()
    if not result and thoughts:
        result = "\n".join(thoughts).strip()
    if show_think and thoughts and texts:
        result = (
            "<thinking>\n" + "\n".join(thoughts) + "\n</thinking>\n\n" + "\n".join(texts)
        )
    if result:
        return result
    # fallback OpenAI-shaped (some gateways)
    try:
        msg = data["choices"][0]["message"]
        return msg.get("content") or msg.get("reasoning_content") or ""
    except Exception:
        pass
    err = data.get("error") or {}
    if err:
        raise RuntimeError(f"API error: {err.get('message') or err}")
    raise RuntimeError(f"Empty model response: {json.dumps(data, ensure_ascii=False)[:300]}")


def analyze_media(
    media_input: str,
    mode: str = "describe",
    model: str = None,
    api_key: str = None,
    base_url: str = None,
    provider: str = None,
    compare_with: str = None,
    force_proxy: bool = False,
) -> str:
    """Analyze image / video / audio.

    CPA/Gemini: native /v1beta/models/{model}:generateContent
      - local → inline_data base64
      - YouTube → file_data.file_uri
    MiMo: OpenAI-compatible /chat/completions
    """
    _provider, base_url, model, api_key = resolve_endpoint(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
    if not api_key:
        conf = PROVIDERS[_provider]
        key_hint = " / ".join(conf["key_envs"])
        raise ValueError(
            f"API key not found for provider '{_provider}'. "
            f"Set {key_hint} or create scripts/.env."
        )

    conf = provider_conf(_provider)
    # Prefer explicit pack style; allow one-shot override via env already in conf.
    # If user only overrides model/base, keep pack style unless conf has no style.
    use_gemini_native = conf["api_style"] == "gemini"

    kind = media_kind(media_input)
    # URL without clear extension: infer from mode (skip YouTube — always video)
    if (
        media_input.startswith(("http://", "https://"))
        and _path_suffix(media_input) == ""
        and not is_youtube_url(media_input)
    ):
        if mode in AUDIO_MODES:
            kind = "audio"
        elif mode in VIDEO_MODES or mode.startswith("video-"):
            kind = "video"

    mode = resolve_mode(mode, kind)
    prompt = PROMPTS.get(mode, PROMPTS["describe"])

    is_video_input = kind == "video"
    is_audio_input = kind == "audio"
    timeout = 180 if (is_video_input or is_audio_input) else 60
    # CPA/Gemini local video: prefer H.264 for broader decoder support
    prefer_h264 = use_gemini_native

    actual_duration = None
    is_local = not media_input.startswith(("http://", "https://"))
    is_yt = is_youtube_url(media_input)
    upload_path = media_input

    if is_local:
        try:
            # --force-proxy is video-oriented; audio/image still size-trigger
            upload_path = ensure_media_under_limit(
                media_input,
                kind=kind,
                force_proxy=bool(force_proxy and is_video_input),
                prefer_h264=prefer_h264,
            )
        except Exception as e:
            if Path(media_input).stat().st_size > MAX_RAW_BYTES:
                raise
            print(f"[genius-omni] proxy skipped: {e}", file=sys.stderr)
            upload_path = media_input

    if is_local and (is_video_input or is_audio_input):
        # Duration from original when possible (proxy may re-mux)
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

    if is_video_input or is_audio_input:
        timeout = max(timeout, 300)

    show_think = os.environ.get("VISION_SHOW_THINKING", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
    max_out = int(os.environ.get("VISION_MAX_TOKENS", "32768"))
    proxy = _http_proxy()

    # ── CPA / Gemini native generateContent ──────────────────────────
    if use_gemini_native:
        def build_gemini_parts(path_or_url: str) -> list:
            parts = [_gemini_media_part(path_or_url, kind)]
            if mode == "compare" and compare_with:
                parts.append(_gemini_media_part(compare_with, "image"))
            parts.append({"text": prompt})
            return parts

        def post_gemini(parts: list) -> dict:
            root = _gemini_api_root(base_url)
            endpoint = f"{root}/v1beta/models/{model}:generateContent"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            }
            body = {
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {
                    "maxOutputTokens": max_out,
                },
            }
            with httpx.Client(timeout=timeout, proxy=proxy) as client:
                resp = client.post(endpoint, headers=headers, json=body)
                if resp.status_code != 200:
                    try:
                        error_body = resp.json()
                        error_msg = (
                            error_body.get("error", {}).get("message")
                            or resp.text[:300]
                        )
                    except Exception:
                        error_msg = resp.text[:300]
                    raise RuntimeError(f"API error {resp.status_code}: {error_msg}")
                return resp.json()

        path_for_api = upload_path if is_local else media_input
        try:
            data = post_gemini(build_gemini_parts(path_for_api))
            result_text = _extract_gemini_text(data, show_think=show_think)
        except RuntimeError as e:
            err = str(e)
            can_retry = (
                is_local
                and is_video_input
                and ("400" in err or "Param" in err or "Invalid" in err
                     or "corrupted" in err.lower() or "decode" in err.lower())
            )
            if not can_retry:
                raise
            print(
                f"[genius-omni] API failed ({err[:120]}); "
                "retrying with H.264 video proxy…",
                file=sys.stderr,
            )
            proxy_path, enc = _make_video_proxy_h264_only(media_input)
            print(f"[genius-omni] fallback encoder={enc}", file=sys.stderr)
            data = post_gemini(build_gemini_parts(proxy_path))
            result_text = _extract_gemini_text(data, show_think=show_think)

    # ── MiMo / OpenAI-compatible chat.completions ────────────────────
    else:
        def media_part(url: str, part_kind: str) -> dict:
            if part_kind == "audio":
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

        def build_content(path_or_url: str) -> list:
            parts = []
            if path_or_url.startswith(("http://", "https://")):
                parts.append(media_part(path_or_url, kind))
            else:
                b64_data, mime = encode_file(path_or_url)
                parts.append(media_part(f"data:{mime};base64,{b64_data}", kind))

            if mode == "compare" and compare_with:
                if compare_with.startswith(("http://", "https://")):
                    parts.append(media_part(compare_with, "image"))
                else:
                    b64_data2, mime2 = encode_file(compare_with)
                    parts.append(media_part(f"data:{mime2};base64,{b64_data2}", "image"))

            parts.append({"type": "text", "text": prompt})
            return parts

        content = build_content(upload_path if is_local else media_input)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "api-key": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_completion_tokens": max_out,
            "max_tokens": max_out,
        }
        if model.startswith("mimo"):
            payload["thinking"] = {"type": "enabled"}

        def post_once(body: dict):
            with httpx.Client(timeout=timeout, proxy=proxy) as client:
                resp = client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=body,
                )
                if resp.status_code != 200:
                    try:
                        error_body = resp.json()
                        error_msg = error_body.get("error", {}).get(
                            "message", resp.text[:300]
                        )
                    except Exception:
                        error_msg = resp.text[:300]
                    raise RuntimeError(f"API error {resp.status_code}: {error_msg}")
                return resp.json()

        try:
            data = post_once(payload)
        except RuntimeError as e:
            err = str(e)
            can_retry = (
                is_local
                and is_video_input
                and ("400" in err or "Param" in err or "Invalid" in err
                     or "corrupted" in err.lower())
            )
            if not can_retry:
                raise
            print(
                f"[genius-omni] API failed ({err[:120]}); "
                "retrying with H.264 video proxy…",
                file=sys.stderr,
            )
            proxy_path, enc = _make_video_proxy_h264_only(media_input)
            print(f"[genius-omni] fallback encoder={enc}", file=sys.stderr)
            content = build_content(proxy_path)
            payload["messages"] = [{"role": "user", "content": content}]
            data = post_once(payload)

        message = data["choices"][0]["message"]
        result_text = message.get("content") or ""
        if not result_text and message.get("reasoning_content"):
            result_text = message["reasoning_content"]
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
        description=(
            "Genius AV (视听) — multimodal analysis. "
            "Built-in providers: cpa (default), google, mimo. "
            "Custom: set {NAME}_BASE_URL / _API_KEY / _MODEL."
        )
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="Image/video/audio path or URL",
    )
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
        "--provider", "-p",
        default=None,
        help="Provider id: cpa|google|mimo or custom name (default: cpa)",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Model override",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="API base URL override",
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
    parser.add_argument(
        "--force-proxy",
        action="store_true",
        help="Force video analysis proxy (HEVC GPU first) even if under size trigger",
    )
    parser.add_argument(
        "--proxy-only",
        action="store_true",
        help="Only build analysis proxy and print path (no API call)",
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List configured providers and exit",
    )
    args = parser.parse_args()

    try:
        if args.list_providers:
            rows = list_providers()
            if args.output == "json":
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                active = resolve_provider(None)
                print(f"active={active}\n")
                for r in rows:
                    mark = "*" if r["id"] == active else " "
                    key = "key=yes" if r["has_key"] else "key=no"
                    print(
                        f"{mark} {r['id']:10} style={r['api_style']:7} "
                        f"model={r['model']}\n"
                        f"    base={r['base_url']}\n"
                        f"    {key}  {r['note']}"
                    )
            return

        if not args.file:
            parser.error("file is required (unless --list-providers)")

        if args.proxy_only:
            kind = media_kind(args.file)
            if kind == "video":
                proxy, enc = make_video_proxy(args.file)
            elif kind == "audio":
                proxy, enc = make_audio_proxy(args.file)
            else:
                proxy, enc = make_image_proxy(args.file)
            if args.output == "json":
                print(json.dumps({
                    "file": args.file,
                    "kind": kind,
                    "proxy": proxy,
                    "encoder": enc,
                    "bytes": Path(proxy).stat().st_size,
                }, ensure_ascii=False, indent=2))
            else:
                print(
                    f"kind={kind}\nproxy={proxy}\nencoder={enc}\n"
                    f"bytes={Path(proxy).stat().st_size}"
                )
            return

        result = analyze_media(
            args.file,
            mode=args.mode,
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url,
            provider=args.provider,
            compare_with=args.compare_with,
            force_proxy=args.force_proxy,
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
