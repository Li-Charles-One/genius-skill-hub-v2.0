#!/usr/bin/env python3
"""
Genius Omni (视听) — Image / video / audio / PDF analysis.

Built-in providers:
  cpa     (default) — Gemini native generateContent via CPA

Custom providers: set {NAME}_BASE_URL / {NAME}_API_KEY / {NAME}_MODEL
  and optional {NAME}_API_STYLE=gemini|openai

Usage:
    python3 vision.py --list-providers
    python3 vision.py --check
    python3 vision.py <file_or_url> <mode> [--provider cpa|custom]
    python3 vision.py https://www.youtube.com/watch?v=... video-summary
    python3 vision.py report.pdf ocr
    python3 vision.py long.mp4 video-summary   # auto segment when long

Image modes (6):  describe, ocr, ui-review, chart-data, object-detect, compare
Video modes (4):  video-summary, video-ocr, video-review, video-frame-analysis
Audio modes (4):  audio-summary, audio-transcribe, audio-review, audio-scene
PDF:              ocr / describe / chart-data / ui-review

Failures print `Error [CODE]: ...` to stderr and exit with EXIT_CODES[CODE].
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

# Local base64: hard cap on raw bytes (×1.33 once encoded).
MAX_RAW_BYTES = int(os.environ.get("VISION_MAX_RAW_MB", "35")) * 1024 * 1024
# Images / whole-PDF: re-encode or page-split above this size.
PROXY_TRIGGER_BYTES = int(os.environ.get("VISION_PROXY_TRIGGER_MB", "20")) * 1024 * 1024
# Audio/video planning: each request carries at most BUDGET bytes of media.
# Measured on CPA: 29.8MB inline video accepted.
BUDGET_BYTES = int(float(os.environ.get("VISION_BUDGET_MB", "30")) * 1024 * 1024)
PROXY_SCALE = int(os.environ.get("VISION_PROXY_SCALE", "1280"))
# Gemini samples video at ~1 fps, so 2 fps loses nothing and leaves bitrate for legible text.
PROXY_FPS = float(os.environ.get("VISION_PROXY_FPS", "2"))
PROXY_AUDIO_KBPS = int(os.environ.get("VISION_PROXY_AUDIO_KBPS", "64"))
# Below this video bitrate (1280 wide @ 2 fps) subtitles start to blur → split instead.
VIDEO_MIN_KBPS = int(os.environ.get("VISION_VIDEO_MIN_KBPS", "200"))
VIDEO_MAX_KBPS = int(os.environ.get("VISION_VIDEO_MAX_KBPS", "1500"))
# Hard cap per request regardless of size (context window / output length).
MAX_SINGLE_SEC = float(os.environ.get("VISION_MAX_SINGLE_SEC", "1800"))
# Large still images: max long-edge px for analysis proxy.
PROXY_IMAGE_MAX_EDGE = int(os.environ.get("VISION_PROXY_IMAGE_MAX_EDGE", "2048"))
PROXY_DIR = Path(tempfile.gettempdir()) / "genius-omni-proxy"
PDF_MAX_PAGES = int(os.environ.get("VISION_PDF_MAX_PAGES", "30"))
PDF_DPI = int(os.environ.get("VISION_PDF_DPI", "180"))
INDEX_DIR = Path(tempfile.gettempdir()) / "genius-omni-index"
# Auto-purge proxy/index files older than N days (default 30). 0 = disable.
CACHE_MAX_AGE_DAYS = float(os.environ.get("VISION_CACHE_MAX_AGE_DAYS", "30"))
_CACHE_CLEANED = False

# Failure codes from SKILL.md; the process exits with the mapped status.
EXIT_CODES = {
    "INPUT_NOT_FOUND": 3,
    "UNSUPPORTED_FORMAT": 4,
    "DEPENDENCY_MISSING": 5,
    "PROVIDER_ERROR": 6,
    "TIMEOUT": 7,
}


class OmniError(RuntimeError):
    """Failure carrying a SKILL.md contract code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

TIMESTAMP_RULES = (
    "TIMESTAMP RULES (mandatory):\n"
    "- Use mm:ss or hh:mm:ss aligned to the verified duration above when given.\n"
    "- Prefer absolute media time, not 'around the middle'.\n"
    "- If unsure of exact second, give a tight range (e.g. 02:14–02:20).\n"
    "- Keep events strictly chronological.\n"
)

SPEAKER_RULES = (
    "SPEAKER RULES (mandatory when speech exists):\n"
    "- Label speakers consistently (Speaker A/B/C or real names if stated).\n"
    "- Mark speaker changes on new lines.\n"
    "- If only one speaker, say so once and continue.\n"
)


# ── Prompts ──────────────────────────────────────────────────────────────

PROMPTS = {
    # ── Image prompts ──────────────────────────────────────────────
    "describe": (
        "Provide a detailed description of this image. Include: main subject, "
        "setting/background, colors/style, any text visible, notable objects, "
        "and overall composition. Read small text and UI labels carefully; "
        "do not invent text that is not visible."
    ),
    "ocr": (
        "Extract ALL text visible in this image/document page VERBATIM.\n"
        "Rules:\n"
        "- Preserve reading order, headers, lists, columns, tables, footnotes.\n"
        "- Keep line breaks that reflect structure; use markdown tables when helpful.\n"
        "- Include numbers, units, IDs, watermarks, stamps, and low-contrast text.\n"
        "- Do NOT translate; do NOT summarize; do NOT invent missing characters.\n"
        "- If a region is unreadable, write [illegible] for that span.\n"
        "- If no text is found, output exactly `NO_TEXT_FOUND` and nothing else."
    ),
    "ui-review": (
        "You are a senior UI/UX design reviewer. Analyze this interface mockup or design. "
        "Return a structured review:\n"
        "(1) Strengths — what works well\n"
        "(2) Issues — usability or design problems with severity (high/medium/low)\n"
        "(3) Specific actionable suggestions for improvement\n"
        "Be constructive and detailed. Quote visible labels accurately."
    ),
    "chart-data": (
        "Extract all data from this chart or graph. List: chart type, title, "
        "axis labels, all data points/series with values, and a brief summary "
        "of the trend or key insight. Prefer exact numbers shown on the chart."
    ),
    "object-detect": (
        "List all distinct objects, people, animals, and activities in this image. "
        "For each, describe what it is, its approximate location "
        "(top-left / top-center / top-right / mid-left / center / mid-right / "
        "bottom-left / bottom-center / bottom-right), relative size, and notable attributes."
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
        "Provide a comprehensive summary of this video.\n"
        f"{TIMESTAMP_RULES}"
        "Structure your response as:\n"
        "(1) Overall topic / what the video is about\n"
        "(2) Timeline — bullet list `mm:ss – mm:ss | what happens` covering the whole video\n"
        "(3) Key people, objects, or scenes shown\n"
        "(4) On-screen text / captions (quote important ones with timestamps)\n"
        "(5) Speech / audio content with speaker labels when possible\n"
        "(6) Overall tone, style, and production quality\n"
        "Be detailed and chronological. Do not invent events outside the video."
    ),
    "video-ocr": (
        "Extract ALL text visible anywhere in this video, organized chronologically.\n"
        f"{TIMESTAMP_RULES}"
        "For each item use: `mm:ss | text` (or `mm:ss–mm:ss | text` if it stays on screen).\n"
        "Include: slides, captions, subtitles, signs, UI labels, logos, watermarks, "
        "and overlaid graphics text. Quote verbatim; do not invent text.\n"
        "If no text is found, output exactly `NO_TEXT_FOUND` and nothing else."
    ),
    "video-review": (
        "You are a senior video production reviewer. Analyze this video or screen recording.\n"
        f"{TIMESTAMP_RULES}"
        "Return a structured review:\n"
        "(1) Content & clarity — is the message clear and well-paced? cite timestamps\n"
        "(2) Visual quality — composition, lighting, color, stability\n"
        "(3) Audio quality — clarity, levels, background noise\n"
        "(4) Editing & flow — transitions, pacing, engagement\n"
        "(5) Specific actionable suggestions for improvement\n"
        "Be constructive and detailed."
    ),
    "video-frame-analysis": (
        "You are a professional storyboard analyst. Analyze this video shot-by-shot "
        "and output a structured storyboard in the EXACT format below.\n\n"
        f"{TIMESTAMP_RULES}"
        "CRITICAL RULES:\n"
        "- Output EVERY shot. Do NOT skip or merge shots. Each camera cut = a new shot.\n"
        "- Number shots sequentially starting from 1.\n"
        "- Duration must be in seconds (e.g. 3.5s). Sum of all shot durations must "
        "approximately equal the total video duration given above.\n"
        "- Prefer absolute start–end times when known (mm:ss–mm:ss).\n\n"
        "FOR EACH SHOT, output exactly these fields:\n\n"
        "---\n"
        "## Shot N\n"
        "- **镜号**: N\n"
        "- **时间**: mm:ss–mm:ss\n"
        "- **时长**: X.Xs\n"
        "- **景别**: 远景/全景/中景/近景/特写/大特写 (pick one)\n"
        "- **画面内容**: Describe exactly what is visible — subject, "
        "action, composition, lighting, color palette. Be specific and visual.\n"
        "- **摄影机运动**: Static / Pan left-right / Tilt up-down / Zoom in-out / "
        "Dolly / Handheld / Crane / Drone / etc. Describe direction and speed.\n"
        "- **场景**: Where does this shot take place?\n"
        "- **对白/旁白**: Transcribe spoken words verbatim with speaker labels. If none, '无'.\n"
        "- **屏显文字**: Any text/graphics/subtitles. If none, '无'.\n\n"
        "After all shots, append:\n"
        "- **总镜数**: N\n"
        "- **总时长**: X.Xs\n"
        "- **整体风格**: 1-2 sentence style description"
    ),
    # ── Audio prompts ──────────────────────────────────────────────
    "audio-summary": (
        "Provide a comprehensive understanding of this audio.\n"
        f"{TIMESTAMP_RULES}{SPEAKER_RULES}"
        "Structure as:\n"
        "(1) Overall content / topic\n"
        "(2) Timeline — `mm:ss – mm:ss | segment summary`\n"
        "(3) Speakers — count, consistent labels, roles if clear\n"
        "(4) Speech content summary (not full verbatim unless short)\n"
        "(5) Non-speech sounds — music, SFX, ambient, silence\n"
        "(6) Tone, emotion, and production quality\n"
        "Be detailed and chronological."
    ),
    "audio-transcribe": (
        "You are a strict speech-to-text transcriber: a missing transcript is acceptable, "
        "an invented one is not.\n"
        "STEP 1 — Voice check. Listen to the whole audio and decide whether an actual "
        "human voice (spoken words or sung lyrics) is audible. Pure tones, beeps, dial/ring "
        "tones, instrumental music, noise, and silence are NOT speech.\n"
        "If no human voice is audible, your ENTIRE answer must be two lines:\n"
        "`NO_SPEECH_DETECTED`\n"
        "<one line describing the sounds>\n"
        "Do not add Speaker lines, guessed words, or example sentences.\n"
        "STEP 2 — Only if a voice is audible: transcribe ALL speech VERBATIM.\n"
        f"{TIMESTAMP_RULES}{SPEAKER_RULES}"
        "Output format preference:\n"
        "`[mm:ss] Speaker A: ...`\n"
        "Rules:\n"
        "- Keep original language; do not translate unless asked\n"
        "- Note [music], [noise], [inaudible], [silence] where relevant\n"
        "- Do not invent words; use [inaudible] when unclear\n"
        "If no speech is present, say so and briefly describe non-speech audio."
    ),
    "audio-review": (
        "You are a senior audio production reviewer. Analyze this recording.\n"
        f"{TIMESTAMP_RULES}"
        "Return a structured review:\n"
        "(1) Content clarity — message, structure, pacing (cite timestamps)\n"
        "(2) Speech quality — intelligibility, diction, levels, speakers\n"
        "(3) Technical quality — noise, clipping, reverb, balance, stereo\n"
        "(4) Music/SFX mix — if present, how well it supports content\n"
        "(5) Specific actionable suggestions for improvement\n"
        "Be constructive and detailed."
    ),
    "audio-scene": (
        "Analyze this audio as an acoustic scene.\n"
        f"{TIMESTAMP_RULES}"
        "List:\n"
        "(1) Environment / setting inferred from soundscape\n"
        "(2) Distinct sound events chronologically as `mm:ss | event`\n"
        "(3) Music: genre, mood, instruments if identifiable\n"
        "(4) Human activity: speech, footsteps, machinery, etc.\n"
        "(5) Overall atmosphere and what story the soundscape tells\n"
        "Be specific and sensory."
    ),
}

# ── File type detection ───────────────────────────────────────────────

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma", ".opus", ".aiff", ".aif"}
PDF_EXTENSIONS = {".pdf"}

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
    """Return 'video' | 'audio' | 'image' | 'pdf' from extension (works for URLs too)."""
    if is_youtube_url(path_or_url):
        return "video"
    suffix = _path_suffix(path_or_url)
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in PDF_EXTENSIONS:
        return "pdf"
    return "image"


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
        raise OmniError(
            "UNSUPPORTED_FORMAT",
            f"Mode '{mode}' is not for audio. Use: {', '.join(sorted(AUDIO_MODES))}",
        )
    if kind == "video":
        if mode in VIDEO_MODES:
            return mode
        if mode == "describe":
            return "video-summary"
        if mode == "ocr":
            return "video-ocr"
        if mode in AUDIO_MODES:
            raise OmniError("UNSUPPORTED_FORMAT", f"Mode '{mode}' is for audio files, got video")
        # image-style modes on video are allowed (model may handle)
        return mode
    if kind == "pdf":
        if mode in ("ocr", "describe", "chart-data", "ui-review"):
            return mode
        if mode in VIDEO_MODES or mode in AUDIO_MODES:
            raise OmniError("UNSUPPORTED_FORMAT", f"Mode '{mode}' is not for PDF. Use: ocr, describe")
        return "ocr" if mode not in IMAGE_MODES else mode
    # image
    if mode.startswith("video-") and mode != "video-summary":
        raise OmniError("UNSUPPORTED_FORMAT", f"Mode '{mode}' requires a video file")
    if mode in AUDIO_MODES:
        raise OmniError("UNSUPPORTED_FORMAT", f"Mode '{mode}' requires an audio file")
    return mode


# ── Duration formatting ──────────────────────────────────────────────────

def format_duration(seconds: float) -> str:
    """Format seconds to mm:ss or hh:mm:ss."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def check_system() -> dict:
    """Self-test: ffmpeg/ffprobe/pdftoppm/key presence (no secrets printed)."""
    ff = shutil.which(_ffmpeg_bin()) or shutil.which("ffmpeg")
    fp = shutil.which("ffprobe")
    providers = [
        {"id": r["id"], "has_key": r["has_key"], "model": r["model"], "style": r["api_style"]}
        for r in list_providers()
    ]
    return {
        "ffmpeg": ff or "MISSING",
        "ffprobe": fp or "MISSING",
        "pdftoppm": shutil.which("pdftoppm") or "MISSING (only needed for page-mode PDF)",
        "active_provider": _active_provider(),
        "providers": providers,
        "video_encoder": _first_listed_encoder(),
        "budget_mb": round(BUDGET_BYTES / 1024 / 1024, 1),
        "proxy_fps": PROXY_FPS,
        "video_min_kbps": VIDEO_MIN_KBPS,
        "pdf_max_pages": PDF_MAX_PAGES,
        "pdf_dpi": PDF_DPI,
        "ok": bool(ff and fp),
    }


def _file_fingerprint(path: str) -> str:
    p = Path(path)
    st = p.stat()
    h = hashlib.sha1()
    h.update(str(p.resolve()).encode("utf-8", errors="replace"))
    h.update(str(st.st_size).encode())
    h.update(str(int(st.st_mtime)).encode())
    return h.hexdigest()[:16]


def _run(cmd: list, timeout: float) -> subprocess.CompletedProcess:
    """Run an external tool; a missing binary is DEPENDENCY_MISSING."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise OmniError("DEPENDENCY_MISSING", f"{cmd[0]} not found on PATH") from e


def _proc_err(proc: subprocess.CompletedProcess) -> str:
    return (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()


def render_pdf_pages(pdf_path: str, max_pages: int | None = None, dpi: int | None = None) -> list[str]:
    """Render PDF pages to JPEG via pdftoppm (poppler). Returns list of image paths."""
    max_pages = max_pages or PDF_MAX_PAGES
    dpi = dpi or PDF_DPI
    src = Path(pdf_path)
    if not src.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    out_dir = _proxy_dir() / f"pdf-{_file_fingerprint(pdf_path)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(out_dir.glob("page-*.jpg"))
    if existing:
        pages = [str(p) for p in existing[:max_pages]]
        print(f"[genius-omni] pdf cache hit: {len(pages)} page(s) from {out_dir}", file=sys.stderr)
        return pages
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise OmniError(
            "DEPENDENCY_MISSING",
            "PDF page rendering needs pdftoppm (poppler): brew install poppler / apt install poppler-utils",
        )
    proc = _run(
        [pdftoppm, "-jpeg", "-r", str(dpi), "-f", "1", "-l", str(max_pages), str(src), str(out_dir / "page")],
        300,
    )
    pages = sorted(out_dir.glob("page-*.jpg"))
    if proc.returncode != 0 or not pages:
        raise RuntimeError(f"PDF render failed (pdftoppm): {_proc_err(proc)[:300]}")
    pages = pages[:max_pages]
    print(f"[genius-omni] pdf rendered {len(pages)} page(s) dpi~{dpi} → {out_dir}", file=sys.stderr)
    return [str(p) for p in pages]


def _index_path(video_path: str, mode: str) -> Path:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    maybe_cleanup_cache()
    return INDEX_DIR / f"{_file_fingerprint(video_path)}-{mode}.json"


# ── Cache and image proxies ──

def _ffmpeg_bin() -> str:
    return os.environ.get("FFMPEG_BIN", "ffmpeg")


def _proxy_dir() -> Path:
    PROXY_DIR.mkdir(parents=True, exist_ok=True)
    maybe_cleanup_cache()
    return PROXY_DIR


def maybe_cleanup_cache(force: bool = False) -> dict:
    """Delete genius-omni proxy/index files older than CACHE_MAX_AGE_DAYS.

    Runs at most once per process unless force=True.
    Returns stats: {removed, bytes, skipped, disabled}.
    """
    global _CACHE_CLEANED
    if not force and _CACHE_CLEANED:
        return {"removed": 0, "bytes": 0, "skipped": True, "disabled": False}
    _CACHE_CLEANED = True
    max_days = CACHE_MAX_AGE_DAYS
    if max_days <= 0:
        return {"removed": 0, "bytes": 0, "skipped": False, "disabled": True}
    cutoff = time.time() - max_days * 86400
    removed = 0
    freed = 0
    for root in (PROXY_DIR, INDEX_DIR):
        if not root.exists():
            continue
        # files first, then empty dirs under root (not root itself)
        for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            try:
                if path.is_file():
                    stat = path.stat()
                    if stat.st_mtime < cutoff:
                        path.unlink(missing_ok=True)
                        removed += 1
                        freed += stat.st_size
                elif path.is_dir() and not any(path.iterdir()):
                    path.rmdir()
            except OSError:
                continue
    if removed:
        print(
            f"[genius-omni] cache cleanup: removed {removed} file(s) "
            f">={max_days:g}d old, freed {freed / 1024 / 1024:.1f}MB",
            file=sys.stderr,
        )
    return {"removed": removed, "bytes": freed, "skipped": False, "disabled": False}


# ── Media planning: probe once, compute the plan, encode once ──────────
#
# Audio/video never go through trial-and-error encoding. One ffprobe call gives
# duration/codec/size; the request budget then fixes the bitrate and whether the
# media is split into segments. Proxies are cached per source + spec.

PASSTHROUGH_VIDEO = {".mp4", ".mov", ".m4v"}
PASSTHROUGH_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}

# Bitrate-targeted recipes, hardware first. The first one that works is remembered.
H264_ENCODERS = [
    ("h264_videotoolbox", ["-c:v", "h264_videotoolbox"]),
    ("h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p1"]),
    ("h264_qsv", ["-c:v", "h264_qsv"]),
    ("h264_amf", ["-c:v", "h264_amf"]),
    ("libx264", ["-c:v", "libx264", "-preset", "veryfast"]),
]
HEVC_ENCODERS = [
    ("hevc_videotoolbox", ["-c:v", "hevc_videotoolbox", "-tag:v", "hvc1"]),
    ("hevc_nvenc", ["-c:v", "hevc_nvenc", "-preset", "p1"]),
    ("hevc_qsv", ["-c:v", "hevc_qsv"]),
    ("hevc_amf", ["-c:v", "hevc_amf"]),
]
_BROKEN_ENCODERS: set = set()


def probe_media(path: str) -> dict:
    """One ffprobe call: duration, size, first real video stream, audio presence."""
    info = {
        "duration": None, "size": Path(path).stat().st_size,
        "vcodec": None, "width": 0, "height": 0, "has_audio": False,
    }
    proc = _run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=codec_type,codec_name,width,height",
        "-of", "json", path,
    ], 30)
    if proc.returncode != 0:
        return info
    data = json.loads(proc.stdout or "{}")
    try:
        info["duration"] = float((data.get("format") or {}).get("duration"))
    except (TypeError, ValueError):
        pass
    for s in data.get("streams") or []:
        if s.get("codec_type") == "audio":
            info["has_audio"] = True
        elif (
            s.get("codec_type") == "video"
            and info["vcodec"] is None
            and s.get("codec_name") not in ("mjpeg", "png", "bmp")  # cover art
        ):
            info.update(vcodec=s.get("codec_name"), width=s.get("width") or 0, height=s.get("height") or 0)
    return info


def plan_media(path: str, kind: str, api_style: str, force_proxy: bool = False) -> dict:
    """Decide passthrough / one proxy / N segments from probe numbers alone."""
    info = probe_media(path)
    dur = info["duration"] or 0.0
    audio_kbps = PROXY_AUDIO_KBPS if (kind == "audio" or info["has_audio"]) else 0
    budget_kbit = BUDGET_BYTES * 8 / 1000 * 0.92  # container overhead headroom
    if kind == "video":
        ok_codecs = {"h264"} if api_style == "gemini" else {"h264", "hevc"}
        native = info["vcodec"] in ok_codecs and _path_suffix(path) in PASSTHROUGH_VIDEO
        floor_kbps = VIDEO_MIN_KBPS + audio_kbps
    else:
        native = _path_suffix(path) in PASSTHROUGH_AUDIO
        floor_kbps = audio_kbps
    if dur <= 0:
        if info["size"] <= BUDGET_BYTES:
            return {**info, "action": "passthrough", "segments": 1, "segment_sec": 0.0,
                    "video_kbps": VIDEO_MAX_KBPS, "audio_kbps": audio_kbps}
        raise OmniError("UNSUPPORTED_FORMAT", f"ffprobe cannot read the duration of {path}")

    split = os.environ.get("VISION_LONG_VIDEO", "1").strip().lower() not in ("0", "false", "no", "off")
    max_seg = min(MAX_SINGLE_SEC, budget_kbit / floor_kbps)
    n = max(1, math.ceil(dur / max_seg)) if split else 1
    seg = dur / n
    video_kbps = int(max(50, min(VIDEO_MAX_KBPS, budget_kbit / seg - audio_kbps))) if kind == "video" else 0
    if n == 1 and native and not force_proxy and info["size"] <= BUDGET_BYTES:
        action = "passthrough"
    else:
        action = "proxy" if n == 1 else "segments"
    return {**info, "action": action, "segments": n, "segment_sec": seg,
            "video_kbps": video_kbps, "audio_kbps": audio_kbps}


def describe_plan(plan: dict, kind: str) -> str:
    size = plan["size"] / 1024 / 1024
    src = f"{kind} {format_duration(plan['duration'] or 0)} {size:.1f}MB"
    if kind == "video" and plan["vcodec"]:
        src += f" {plan['vcodec']} {plan['width']}x{plan['height']}"
    if plan["action"] == "passthrough":
        return f"{src} → upload as-is"
    target = f"{plan['video_kbps']}k video @{PROXY_FPS:g}fps + " if kind == "video" else ""
    target += f"{plan['audio_kbps']}k audio"
    if plan["action"] == "proxy":
        return f"{src} → one proxy ({target})"
    return f"{src} → {plan['segments']} segments × {format_duration(plan['segment_sec'])} ({target})"


def _first_listed_encoder() -> str:
    """First H.264 encoder this ffmpeg build lists (hardware before libx264)."""
    try:
        listed = _run([_ffmpeg_bin(), "-hide_banner", "-encoders"], 15).stdout
    except OmniError:
        return "MISSING"
    for name, _ in _encoder_chain(True):
        if f" {name} " in listed:
            return name
    return "none"


def _encoder_chain(h264_only: bool) -> list:
    chain = H264_ENCODERS if h264_only else HEVC_ENCODERS + H264_ENCODERS
    if sys.platform != "darwin":
        chain = [e for e in chain if "videotoolbox" not in e[0]]
    return [e for e in chain if e[0] not in _BROKEN_ENCODERS]


def _cached_proxy(src: str, tag: str, suffix: str) -> tuple[Path, bool]:
    out = _proxy_dir() / f"{_file_fingerprint(src)}-{tag}{suffix}"
    return out, out.is_file() and out.stat().st_size > 0


def make_video_proxy(
    src: str,
    start: float = 0.0,
    duration: float | None = None,
    video_kbps: int = VIDEO_MAX_KBPS,
    audio_kbps: int = PROXY_AUDIO_KBPS,
    h264_only: bool = True,
) -> tuple[str, str]:
    """Encode one analysis proxy at a computed bitrate. Returns (path, encoder)."""
    if not Path(src).is_file():
        raise FileNotFoundError(f"File not found: {src}")
    tag = (
        f"v{start:.0f}+{duration or 0:.0f}-{video_kbps}k-a{audio_kbps}k-"
        f"{PROXY_FPS:g}fps-{PROXY_SCALE}-{'h264' if h264_only else 'any'}"
    )
    out, hit = _cached_proxy(src, tag, ".mp4")
    if hit:
        print(f"[genius-omni] proxy cache hit → {out}", file=sys.stderr)
        return str(out), "cache"
    s = PROXY_SCALE
    vf = (
        f"fps={PROXY_FPS:g},"
        f"scale='if(gte(iw,ih),min({s},iw),-2)':'if(gte(iw,ih),-2,min({s},ih))'"
    )
    rate = ["-b:v", f"{video_kbps}k", "-maxrate", f"{int(video_kbps * 1.25)}k",
            "-bufsize", f"{video_kbps * 2}k"]
    audio = ["-c:a", "aac", "-b:a", f"{audio_kbps}k", "-ac", "1"] if audio_kbps else ["-an"]
    head = [_ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error"]
    if start:
        head += ["-ss", f"{start:.3f}"]
    head += ["-i", src]
    if duration:
        head += ["-t", f"{duration:.3f}"]
    tmp = out.with_suffix(".part.mp4")
    last_err = ""
    for name, vcodec in _encoder_chain(h264_only):
        t0 = time.perf_counter()
        try:
            proc = _run([*head, "-vf", vf, *vcodec, *rate, *audio,
                         "-movflags", "+faststart", str(tmp)], 900)
        except subprocess.TimeoutExpired as e:
            tmp.unlink(missing_ok=True)
            raise OmniError("TIMEOUT", f"{name} encode exceeded 900s") from e
        if proc.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
            last_err = _proc_err(proc)
            tmp.unlink(missing_ok=True)
            _BROKEN_ENCODERS.add(name)
            continue
        size = tmp.stat().st_size
        if size > MAX_RAW_BYTES and video_kbps > 60:
            # Encoder overshot its target: one deterministic retry, scaled down.
            tmp.unlink(missing_ok=True)
            return make_video_proxy(src, start, duration, int(video_kbps * 0.7 * MAX_RAW_BYTES / size),
                                    audio_kbps, h264_only)
        tmp.replace(out)
        print(
            f"[genius-omni] video proxy via {name}: {size / 1024 / 1024:.1f}MB "
            f"in {time.perf_counter() - t0:.1f}s → {out}",
            file=sys.stderr,
        )
        return str(out), name
    raise RuntimeError(f"No working video encoder. Last error: {last_err[:400]}")


def make_audio_proxy(src: str, start: float = 0.0, duration: float | None = None) -> tuple[str, str]:
    """Encode mono AAC at PROXY_AUDIO_KBPS. Returns (path, codec)."""
    if not Path(src).is_file():
        raise FileNotFoundError(f"File not found: {src}")
    out, hit = _cached_proxy(src, f"a{start:.0f}+{duration or 0:.0f}-{PROXY_AUDIO_KBPS}k", ".m4a")
    if hit:
        print(f"[genius-omni] proxy cache hit → {out}", file=sys.stderr)
        return str(out), "cache"
    cmd = [_ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error"]
    if start:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", src]
    if duration:
        cmd += ["-t", f"{duration:.3f}"]
    tmp = out.with_suffix(".part.m4a")
    t0 = time.perf_counter()
    proc = _run([*cmd, "-vn", "-c:a", "aac", "-b:a", f"{PROXY_AUDIO_KBPS}k", "-ac", "1", str(tmp)], 900)
    if proc.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Audio proxy failed: {_proc_err(proc)[:400]}")
    tmp.replace(out)
    print(
        f"[genius-omni] audio proxy aac/{PROXY_AUDIO_KBPS}k mono: "
        f"{out.stat().st_size / 1024 / 1024:.1f}MB in {time.perf_counter() - t0:.1f}s → {out}",
        file=sys.stderr,
    )
    return str(out), "aac"


def build_proxy(src: str, kind: str, plan: dict, h264_only: bool, start: float = 0.0,
                duration: float | None = None) -> str:
    if kind == "video":
        return make_video_proxy(src, start, duration, plan["video_kbps"], plan["audio_kbps"], h264_only)[0]
    return make_audio_proxy(src, start, duration)[0]


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
    t0 = time.perf_counter()
    proc = _run([
        _ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src_path),
        "-vf", vf,
        "-frames:v", "1",
        "-q:v", "3",
        str(out),
    ], 120)
    if proc.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
        out.unlink(missing_ok=True)
        raise RuntimeError(f"Image proxy failed: {_proc_err(proc)[:400]}")
    print(
        f"[genius-omni] image proxy max_edge={max_edge}: "
        f"{out.stat().st_size / 1024 / 1024:.1f}MB in {time.perf_counter() - t0:.1f}s → {out}",
        file=sys.stderr,
    )
    if out.stat().st_size > MAX_RAW_BYTES and max_edge > 1280:
        return make_image_proxy(src, max_edge=1280)
    return str(out), f"jpeg-{max_edge}"


# ── Providers ─────────────────────────────────────────────────────────────
#
# Built-in packs + any custom provider via env:
#   VISION_PROVIDER=myrelay
#   MYRELAY_BASE_URL=https://...
#   MYRELAY_API_KEY=...
#   MYRELAY_MODEL=...
#   MYRELAY_API_STYLE=gemini|openai   # optional; auto if omitted
#
# api_style:
#   gemini  → /v1beta/models/{model}:generateContent (inline_data / file_data)
#   openai  → /chat/completions (image_url / video_url / input_audio)

BUILTIN_PROVIDERS = {
    "cpa": {
        "base_url": "https://cpa-jp.charles-ai.space/v1",
        "model": "gemini-3.8-flash-high",
        "api_style": "gemini",
        "key_envs": ("CPA_API_KEY", "VISION_CPA_API_KEY", "VISION_API_KEY"),
        "note": "CPA Gemini relay (native generateContent)",
    },
}
DEFAULT_PROVIDER = "cpa"


@lru_cache(maxsize=None)
def _dotenv() -> dict:
    """Parse the first existing .env (skill scripts/, then ~/.hermes) once per process."""
    for env_path in (Path(__file__).parent / ".env", Path.home() / ".hermes" / ".env"):
        if not env_path.exists():
            continue
        out = {}
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            out[name.strip()] = value.strip().strip('"').strip("'")
        return out
    return {}


def _env(name: str) -> str:
    return (os.environ.get(name) or _dotenv().get(name) or "").strip()


def _active_provider() -> str:
    return (_env("VISION_PROVIDER") or DEFAULT_PROVIDER).lower()


def _infer_api_style(model: str, base_url: str) -> str:
    """Heuristic for custom providers without {NAME}_API_STYLE."""
    m, b = model.lower(), base_url.lower()
    if "generativelanguage.googleapis.com" in b or "googleapis.com/v1beta" in b:
        return "gemini"
    if m.startswith("gemini") and ("googleapis" in b or "charles-ai" in b):
        return "gemini"
    return "openai"


def provider_conf(
    pid: str | None = None,
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Resolve the config that requests will actually use.

    Precedence: CLI → {PROVIDER}_* → VISION_* (active provider only) → pack defaults.
    """
    active = _active_provider()
    pid = (pid or active).strip().lower()
    p = pid.upper()
    builtin = BUILTIN_PROVIDERS.get(pid, {})

    def pick(cli_val: str | None, suffix: str) -> str:
        return (
            cli_val
            or _env(f"{p}_{suffix}")
            or (_env(f"VISION_{suffix}") if pid == active else "")
            or builtin.get(suffix.lower(), "")
        )

    resolved_base = pick(base_url, "BASE_URL")
    resolved_model = pick(model, "MODEL")
    if not resolved_base or not resolved_model:
        raise OmniError(
            "PROVIDER_ERROR",
            f"Unknown provider '{pid}'. Built-ins: {', '.join(sorted(BUILTIN_PROVIDERS))}. "
            f"For a custom provider set {p}_BASE_URL, {p}_API_KEY, {p}_MODEL "
            f"(optional {p}_API_STYLE=gemini|openai).",
        )
    style = (
        _env(f"{p}_API_STYLE")
        or _env("VISION_API_STYLE")
        or builtin.get("api_style")
        or _infer_api_style(resolved_model, resolved_base)
    ).lower()
    if style not in ("gemini", "openai"):
        raise OmniError(
            "PROVIDER_ERROR",
            f"Invalid API style '{style}' for provider '{pid}'. Use gemini or openai.",
        )
    key_envs = list(builtin.get("key_envs") or ())
    for extra in (f"{p}_API_KEY", "VISION_API_KEY"):
        if extra not in key_envs:
            key_envs.append(extra)
    key = api_key or next((v for v in map(_env, key_envs) if v), "")
    return {
        "id": pid,
        "base_url": resolved_base.rstrip("/"),
        "model": resolved_model,
        "api_style": style,
        "api_key": key,
        "key_envs": tuple(key_envs),
        "note": builtin.get("note") or f"custom provider '{pid}'",
        "builtin": bool(builtin),
    }


def list_providers() -> list[dict]:
    """Built-in packs plus the active custom provider, as requests would resolve them."""
    ids = list(BUILTIN_PROVIDERS)
    if _active_provider() not in ids:
        ids.append(_active_provider())
    rows = []
    for pid in ids:
        conf = provider_conf(pid)
        rows.append({
            "id": pid,
            "builtin": conf["builtin"],
            "model": conf["model"],
            "base_url": conf["base_url"],
            "api_style": conf["api_style"],
            "note": conf["note"],
            "has_key": bool(conf["api_key"]),
        })
    return rows


# ── Request building ─────────────────────────────────────────────────────

MIME_TYPES = {
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
    ".aiff": "audio/aiff", ".aif": "audio/aiff",
    ".pdf": "application/pdf",
}
# URLs without a known extension fall back to the media kind.
URL_KIND_MIME = {"image": "image/jpeg", "video": "video/mp4", "audio": "audio/mpeg", "pdf": "application/pdf"}


def encode_file(file_path: str) -> tuple[str, str]:
    """Encode a local media file to base64. Returns (base64_data, media_type)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    file_size = path.stat().st_size
    if file_size > MAX_RAW_BYTES:
        raise ValueError(
            f"File too large: {file_size / 1024 / 1024:.1f}MB "
            f"(max ~{MAX_RAW_BYTES / 1024 / 1024:.0f}MB raw for base64). "
            "Audio/video are planned to fit the request budget; images over "
            f"{PROXY_TRIGGER_BYTES / 1024 / 1024:.0f}MB are downscaled. "
            "Or pass a public URL (video ≤300MB, audio ≤100MB)."
        )
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return data, MIME_TYPES.get(path.suffix.lower(), "image/png")


def _gemini_api_root(base_url: str) -> str:
    """Map OpenAI-style .../v1 base to host root for /v1beta/... routes."""
    u = base_url.rstrip("/")
    for suffix in ("/v1", "/v1beta/openai", "/openai"):
        if u.endswith(suffix):
            return u[: -len(suffix)]
    return u


def _gemini_part(path_or_url: str, kind: str) -> dict:
    if is_youtube_url(path_or_url):
        return {"file_data": {"file_uri": path_or_url, "mime_type": "video/*"}}
    if path_or_url.startswith(("http://", "https://")):
        # Public direct media URL via file_data (best-effort on CPA)
        mime = MIME_TYPES.get(_path_suffix(path_or_url)) or URL_KIND_MIME.get(kind, "application/octet-stream")
        return {"file_data": {"file_uri": path_or_url, "mime_type": mime}}
    b64, mime = encode_file(path_or_url)
    return {"inline_data": {"mime_type": mime, "data": b64}}


def _openai_part(path_or_url: str, kind: str) -> dict:
    url = path_or_url
    if not path_or_url.startswith(("http://", "https://")):
        b64, mime = encode_file(path_or_url)
        if kind == "audio":
            fmt = {"audio/mpeg": "mp3"}.get(mime, mime.split("/")[1])
            return {"type": "input_audio", "input_audio": {"data": b64, "format": fmt}}
        url = f"data:{mime};base64,{b64}"
    if kind == "audio":
        return {"type": "input_audio", "input_audio": {"data": url}}
    if kind == "video":
        return {"type": "video_url", "video_url": {"url": url}}
    return {"type": "image_url", "image_url": {"url": url}}


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
    if data.get("choices"):
        # OpenAI-shaped reply from some gateways
        return _extract_openai_text(data, show_think)
    err = data.get("error") or {}
    if err:
        raise OmniError("PROVIDER_ERROR", f"API error: {err.get('message') if isinstance(err, dict) else err}")
    raise OmniError("PROVIDER_ERROR", f"Empty model response: {json.dumps(data, ensure_ascii=False)[:300]}")


def _extract_openai_text(data: dict, show_think: bool = False) -> str:
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        raise OmniError("PROVIDER_ERROR", f"Unexpected response: {json.dumps(data, ensure_ascii=False)[:300]}")
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""
    if show_think and content and reasoning:
        return f"<thinking>\n{reasoning}\n</thinking>\n\n{content}"
    return content or reasoning


def _http_proxy() -> str | None:
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        if os.environ.get(name):
            return os.environ[name]
    return None


RETRY_HTTP = {429, 500, 502, 503, 504}
RETRY_DELAYS = (5, 15, 30)


def _post_json(url: str, headers: dict, body: dict, timeout: float) -> dict:
    """POST with retries on gateway errors (e.g. CPA 502 under concurrent load)."""
    data = json.dumps(body).encode("utf-8")
    for attempt, delay in enumerate((*RETRY_DELAYS, None), 1):
        try:
            return _post_json_once(url, headers, data, timeout)
        except OmniError as e:
            # Timeouts are not retried: a slow multi-minute request would only repeat.
            transient = getattr(e, "http_status", None) in RETRY_HTTP or str(e).startswith("Network error")
            if delay is None or not transient:
                raise
            print(
                f"[genius-omni] {e} — retry {attempt}/{len(RETRY_DELAYS)} in {delay}s…",
                file=sys.stderr,
            )
            time.sleep(delay)


def _post_json_once(url: str, headers: dict, data: bytes, timeout: float) -> dict:
    """POST JSON with the standard library; errors become PROVIDER_ERROR / TIMEOUT."""
    proxy = _http_proxy()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {})
    )
    request = urllib.request.Request(
        url,
        data=data,
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener.open(request, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(text).get("error")
            msg = (err.get("message") if isinstance(err, dict) else err) or text
        except Exception:
            msg = text
        msg = str(msg)
        if len(msg) > 300:
            msg = msg[:300] + f"… [truncated, {len(msg)} chars total]"
        error = OmniError("PROVIDER_ERROR", f"API error {e.code}: {msg}")
        error.http_status = e.code
        raise error from e
    except (socket.timeout, TimeoutError) as e:
        raise OmniError("TIMEOUT", f"No response within {timeout:g}s") from e
    except urllib.error.URLError as e:
        if isinstance(e.reason, (socket.timeout, TimeoutError)):
            raise OmniError("TIMEOUT", f"No response within {timeout:g}s") from e
        raise OmniError("PROVIDER_ERROR", f"Network error: {e.reason}") from e


# Short canned refusals (e.g. "blocked by content policy").
REFUSAL_RE = re.compile(r"content (?:policy|filter)", re.I)


def call_model(conf: dict, media: list, prompt: str, timeout: float, show_think: bool = False) -> str:
    """Send one request; a canned refusal is a PROVIDER_ERROR, never a result."""
    text = _call_model_once(conf, media, prompt, timeout, show_think)
    if len(text) < 300 and REFUSAL_RE.search(text):
        raise OmniError("PROVIDER_ERROR", f"Model refused ({conf['id']}): {text.strip()}")
    return text


def _call_model_once(conf: dict, media: list, prompt: str, timeout: float, show_think: bool = False) -> str:
    """Send one request. media = [(path_or_url, kind), ...] placed before the prompt."""
    max_out = int(os.environ.get("VISION_MAX_TOKENS", "32768"))
    key, model = conf["api_key"], conf["model"]
    if conf["api_style"] == "gemini":
        parts = [_gemini_part(src, kind) for src, kind in media] + [{"text": prompt}]
        data = _post_json(
            f"{_gemini_api_root(conf['base_url'])}/v1beta/models/{model}:generateContent",
            {"Authorization": f"Bearer {key}", "x-goog-api-key": key},
            {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"maxOutputTokens": max_out}},
            timeout,
        )
        return _extract_gemini_text(data, show_think)
    content = [_openai_part(src, kind) for src, kind in media] + [{"type": "text", "text": prompt}]
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_completion_tokens": max_out,
        "max_tokens": max_out,
    }
    data = _post_json(
        f"{conf['base_url']}/chat/completions",
        {"Authorization": f"Bearer {key}", "api-key": key},
        payload,
        timeout,
    )
    return _extract_openai_text(data, show_think)


# ── Analysis ─────────────────────────────────────────────────────────────

def _analyze_pdf(pdf_path: str, mode: str, conf: dict, force_proxy: bool = False) -> str:
    """Gemini-style providers read the whole PDF in one request; others go page by page."""
    mode = resolve_mode(mode, "pdf")
    whole = (
        conf["api_style"] == "gemini"
        and os.environ.get("VISION_PDF_PAGES", "").strip().lower() not in ("1", "true", "yes", "on")
        and Path(pdf_path).stat().st_size <= PROXY_TRIGGER_BYTES
    )
    if whole:
        print(f"[genius-omni] pdf → one native request ({conf['model']})…", file=sys.stderr)
        prompt = (
            f"{PROMPTS[mode]}\n\nThis is a multi-page PDF document. Cover every page in order "
            "and start each page with a `## Page N` heading."
        )
        text = call_model(conf, [(pdf_path, "pdf")], prompt, timeout=300)
        return f"# PDF analysis ({mode})\n\nSource: `{pdf_path}`\n\n{text}"

    pages = render_pdf_pages(pdf_path)
    chunks = []
    total = len(pages)
    for i, page_path in enumerate(pages, 1):
        print(f"[genius-omni] pdf page {i}/{total}…", file=sys.stderr)
        text = analyze_media(
            page_path,
            mode=mode,
            force_proxy=force_proxy,
            _conf=conf,
            _skip_long_video=True,
            _page_label=f"PDF page {i}/{total}",
        )
        chunks.append(f"## Page {i}/{total}\n\n{text}")
    header = f"# PDF analysis ({mode}) — {total} page(s)\n\nSource: `{pdf_path}`\n"
    return header + "\n\n---\n\n".join(chunks)


# Modes whose per-segment output is the deliverable: join instead of re-summarizing.
CONCAT_MODES = {"audio-transcribe", "video-frame-analysis"}


def _analyze_segments(src: str, kind: str, mode: str, plan: dict, conf: dict, h264_only: bool) -> str:
    """Planned long media: encode each segment once → analyze → index → join/synthesize.

    The index is written after every segment, so a failed run resumes where it stopped.
    """
    n, seg_len, duration = plan["segments"], plan["segment_sec"], plan["duration"]
    idx_file = _index_path(src, mode)
    segments = []
    if idx_file.is_file():
        try:
            cached = json.loads(idx_file.read_text(encoding="utf-8"))
            if (
                cached.get("duration") == round(duration, 1)
                and cached.get("mode") == mode
                and cached.get("count") == n
                and cached.get("provider") == conf["id"]
                and cached.get("model") == conf["model"]
            ):
                segments = cached.get("segments") or []
                print(f"[genius-omni] segment index hit: {len(segments)}/{n} done", file=sys.stderr)
        except Exception:
            segments = []

    label = "VIDEO" if kind == "video" else "AUDIO"
    for i in range(len(segments) + 1, n + 1):
        start = (i - 1) * seg_len
        end = min(duration, start + seg_len)
        print(
            f"[genius-omni] segment {i}/{n} {format_duration(start)}–{format_duration(end)}…",
            file=sys.stderr,
        )
        seg_path = build_proxy(src, kind, plan, h264_only, start, end - start)
        try:
            note = analyze_media(
                seg_path,
                mode=mode,
                _conf=conf,
                _skip_long_video=True,
                _segment_label=(
                    f"SEGMENT {i}/{n} absolute time "
                    f"{format_duration(start)}–{format_duration(end)} "
                    f"(offset +{format_duration(start)} from media start). "
                    f"Report timestamps as ABSOLUTE media time, not segment-local."
                ),
            )
        finally:
            Path(seg_path).unlink(missing_ok=True)
        segments.append({
            "index": i,
            "start": round(start, 2),
            "end": round(end, 2),
            "start_label": format_duration(start),
            "end_label": format_duration(end),
            "note": note,
        })
        idx_file.write_text(
            json.dumps({
                "file": str(Path(src).resolve()),
                "mode": mode,
                "provider": conf["id"],
                "model": conf["model"],
                "duration": round(duration, 1),
                "count": n,
                "segment_sec": seg_len,
                "segments": segments,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    index_blob = "\n\n".join(
        f"### Segment {s['index']}: {s['start_label']} – {s['end_label']}\n{s['note']}"
        for s in segments
    )
    if mode in CONCAT_MODES:
        result = index_blob
    else:
        # Synthesize from segment notes (text-only, no media re-upload)
        synth_prompt = (
            f"[{label} GROUND TRUTH — total duration {format_duration(duration)} "
            f"({duration:.1f}s). Segment notes below cover the full timeline.]\n\n"
            f"{PROMPTS.get(mode, PROMPTS['video-summary'])}\n\n"
            f"You are given chronological segment notes already extracted from the {kind}. "
            f"Synthesize ONE coherent answer for the whole {kind}. "
            "Merge duplicates, keep absolute timestamps, do not invent content "
            "not supported by the notes.\n\n"
            f"--- SEGMENT NOTES ---\n{index_blob}"
        )
        result = call_model(conf, [], synth_prompt, timeout=300)
    result += (
        f"\n\n---\n⏱ **时长校验** — ffprobe 实测: **{format_duration(duration)}** "
        f"| segments: {n} × ~{format_duration(seg_len)} "
        f"| index: `{idx_file}`"
    )
    return result


# audio-transcribe asks this first: a dedicated yes/no request stops the model from
# inventing speech for tones, music or noise, which a strict transcribe prompt alone did not.
VOICE_CHECK_PROMPT = (
    "Is an actual human voice (spoken words or sung lyrics) audible anywhere in this audio? "
    "Pure tones, beeps, dial/ring tones, instrumental music, noise and silence are not a voice. "
    "Answer with exactly one word: YES or NO."
)
NO_SPEECH_RESULT = (
    "NO_SPEECH_DETECTED\n"
    "Voice check found no audible human voice. Use audio-summary or audio-scene to describe the sounds."
)


def analyze_media(
    media_input: str,
    mode: str = "describe",
    model: str = None,
    api_key: str = None,
    base_url: str = None,
    provider: str = None,
    compare_with: str = None,
    force_proxy: bool = False,
    _conf: dict | None = None,
    _skip_long_video: bool = False,
    _page_label: str | None = None,
    _segment_label: str | None = None,
) -> str:
    """Analyze image / video / audio / PDF.

    Gemini style (CPA): native /v1beta/models/{model}:generateContent
      - local → inline_data base64; YouTube / URL → file_data.file_uri
    OpenAI style (custom providers): /chat/completions
    """
    conf = _conf or provider_conf(provider, model=model, base_url=base_url, api_key=api_key)
    if not conf["api_key"]:
        raise OmniError(
            "PROVIDER_ERROR",
            f"API key not found for provider '{conf['id']}'. "
            f"Set {' / '.join(conf['key_envs'])} or create scripts/.env.",
        )
    for path in (media_input, compare_with):
        if path and not path.startswith(("http://", "https://")) and not Path(path).is_file():
            raise OmniError("INPUT_NOT_FOUND", f"File not found: {path}")

    is_local = not media_input.startswith(("http://", "https://"))
    kind = media_kind(media_input)
    # URL without clear extension: infer from mode (skip YouTube — always video)
    if not is_local and _path_suffix(media_input) == "" and not is_youtube_url(media_input):
        if mode in AUDIO_MODES:
            kind = "audio"
        elif mode in VIDEO_MODES or mode.startswith("video-"):
            kind = "video"

    # PDF: whole-document or page-by-page path (before generic image pipeline)
    if kind == "pdf" and is_local:
        return _analyze_pdf(media_input, mode, conf, force_proxy)

    mode = resolve_mode(mode, kind)
    prompt = PROMPTS.get(mode, PROMPTS["describe"])
    if _page_label:
        prompt = f"[{_page_label} — treat this as one document page.]\n\n" + prompt
    if _segment_label:
        prompt = f"[{_segment_label}]\n\n" + prompt

    is_video_input = kind == "video"
    is_audio_input = kind == "audio"
    timeout = 60
    upload_path = media_input
    actual_duration = None
    plan = None
    h264_only = conf["api_style"] == "gemini"  # Gemini decodes H.264 most reliably

    if is_local and (is_video_input or is_audio_input):
        plan = plan_media(media_input, kind, conf["api_style"], force_proxy=force_proxy)
        actual_duration = plan["duration"]
        if not _skip_long_video:
            print(f"[genius-omni] plan: {describe_plan(plan, kind)}", file=sys.stderr)
        if plan["action"] == "segments" and not _skip_long_video:
            return _analyze_segments(media_input, kind, mode, plan, conf, h264_only)
        if plan["action"] != "passthrough":
            upload_path = build_proxy(media_input, kind, plan, h264_only)
        timeout = max(300, min(900, (actual_duration or 0) * 0.6))
    elif is_video_input or is_audio_input:
        timeout = 300
    elif is_local and Path(media_input).stat().st_size > PROXY_TRIGGER_BYTES:
        upload_path = make_image_proxy(media_input)[0]

    if actual_duration is not None:
        label = "AUDIO" if is_audio_input else "VIDEO"
        prompt = (
            f"[{label} GROUND TRUTH — actual duration: {format_duration(actual_duration)} "
            f"({actual_duration:.1f}s), verified by ffprobe. "
            f"Use this as your timing reference for all timestamps.]\n\n"
            + prompt
        )

    show_think = os.environ.get("VISION_SHOW_THINKING", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
    media = [(upload_path, kind)]
    if mode == "compare" and compare_with:
        media.append((compare_with, "image"))
    no_voice = (
        mode == "audio-transcribe"
        and os.environ.get("VISION_VOICE_CHECK", "1").strip().lower() not in ("0", "false", "no", "off")
        and call_model(conf, media, VOICE_CHECK_PROMPT, timeout).strip().upper().startswith("NO")
    )
    if no_voice:
        print("[genius-omni] voice check: no human voice, skipping transcription", file=sys.stderr)
        result_text = NO_SPEECH_RESULT
    else:
        try:
            result_text = call_model(conf, media, prompt, timeout, show_think)
        except OmniError as e:
            err = str(e)
            retryable = (
                e.code == "PROVIDER_ERROR"
                and is_local
                and is_video_input
                and upload_path == media_input
                and (any(s in err for s in ("400", "Param", "Invalid"))
                     or "corrupted" in err.lower() or "decode" in err.lower())
            )
            if not retryable:
                raise
            print(
                f"[genius-omni] API failed ({err[:120]}); retrying with H.264 video proxy…",
                file=sys.stderr,
            )
            proxy_path, enc = make_video_proxy(
                media_input, video_kbps=plan["video_kbps"], audio_kbps=plan["audio_kbps"], h264_only=True,
            )
            print(f"[genius-omni] fallback encoder={enc}", file=sys.stderr)
            media[0] = (proxy_path, kind)
            result_text = call_model(conf, media, prompt, timeout, show_think)


    # Segments get one footer on the joined result, not one each.
    if actual_duration is not None and not _segment_label:
        footer_parts = [f"ffprobe 实测: **{format_duration(actual_duration)}**"]
        dur_patterns = [
            r'(?:total\s+)?duration[:\s]*(\d+)[:：](\d+)(?:[:：](\d+))?',
            r'总时长[：:\s]*(\d+)[:：](\d+)(?:[:：](\d+))?',
            r'(?:视频|音频)\s*时长[：:\s]*(\d+)[:：](\d+)(?:[:：](\d+))?',
            r'(?:视频\s*)?时长[：:\s]*(\d+)[:：](\d+)(?:[:：](\d+))?',
        ]
        for pat in dur_patterns:
            m = re.search(pat, result_text, re.IGNORECASE)
            if m:
                claimed = f"{m.group(1)}:{m.group(2)}" + (f":{m.group(3)}" if m.group(3) else "")
                footer_parts.append(f"模型声称: `{claimed}`")
                break
        footer_parts.append("（以此为基准校验模型时间戳准确性）")
        result_text += "\n\n---\n⏱ **时长校验** — " + " | ".join(footer_parts)

    return result_text


# ── CLI ───────────────────────────────────────────────────────────────────

def _error_code(error: Exception) -> str | None:
    if isinstance(error, OmniError):
        return error.code
    if isinstance(error, FileNotFoundError):
        return "INPUT_NOT_FOUND"
    if isinstance(error, subprocess.TimeoutExpired):
        return "TIMEOUT"
    return None


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Genius Omni (视听) — multimodal analysis. "
            "Built-in provider: cpa (default). "
            "Custom: set {NAME}_BASE_URL / _API_KEY / _MODEL."
        )
    )
    parser.add_argument("file", nargs="?", default=None, help="Image/video/audio/PDF path or URL")
    parser.add_argument(
        "mode", nargs="?", default="describe", choices=list(PROMPTS.keys()), help="Analysis mode",
    )
    parser.add_argument(
        "--output", "-o", choices=["text", "json"], default="text", help="Output format (default: text)",
    )
    parser.add_argument(
        "--provider", "-p", default=None, help="Provider id: cpa or custom name (default: cpa)",
    )
    parser.add_argument("--model", "-m", default=None, help="Model override")
    parser.add_argument("--base-url", default=None, help="API base URL override")
    parser.add_argument("--api-key", "-k", default=None, help="API key override")
    parser.add_argument("--compare-with", "-c", default=None, help="Second image for 'compare' mode")
    parser.add_argument(
        "--force-proxy",
        action="store_true",
        help="Always build an analysis proxy, even when the file could be uploaded as-is",
    )
    parser.add_argument(
        "--proxy-only", action="store_true", help="Only build analysis proxy and print path (no API call)",
    )
    parser.add_argument("--list-providers", action="store_true", help="List configured providers and exit")
    parser.add_argument(
        "--check", action="store_true", help="Self-test ffmpeg/ffprobe/providers (no media API call)",
    )
    parser.add_argument(
        "--cleanup-cache",
        action="store_true",
        help="Purge proxy/index files older than VISION_CACHE_MAX_AGE_DAYS (default 30) and exit",
    )
    parser.add_argument(
        "--no-long-video",
        action="store_true",
        help="Disable long-video segment indexing even if duration exceeds threshold",
    )
    args = parser.parse_args()

    try:
        if args.cleanup_cache:
            stats = maybe_cleanup_cache(force=True)
            if args.output == "json":
                print(json.dumps({
                    **stats,
                    "max_age_days": CACHE_MAX_AGE_DAYS,
                    "proxy_dir": str(PROXY_DIR),
                    "index_dir": str(INDEX_DIR),
                }, ensure_ascii=False, indent=2))
            elif stats.get("disabled"):
                print("cache cleanup disabled (VISION_CACHE_MAX_AGE_DAYS<=0)")
            else:
                print(
                    f"removed={stats['removed']} bytes={stats['bytes']} "
                    f"max_age_days={CACHE_MAX_AGE_DAYS:g}\n"
                    f"proxy_dir={PROXY_DIR}\nindex_dir={INDEX_DIR}"
                )
            return

        if args.list_providers:
            rows = list_providers()
            if args.output == "json":
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                active = _active_provider()
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

        if args.check:
            info = check_system()
            if args.output == "json":
                print(json.dumps(info, ensure_ascii=False, indent=2))
            else:
                print(f"ffmpeg:   {info['ffmpeg']}")
                print(f"ffprobe:  {info['ffprobe']}")
                print(f"pdftoppm: {info['pdftoppm']}")
                print(f"active:   {info['active_provider']}")
                print(
                    f"media: budget={info['budget_mb']}MB/request fps={info['proxy_fps']:g} "
                    f"min_video={info['video_min_kbps']}k encoder={info['video_encoder']}"
                )
                print(f"pdf: max_pages={info['pdf_max_pages']} dpi={info['pdf_dpi']}")
                for p in info["providers"]:
                    print(
                        f"  - {p['id']}: key={'yes' if p['has_key'] else 'no'} "
                        f"model={p['model']} style={p['style']}"
                    )
                print("ok" if info["ok"] else "MISSING system tools")
            if not info["ok"]:
                sys.exit(2)
            return

        if not args.file:
            parser.error("file is required (unless --list-providers / --check)")

        if args.no_long_video:
            os.environ["VISION_LONG_VIDEO"] = "0"

        if args.proxy_only:
            kind = media_kind(args.file)
            if kind == "pdf":
                pages = render_pdf_pages(args.file)
                if args.output == "json":
                    print(json.dumps({
                        "file": args.file,
                        "kind": "pdf",
                        "pages": pages,
                        "count": len(pages),
                    }, ensure_ascii=False, indent=2))
                else:
                    print(f"kind=pdf\npages={len(pages)}\n" + "\n".join(pages))
                return
            if kind == "image":
                proxy, enc = make_image_proxy(args.file)
                built = {"kind": kind, "proxies": [proxy], "encoder": enc}
            else:
                conf = provider_conf(args.provider)
                h264_only = conf["api_style"] == "gemini"
                plan = plan_media(args.file, kind, conf["api_style"], force_proxy=True)
                if plan["action"] == "segments":
                    proxies = [
                        build_proxy(args.file, kind, plan, h264_only, i * plan["segment_sec"],
                                    min(plan["duration"], (i + 1) * plan["segment_sec"]) - i * plan["segment_sec"])
                        for i in range(plan["segments"])
                    ]
                else:
                    proxies = [build_proxy(args.file, kind, plan, h264_only)]
                built = {"kind": kind, "plan": describe_plan(plan, kind), "proxies": proxies}
            sizes = [Path(p).stat().st_size for p in built["proxies"]]
            if args.output == "json":
                print(json.dumps({"file": args.file, **built, "bytes": sizes}, ensure_ascii=False, indent=2))
            else:
                print("\n".join(f"{k}={v}" for k, v in built.items() if k != "proxies"))
                for p, b in zip(built["proxies"], sizes):
                    print(f"proxy={p} bytes={b}")
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
        code = _error_code(e)
        print(f"Error [{code}]: {e}" if code else f"Error: {e}", file=sys.stderr)
        sys.exit(EXIT_CODES.get(code, 1))


if __name__ == "__main__":
    main()
