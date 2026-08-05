#!/usr/bin/env python3
"""Genius CPA Image — multi-provider CPA image generation.

Providers:
  cpa-jp  Gemini native generateContent
    POST {CPA_JP_BASE}/v1beta/models/{model}:generateContent
    default model: gemini-3.1-flash-image
    auth: CPA_JP_API_KEY (alias CPA_API_KEY)

  cpa-us  OpenAI-compatible images API (Codex / gpt-image-2)
    POST {CPA_US_BASE}/v1/images/generations
    POST {CPA_US_BASE}/v1/images/edits   (when --ref)
    default model: gpt-image-2
    auth: CPA_US_API_KEY (alias CPA_GPT_API_KEY)

Native controls:
  Gemini: imageConfig.aspectRatio + imageSize (0.5K/1K/2K/4K), --ref, --google-search
  gpt-image-2 (CPA-US observed): aspect→fixed 1K size presets, --quality, --output-format,
    --ref edits. Higher 2K/4K requests are not available on this channel.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
OUT_DIR = Path.cwd() / "genius_output"
LOG_DIR = OUT_DIR / "Logs"
JOBS_DIR = OUT_DIR / "Jobs"
LOG_FILE = LOG_DIR / "cpa_image_log.jsonl"
# Defaults; overridable via env / skill .env (see resolve_log_limits)
LOG_MAX_SIZE = 10 * 1024 * 1024
LOG_ARCHIVE_DAYS = 7
LOG_MAX_ARCHIVES = 20
JOB_LOG_MAX_SIZE = 5 * 1024 * 1024
JOB_KEEP_DAYS = 7
JOB_MAX_FILES = 100
DEFAULT_WAIT_TIMEOUT = 600
JOB_POLL_INTERVAL = 1.0


def load_dotenv(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file. Never raise on missing file."""
    if not path.exists() or not path.is_file():
        return {}
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def load_dotenv_map() -> dict[str, str]:
    """Load first existing local secrets file (never committed).

    Search order:
      1) skill root .env
      2) scripts/.env
      3) skill root Genius_cpa_image.env
    """
    candidates = [
        SKILL_DIR / ".env",
        HERE / ".env",
        SKILL_DIR / "Genius_cpa_image.env",
    ]
    for path in candidates:
        data = load_dotenv(path)
        if data:
            return data
    return {}


def env_or_file(name: str, file_keys: dict[str, str], default: str = "") -> str:
    """Prefer process env (override), then skill-local .env."""
    return (os.environ.get(name) or file_keys.get(name) or default).strip()


_FILE_KEYS = load_dotenv_map()

# ---------------------------------------------------------------------------
# Provider + model registry
# ---------------------------------------------------------------------------

PROVIDERS = {
    "cpa-jp": {
        "label": "JP CPA Gemini",
        "api_key_names": ("CPA_JP_API_KEY", "CPA_API_KEY"),
        "base_name": "CPA_JP_BASE",
        "base_default": "https://cpa-jp.charles-ai.space",
        "api": "generateContent",
    },
    "cpa-us": {
        "label": "US CPA OpenAI images",
        "api_key_names": ("CPA_US_API_KEY", "CPA_GPT_API_KEY"),
        "base_name": "CPA_US_BASE",
        "base_default": "https://cpa.charles-ai.space",
        "api": "images",
    },
}

ASPECTS_GEMINI = {
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4",
    "9:16", "16:9", "21:9", "1:4", "4:1", "1:8", "8:1",
}
RESOLUTIONS_GEMINI = {"0.5K", "1K", "2K", "4K"}

# gpt-image-2 via CPA-US: observed fixed 1K size matrix (UI + live actual_size).
# Verified 2026-08-05: requesting 16:9 4K / 3840x2160 still returns 1672x941.
# quality low|medium|high changes fidelity/latency, NOT pixel dimensions.
# Do not invent 2K/4K OpenAI sizes for this channel — CPA rewrites them to 1K.
ASPECTS_GPT_IMAGE = {
    "1:1", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5",
    "16:9", "9:16", "21:9", "9:21", "2:1", "1:2", "auto",
}
# Only 1K is real on CPA-US. 2K/4K are accepted as aliases and coerced to 1K.
RESOLUTIONS_GPT_IMAGE = {"1K", "2K", "4K", "auto"}
RESOLUTIONS_GPT_IMAGE_REAL = {"1K", "auto"}
GPT_IMAGE_RESOLUTION_ALIASES = {"2K": "1K", "4K": "1K"}

# CPA-US observed aspect → size (1K only)
GPT_IMAGE_SIZE_MAP = {
    ("1:1", "1K"): "1024x1024",
    ("16:9", "1K"): "1672x941",
    ("9:16", "1K"): "941x1672",
    ("4:3", "1K"): "1443x1090",
    ("3:4", "1K"): "1090x1443",
    ("3:2", "1K"): "1536x1024",
    ("2:3", "1K"): "1024x1536",
    ("5:4", "1K"): "1408x1120",
    ("4:5", "1K"): "1120x1408",
    ("21:9", "1K"): "1920x832",
    ("9:21", "1K"): "832x1920",
    ("2:1", "1K"): "1792x896",
    ("1:2", "1K"): "896x1792",
    # auto
    ("auto", "1K"): "auto",
    ("auto", "auto"): "auto",
    ("1:1", "auto"): "auto",
    ("3:2", "auto"): "auto",
    ("2:3", "auto"): "auto",
    ("4:3", "auto"): "auto",
    ("3:4", "auto"): "auto",
    ("5:4", "auto"): "auto",
    ("4:5", "auto"): "auto",
    ("16:9", "auto"): "auto",
    ("9:16", "auto"): "auto",
    ("21:9", "auto"): "auto",
    ("9:21", "auto"): "auto",
    ("2:1", "auto"): "auto",
    ("1:2", "auto"): "auto",
}
# Fill 2K/4K alias keys so old CLI still maps cleanly to the same 1K presets.
for _aspect, _size in list(GPT_IMAGE_SIZE_MAP.items()):
    a, r = _aspect
    if r == "1K" and _size != "auto":
        GPT_IMAGE_SIZE_MAP[(a, "2K")] = _size
        GPT_IMAGE_SIZE_MAP[(a, "4K")] = _size
GPT_IMAGE_SIZE_MAP[("auto", "2K")] = "auto"
GPT_IMAGE_SIZE_MAP[("auto", "4K")] = "auto"

GPT_IMAGE_QUALITIES = {"low", "medium", "high", "auto"}
GPT_IMAGE_OUTPUT_FORMATS = {"png", "jpeg", "jpg", "webp"}
# Exact CPA-US size dropdown (plus auto)
GPT_IMAGE_POPULAR_SIZES = {
    "1024x1024",  # 1:1 1K
    "1672x941",   # 16:9 1K
    "941x1672",   # 9:16 1K
    "1443x1090",  # 4:3 1K
    "1090x1443",  # 3:4 1K
    "1536x1024",  # 3:2 1K
    "1024x1536",  # 2:3 1K
    "1408x1120",  # 5:4 1K
    "1120x1408",  # 4:5 1K
    "1920x832",   # 21:9 1K
    "832x1920",   # 9:21 1K
    "1792x896",   # 2:1 1K
    "896x1792",   # 1:2 1K
    "auto",
}
GPT_IMAGE_SIZE_TO_ASPECT = {
    "1024x1024": "1:1",
    "1672x941": "16:9",
    "941x1672": "9:16",
    "1443x1090": "4:3",
    "1090x1443": "3:4",
    "1536x1024": "3:2",
    "1024x1536": "2:3",
    "1408x1120": "5:4",
    "1120x1408": "4:5",
    "1920x832": "21:9",
    "832x1920": "9:21",
    "1792x896": "2:1",
    "896x1792": "1:2",
    "auto": "auto",
}
# Legacy OpenAI-style sizes → nearest CPA 1K preset (same aspect when known).
GPT_IMAGE_LEGACY_SIZE_ALIASES = {
    "1344x768": "1672x941",
    "768x1344": "941x1672",
    "1024x768": "1443x1090",
    "768x1024": "1090x1443",
    "1280x1024": "1408x1120",
    "1024x1280": "1120x1408",
    "1536x656": "1920x832",
    "2048x2048": "1024x1024",
    "2880x2880": "1024x1024",
    "2048x1152": "1672x941",
    "1152x2048": "941x1672",
    "2560x1440": "1672x941",
    "3840x2160": "1672x941",
    "2160x3840": "941x1672",
    "2304x1536": "1536x1024",
    "1536x2304": "1024x1536",
    "2048x1536": "1443x1090",
    "1536x2048": "1090x1443",
    "2048x1632": "1408x1120",
    "1632x2048": "1120x1408",
    "2560x1104": "1920x832",
    "3520x2352": "1536x1024",
    "2352x3520": "1024x1536",
    "3312x2480": "1443x1090",
    "2480x3312": "1090x1443",
    "3200x2560": "1408x1120",
    "2560x3200": "1120x1408",
    "3840x1648": "1920x832",
}

MODELS = {
    "gemini-3.1-flash-image": {
        "id": "gemini-3.1-flash-image",
        "provider": "cpa-jp",
        "api": "generateContent",
        "max_ref": 14,
        "max_prompt": 20000,
        "default_aspect": "1:1",
        "default_resolution": "1K",
        "aspects": ASPECTS_GEMINI,
        "resolutions": RESOLUTIONS_GEMINI,
        "supports_google_search": True,
        "supports_quality": False,
        "supports_output_format": False,
        "default_quality": None,
        "default_output_format": None,
    },
    "gpt-image-2": {
        "id": "gpt-image-2",
        "provider": "cpa-us",
        "api": "images",
        "max_ref": 10,
        "max_prompt": 32000,
        "default_aspect": "1:1",
        "default_resolution": "1K",
        "aspects": ASPECTS_GPT_IMAGE,
        "resolutions": RESOLUTIONS_GPT_IMAGE,
        "resolutions_real": RESOLUTIONS_GPT_IMAGE_REAL,
        "supports_google_search": False,
        "supports_quality": True,
        "supports_output_format": True,
        "qualities": GPT_IMAGE_QUALITIES,
        "output_formats": GPT_IMAGE_OUTPUT_FORMATS,
        "default_quality": "auto",
        "default_output_format": "png",
        "size_map": GPT_IMAGE_SIZE_MAP,
        # CPA-US only exposes fixed 1K presets; not open flexible WxH.
        "flexible_size": False,
        "popular_sizes": GPT_IMAGE_POPULAR_SIZES,
    },
}

DEFAULT_MODEL = "gemini-3.1-flash-image"

TIMEOUT_SUBMIT = 180
TIMEOUT_MODELS = 20
MAX_RETRIES = 3
RETRY_DELAY = 5
DEFAULT_CONCURRENT = 3


def log_print(*args, **kwargs):
    kwargs.setdefault("flush", True)
    print(*args, **kwargs)


def configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(line_buffering=True)
        except Exception:
            pass


def provider_base(provider: str) -> str:
    meta = PROVIDERS[provider]
    return env_or_file(
        meta["base_name"], _FILE_KEYS, meta["base_default"]
    ).rstrip("/")


def provider_api_key(provider: str) -> str:
    meta = PROVIDERS[provider]
    for name in meta["api_key_names"]:
        val = env_or_file(name, _FILE_KEYS)
        if val:
            return val
    return ""


def require_api_key(provider: str) -> str:
    key = provider_api_key(provider)
    if key:
        return key
    names = " / ".join(PROVIDERS[provider]["api_key_names"])
    raise RuntimeError(
        f"{names} not set for provider={provider}. "
        "Export it, or put it in skill .env / scripts/.env "
        "(see .env.example). Never commit real keys."
    )


def headers_for(provider: str) -> dict:
    return {
        "Authorization": f"Bearer {require_api_key(provider)}",
        "Content-Type": "application/json",
    }


def model_provider(model: str) -> str:
    if model not in MODELS:
        raise RuntimeError(f"unknown model: {model}; available: {sorted(MODELS)}")
    return MODELS[model]["provider"]


def model_api(model: str) -> str:
    return MODELS[model]["api"]


def parse_error_payload(text: str):
    """Best-effort parse of CPA/Gemini/OpenAI JSON error body."""
    if not text:
        return None
    try:
        data = json.loads(text)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    err = data.get("error")
    if isinstance(err, dict):
        return err
    return data if any(
        k in data for k in ("code", "message", "reset_time", "reset_seconds")
    ) else None


def format_http_error(status: int, body: str) -> str:
    err = parse_error_payload(body)
    if not err:
        snippet = (body or "").strip().replace("\n", " ")
        if len(snippet) > 300:
            snippet = snippet[:300] + "..."
        return f"HTTP {status}: {snippet or '(empty body)'}"

    code = err.get("code")
    message = err.get("message") or err.get("msg") or str(err)
    model = err.get("model")
    provider = err.get("provider")
    reset_time = err.get("reset_time") or err.get("resetTime")
    reset_seconds = err.get("reset_seconds")
    if reset_seconds is None:
        reset_seconds = err.get("resetSeconds")

    parts = [f"HTTP {status}"]
    if code:
        parts.append(f"code={code}")
    if model:
        parts.append(f"model={model}")
    if provider:
        parts.append(f"provider={provider}")
    if reset_time:
        parts.append(f"reset_time={reset_time}")
    if reset_seconds is not None:
        parts.append(f"reset_seconds={reset_seconds}")
    parts.append(f"message={message}")
    return " ".join(parts)


def is_non_retryable_error(exc: BaseException) -> bool:
    """Cooldown / auth / bad-request should fail fast (no multi-retry loops)."""
    msg = str(exc).lower()
    if "model_cooldown" in msg or "cooling down" in msg:
        return True
    if "reset_time=" in msg or "reset_seconds=" in msg:
        return True
    if "http 429" in msg:
        return True
    if "http 400" in msg or "http 401" in msg or "http 403" in msg or "http 404" in msg:
        return True
    if "auth_unavailable" in msg or "no auth available" in msg:
        return True
    if "refresh_token_invalidated" in msg:
        return True
    return False


def request_with_retry(method, url, retries=MAX_RETRIES, **kwargs):
    """Retry transient network errors only.

    model_cooldown / HTTP 429 fail immediately — do not burn retries.
    """
    last_exc = None
    for i in range(retries):
        try:
            r = requests.request(method, url, **kwargs)
            if r.status_code == 429:
                raise RuntimeError(format_http_error(429, r.text or ""))
            return r
        except RuntimeError:
            raise
        except requests.RequestException as e:
            last_exc = e
            if i + 1 >= retries:
                break
            time.sleep(2 ** i)
    raise RuntimeError(f"request failed {retries} times: {last_exc}")


def emit_result(**fields):
    parts = []
    for k, v in fields.items():
        if v is None:
            continue
        s = str(v).replace("\n", " ").replace("\r", " ")
        if any(c.isspace() for c in s):
            s = '"' + s.replace('"', "'") + '"'
        parts.append(f"{k}={s}")
    log_print("GENIUS_RESULT " + " ".join(parts))


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    """Read int from process env or skill .env; fall back to default."""
    raw = env_or_file(name, _FILE_KEYS, "")
    if not raw:
        return default
    try:
        val = int(str(raw).strip())
    except ValueError:
        return default
    return max(minimum, val)


def resolve_log_limits() -> dict:
    """Resolve log/job retention limits (env overrides constants)."""
    if env_or_file("CPA_IMAGE_LOG_MAX_MB", _FILE_KEYS):
        log_max_size = _env_int("CPA_IMAGE_LOG_MAX_MB", 10, 1) * 1024 * 1024
    else:
        log_max_size = _env_int("CPA_IMAGE_LOG_MAX_BYTES", LOG_MAX_SIZE, 1024)

    if env_or_file("CPA_IMAGE_JOB_LOG_MAX_MB", _FILE_KEYS):
        job_log_max_size = _env_int("CPA_IMAGE_JOB_LOG_MAX_MB", 5, 1) * 1024 * 1024
    else:
        job_log_max_size = _env_int(
            "CPA_IMAGE_JOB_LOG_MAX_BYTES", JOB_LOG_MAX_SIZE, 1024
        )

    return {
        "log_max_size": log_max_size,
        "log_keep_days": _env_int("CPA_IMAGE_LOG_KEEP_DAYS", LOG_ARCHIVE_DAYS, 1),
        "log_max_archives": _env_int("CPA_IMAGE_LOG_MAX_ARCHIVES", LOG_MAX_ARCHIVES, 1),
        "job_log_max_size": job_log_max_size,
        "job_keep_days": _env_int("CPA_IMAGE_JOB_KEEP_DAYS", JOB_KEEP_DAYS, 1),
        "job_max_files": _env_int("CPA_IMAGE_JOB_MAX_FILES", JOB_MAX_FILES, 1),
    }


def rotate_file_by_size(
    path: Path,
    max_size: int,
    archive_name: str | None = None,
    label: str = "log",
) -> Path | None:
    """If path exceeds max_size, rename to archive and return archive path."""
    try:
        if not path.exists() or not path.is_file():
            return None
        if path.stat().st_size <= max_size:
            return None
    except OSError:
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if archive_name:
        archive = path.with_name(archive_name)
    else:
        # file.log -> file_YYYYMMDD_HHMMSS.log
        archive = path.with_name(f"{path.stem}_{stamp}{path.suffix}")
    # avoid clobber
    if archive.exists():
        archive = path.with_name(f"{path.stem}_{stamp}_{uuid.uuid4().hex[:6]}{path.suffix}")
    try:
        path.rename(archive)
        log_print(f"  [{label}] rotated: {path.name} -> {archive.name}")
        return archive
    except OSError as e:
        log_print(f"  [{label}] rotate failed for {path.name}: {e}")
        return None


def prune_by_mtime(paths, keep_days: int, label: str = "log") -> int:
    """Delete files older than keep_days. Returns removed count."""
    cutoff = time.time() - keep_days * 86400
    removed = 0
    for f in paths:
        try:
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
                log_print(f"  [{label}] removed old: {f.name}")
        except OSError:
            continue
    return removed


def prune_by_count(paths, max_files: int, label: str = "log") -> int:
    """Keep newest max_files; delete older. paths is iterable of Path."""
    files = []
    for f in paths:
        try:
            if f.is_file():
                files.append((f.stat().st_mtime, f))
        except OSError:
            continue
    files.sort(key=lambda x: x[0], reverse=True)
    removed = 0
    for _, f in files[max_files:]:
        try:
            f.unlink()
            removed += 1
            log_print(f"  [{label}] pruned excess: {f.name}")
        except OSError:
            continue
    return removed


def write_log(entry):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    limits = resolve_log_limits()
    rotate_file_by_size(
        LOG_FILE,
        limits["log_max_size"],
        archive_name=f"cpa_image_log_{datetime.now():%Y%m%d_%H%M%S}.jsonl",
        label="log",
    )
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def rotate_job_log_if_needed(job_id: str | None = None, path: Path | None = None):
    """Rotate a single job worker log when it exceeds size limit."""
    limits = resolve_log_limits()
    target = path or (job_log_path(job_id) if job_id else None)
    if not target:
        return None
    return rotate_file_by_size(
        target,
        limits["job_log_max_size"],
        label="job-log",
    )


def clean_old_logs():
    """Rotate/prune main jsonl archives and async job artifacts."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    limits = resolve_log_limits()

    # Main active log: size rotate if needed (no write, just cap growth)
    rotate_file_by_size(
        LOG_FILE,
        limits["log_max_size"],
        archive_name=f"cpa_image_log_{datetime.now():%Y%m%d_%H%M%S}.jsonl",
        label="log",
    )

    # Main archives: by age then by count
    archives = list(LOG_DIR.glob("cpa_image_log_*.jsonl"))
    prune_by_mtime(archives, limits["log_keep_days"], label="log")
    archives = list(LOG_DIR.glob("cpa_image_log_*.jsonl"))
    prune_by_count(archives, limits["log_max_archives"], label="log")

    # Optional legacy log name (not written by this skill, but may exist)
    legacy = LOG_DIR / "genius_log.jsonl"
    if legacy.exists():
        rotate_file_by_size(
            legacy,
            limits["log_max_size"],
            archive_name=f"genius_log_{datetime.now():%Y%m%d_%H%M%S}.jsonl",
            label="log",
        )
        legacy_archives = list(LOG_DIR.glob("genius_log_*.jsonl"))
        prune_by_mtime(legacy_archives, limits["log_keep_days"], label="log")

    # Job logs: rotate oversized *active* worker logs only.
    # Active: <job_id>.log  (job_id like cpa-YYYYMMDD_HHMMSS-xxxxxxxx)
    # Rotated archives: <job_id>_YYYYMMDD_HHMMSS.log — age/count pruned below.
    active_job_log_re = re.compile(
        r"^(?:cpa|test)-(\d{8})_(\d{6})-([0-9a-f]{6,})\.log$"
    )
    for logf in JOBS_DIR.glob("*.log"):
        if active_job_log_re.match(logf.name):
            rotate_file_by_size(logf, limits["job_log_max_size"], label="job-log")

    # Job artifacts age prune: .json + .log (+ rotated job logs)
    job_files = (
        list(JOBS_DIR.glob("*.json"))
        + list(JOBS_DIR.glob("*.log"))
        + list(JOBS_DIR.glob("*.json.tmp"))
    )
    prune_by_mtime(job_files, limits["job_keep_days"], label="job")

    # Cap total job json status files (newest kept); delete paired logs when possible
    status_files = []
    for p in JOBS_DIR.glob("*.json"):
        try:
            if p.is_file():
                status_files.append((p.stat().st_mtime, p))
        except OSError:
            continue
    status_files.sort(key=lambda x: x[0], reverse=True)
    for _, old in status_files[limits["job_max_files"]:]:
        try:
            job_id = old.stem
            if old.exists():
                old.unlink()
            for paired in JOBS_DIR.glob(f"{job_id}*"):
                try:
                    if paired.is_file() and paired != old:
                        paired.unlink()
                except OSError:
                    pass
            log_print(f"  [job] pruned excess status: {old.name}")
        except OSError:
            continue

    # Cap orphan/rotated job logs by count (newest kept)
    job_logs = list(JOBS_DIR.glob("*.log"))
    prune_by_count(job_logs, limits["job_max_files"] * 2, label="job-log")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def job_log_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.log"


def new_job_id(prefix: str = "cpa") -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:8]}"


def write_job(job: dict) -> Path:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    job = dict(job)
    job["updated_at"] = now_iso()
    path = job_path(job["job_id"])
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def read_job(job_id: str) -> dict:
    path = job_path(job_id)
    if not path.is_file():
        raise RuntimeError(f"job not found: {job_id} ({path})")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"invalid job file {path}: {e}")
    if not isinstance(data, dict):
        raise RuntimeError(f"invalid job file {path}: not an object")
    return data


def update_job(job_id: str, **fields) -> dict:
    job = read_job(job_id)
    job.update(fields)
    write_job(job)
    return job


def is_terminal_status(status: str) -> bool:
    return status in {"success", "failed", "partial", "batch_done"}


def print_job_summary(job: dict, verbose: bool = True):
    job_id = job.get("job_id")
    status = job.get("status")
    kind = job.get("kind") or "single"
    log_print(f"job_id : {job_id}")
    log_print(f"status : {status}")
    log_print(f"kind   : {kind}")
    if job.get("created_at"):
        log_print(f"created: {job['created_at']}")
    if job.get("updated_at"):
        log_print(f"updated: {job['updated_at']}")
    if job.get("pid"):
        log_print(f"pid    : {job['pid']}")
    if job.get("error"):
        log_print(f"error  : {job['error']}")
    result = job.get("result") or {}
    if isinstance(result, dict):
        if result.get("path"):
            log_print(f"path   : {result['path']}")
        if result.get("duration_s") is not None:
            log_print(f"duration: {result['duration_s']}s")
        if result.get("ok") is not None:
            log_print(f"ok/fail: {result.get('ok')}/{result.get('fail')}")
    if verbose and job.get("log_path"):
        log_print(f"log    : {job['log_path']}")


def spawn_job_worker(job_id: str) -> int:
    """Detach a worker process that continues after the CLI exits."""
    script = Path(__file__).resolve()
    log_file = job_log_path(job_id)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    # Rotate oversized previous worker log before appending.
    rotate_job_log_if_needed(path=log_file)
    cmd = [
        sys.executable,
        "-u",
        str(script),
        "--_run-job",
        job_id,
        "--out",
        str(OUT_DIR),
    ]
    env = os.environ.copy()
    with open(log_file, "a", encoding="utf-8") as logf:
        logf.write(f"\n===== worker spawn {now_iso()} =====\n")
        logf.write("cmd: " + " ".join(cmd) + "\n")
        logf.flush()
        proc = subprocess.Popen(
            cmd,
            stdout=logf,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            cwd=str(Path.cwd()),
            env=env,
            start_new_session=True,
            close_fds=True,
        )
    return proc.pid


def task_meta(task: dict) -> tuple[str, str, str]:
    model = task.get("model") or DEFAULT_MODEL
    provider = model_provider(model)
    api = model_api(model)
    return model, provider, api


def submit_async_job(kind: str, payload: dict) -> dict:
    # Validate credentials for the job's model(s) before detach.
    if kind == "single":
        task = payload.get("task") or {}
        require_api_key(model_provider(task.get("model") or DEFAULT_MODEL))
    elif kind == "batch":
        for t in payload.get("tasks") or []:
            require_api_key(model_provider(t.get("model") or DEFAULT_MODEL))
    else:
        require_api_key(model_provider(DEFAULT_MODEL))

    job_id = new_job_id("cpa")
    log_file = job_log_path(job_id)
    job = {
        "job_id": job_id,
        "kind": kind,
        "status": "queued",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "out_dir": str(OUT_DIR),
        "log_path": str(log_file),
        "payload": payload,
        "result": None,
        "error": None,
        "pid": None,
    }
    write_job(job)
    pid = spawn_job_worker(job_id)
    job = update_job(job_id, pid=pid, status="queued")
    log_print(f">> async submitted job_id={job_id} pid={pid}")
    log_print(f"   status file: {job_path(job_id)}")
    log_print(f"   worker log : {log_file}")
    emit_result(
        status="queued",
        job_id=job_id,
        kind=kind,
        pid=pid,
        path=job_path(job_id),
        mode="async-local",
    )
    return job


def run_job_worker(job_id: str):
    """Internal worker entry: execute a previously queued local job."""
    job = read_job(job_id)
    if job.get("status") in {"success", "failed", "partial", "batch_done"}:
        log_print(f">> job {job_id} already terminal: {job.get('status')}")
        return
    update_job(job_id, status="running", pid=os.getpid(), started_at=now_iso())
    kind = job.get("kind") or "single"
    payload = job.get("payload") or {}
    t0 = time.time()
    try:
        if kind == "single":
            task = payload.get("task") or {}
            name = payload.get("name")
            info = generate_one(task, name=name)
            result = {
                "task_id": info["task_id"],
                "path": str(info["path"]),
                "size": info["size"],
                "duration_s": round(info["duration_s"], 1),
                "model": info["model"],
                "provider": info["provider"],
                "api": info["api"],
                "prompt": info["prompt"],
                "aspect": info["aspect"],
                "resolution": info["resolution"],
                "size_param": info.get("size_param"),
                "actual_size": info.get("actual_size"),
                "quality": info.get("quality"),
                "output_format": info.get("output_format"),
                "n_images": info.get("n_images"),
            }
            update_job(
                job_id,
                status="success",
                finished_at=now_iso(),
                result=result,
                error=None,
                duration_s=round(time.time() - t0, 1),
            )
            log_print(f">> job success path={info['path']}")
            emit_result(
                status="success",
                job_id=job_id,
                model=info["model"],
                provider=info["provider"],
                api=info["api"],
                mode="async-local",
                task_id=info["task_id"],
                path=info["path"],
                aspect=info["aspect"],
                resolution=info["resolution"],
                size=info.get("size_param"),
                actual_size=info.get("actual_size"),
                quality=info.get("quality"),
                duration_s=round(info["duration_s"], 1),
                size_kb=round(info["size"] / 1024, 1),
            )
            write_log({
                "timestamp": now_iso(),
                "job_id": job_id,
                "task_id": info["task_id"],
                "model": info["model"],
                "provider": info["provider"],
                "api": info["api"],
                "mode": "async-local",
                "prompt": info["prompt"],
                "aspect": info["aspect"],
                "resolution": info["resolution"],
                "size": info.get("size_param"),
                "actual_size": info.get("actual_size"),
                "quality": info.get("quality"),
                "duration_s": round(info["duration_s"], 1),
                "file_size_kb": round(info["size"] / 1024, 1),
                "file_path": str(info["path"]),
                "status": "success",
            })
        elif kind == "batch":
            tasks = payload.get("tasks") or []
            concurrent = int(payload.get("concurrent") or DEFAULT_CONCURRENT)
            if not tasks:
                raise RuntimeError("async batch payload has no tasks")
            n = len(tasks)
            log_print(
                f">> async batch job={job_id} tasks={n} concurrent={concurrent}"
            )
            ok = fail = 0
            paths = []

            def one(idx, task):
                info = generate_one(task, name=task.get("name"))
                return idx, info

            with ThreadPoolExecutor(max_workers=max(1, concurrent)) as ex:
                futures = [ex.submit(one, i, t) for i, t in enumerate(tasks)]
                for fut in as_completed(futures):
                    try:
                        idx, info = fut.result()
                        ok += 1
                        paths.append(str(info["path"]))
                        log_print(
                            f"  [{idx+1}/{n}] OK {info['path'].name} "
                            f"({info['model']}/{info['aspect']}/{info['resolution']}, "
                            f"{info['duration_s']:.1f}s)"
                        )
                        emit_result(
                            status="success",
                            job_id=job_id,
                            model=info["model"],
                            provider=info["provider"],
                            api=info["api"],
                            mode="async-local",
                            task_id=info["task_id"],
                            path=info["path"],
                            aspect=info["aspect"],
                            resolution=info["resolution"],
                            size=info.get("size_param"),
                            actual_size=info.get("actual_size"),
                            quality=info.get("quality"),
                            duration_s=round(info["duration_s"], 1),
                            size_kb=round(info["size"] / 1024, 1),
                        )
                        write_log({
                            "timestamp": now_iso(),
                            "job_id": job_id,
                            "task_id": info["task_id"],
                            "model": info["model"],
                            "provider": info["provider"],
                            "api": info["api"],
                            "mode": "async-local",
                            "prompt": info["prompt"],
                            "aspect": info["aspect"],
                            "resolution": info["resolution"],
                            "size": info.get("size_param"),
                            "actual_size": info.get("actual_size"),
                            "quality": info.get("quality"),
                            "duration_s": round(info["duration_s"], 1),
                            "file_size_kb": round(info["size"] / 1024, 1),
                            "file_path": str(info["path"]),
                            "status": "success",
                        })
                    except Exception as e:
                        fail += 1
                        log_print(f"  FAIL: {e}")
                        emit_result(
                            status="failed",
                            job_id=job_id,
                            mode="async-local",
                            error=str(e),
                        )
                        write_log({
                            "timestamp": now_iso(),
                            "job_id": job_id,
                            "mode": "async-local",
                            "status": "failed",
                            "error": str(e),
                        })

            if fail and not ok:
                status = "failed"
            elif fail:
                status = "partial"
            else:
                status = "success"
            result = {
                "ok": ok,
                "fail": fail,
                "total": n,
                "paths": paths,
                "duration_s": round(time.time() - t0, 1),
            }
            update_job(
                job_id,
                status=status,
                finished_at=now_iso(),
                result=result,
                error=None if ok else f"{fail}/{n} tasks failed",
                duration_s=result["duration_s"],
            )
            log_print(f">> async batch done status={status} ok={ok} fail={fail}")
            emit_result(
                status="batch_done",
                job_id=job_id,
                ok=ok,
                fail=fail,
                duration_s=result["duration_s"],
                mode="async-local",
            )
        else:
            raise RuntimeError(f"unknown job kind: {kind}")
    except Exception as e:
        update_job(
            job_id,
            status="failed",
            finished_at=now_iso(),
            error=str(e),
            duration_s=round(time.time() - t0, 1),
        )
        log_print(f">> job failed: {e}")
        emit_result(
            status="failed",
            job_id=job_id,
            mode="async-local",
            error=str(e),
        )
        write_log({
            "timestamp": now_iso(),
            "job_id": job_id,
            "mode": "async-local",
            "status": "failed",
            "error": str(e),
        })
        raise


def run_status(job_id: str):
    job = read_job(job_id)
    print_job_summary(job, verbose=True)
    emit_result(
        status=job.get("status"),
        job_id=job_id,
        kind=job.get("kind"),
        path=(job.get("result") or {}).get("path") if isinstance(job.get("result"), dict) else None,
        error=job.get("error"),
        mode="async-local",
    )
    return job


def run_wait(job_id: str, timeout: float = DEFAULT_WAIT_TIMEOUT):
    t0 = time.time()
    log_print(f">> wait job_id={job_id} timeout={timeout}s")
    while True:
        job = read_job(job_id)
        status = job.get("status") or "unknown"
        if is_terminal_status(status):
            print_job_summary(job, verbose=True)
            emit_result(
                status=status,
                job_id=job_id,
                kind=job.get("kind"),
                path=(job.get("result") or {}).get("path")
                if isinstance(job.get("result"), dict)
                else None,
                error=job.get("error"),
                waited_s=round(time.time() - t0, 1),
                mode="async-local",
            )
            if status == "failed":
                sys.exit(1)
            return job
        if time.time() - t0 >= timeout:
            print_job_summary(job, verbose=True)
            emit_result(
                status="timeout",
                job_id=job_id,
                kind=job.get("kind"),
                waited_s=round(time.time() - t0, 1),
                mode="async-local",
            )
            raise RuntimeError(
                f"wait timeout after {timeout}s; job still {status}. "
                f"Check {job_path(job_id)} / {job_log_path(job_id)}"
            )
        time.sleep(JOB_POLL_INTERVAL)


def run_list_jobs(limit: int = 20):
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(JOBS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        log_print(">> no jobs")
        emit_result(status="empty", mode="async-local", count=0)
        return
    shown = 0
    for path in files:
        if shown >= limit:
            break
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(job, dict):
            continue
        shown += 1
        result = job.get("result") or {}
        path_hint = ""
        if isinstance(result, dict) and result.get("path"):
            path_hint = f" path={result['path']}"
        elif isinstance(result, dict) and result.get("ok") is not None:
            path_hint = f" ok={result.get('ok')} fail={result.get('fail')}"
        log_print(
            f"{job.get('job_id')}\t{job.get('status')}\t{job.get('kind')}\t"
            f"{job.get('updated_at') or job.get('created_at') or ''}{path_hint}"
        )
    emit_result(status="listed", mode="async-local", count=shown)


def safe_filename_stem(text, max_len=36):
    text = (text or "").strip()
    parts = []
    for ch in text:
        if ch.isalnum() or ch in "-_" or "\u4e00" <= ch <= "\u9fff":
            parts.append(ch)
        elif ch.isspace() or ch in ".,，。、/\\:：;；!！?？\"'“”‘’()（）[]【】{}":
            parts.append("_")
    stem = re.sub(r"_+", "_", "".join(parts)).strip("_")
    return (stem or "output")[:max_len]


def make_output_basename(model, prompt, name=None):
    if name:
        return safe_filename_stem(name, max_len=48)
    return f"{model}_{safe_filename_stem(prompt)}"


def find_next_filename(base, ext, out_dir):
    i = 1
    while True:
        dest = out_dir / f"{base}_{i}.{ext}"
        if not dest.exists():
            return dest
        i += 1


def load_local_image_b64(path: Path):
    raw = path.read_bytes()
    if raw[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    elif raw[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        mime = "image/webp"
    elif raw[:6] in (b"GIF87a", b"GIF89a"):
        mime = "image/gif"
    else:
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return mime, base64.b64encode(raw).decode("ascii")


def load_ref_bytes(ref: str):
    """Return (filename, mime, bytes) for a ref path/URL/data-url."""
    if not isinstance(ref, str):
        raise RuntimeError(f"ref must be string, got {type(ref).__name__}")
    low = ref.lower()
    if low.startswith("data:"):
        m = re.match(r"data:([^;,]+);base64,(.+)$", ref, re.S)
        if not m:
            raise RuntimeError("invalid data URL ref")
        mime = m.group(1)
        raw = base64.b64decode(re.sub(r"\s+", "", m.group(2)))
        ext = guess_ext(mime, "png")
        return f"ref.{ext}", mime, raw
    if low.startswith(("http://", "https://")):
        r = request_with_retry("GET", ref, timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"failed to fetch ref URL HTTP {r.status_code}: {ref}")
        ctype = (r.headers.get("Content-Type") or "image/png").split(";")[0].strip()
        if not ctype.startswith("image/"):
            ctype = "image/png"
        ext = guess_ext(ctype, "png")
        return f"ref.{ext}", ctype, r.content
    p = Path(ref).expanduser()
    if not p.is_file():
        raise RuntimeError(f"ref is neither URL nor local file: {ref}")
    mime, b64 = load_local_image_b64(p)
    return p.name, mime, base64.b64decode(b64)


def resolve_ref_parts(refs):
    """Return Gemini parts for reference images (inlineData or file URI text fallback)."""
    parts = []
    for ref in refs or []:
        name, mime, raw = load_ref_bytes(ref)
        b64 = base64.b64encode(raw).decode("ascii")
        parts.append({"inlineData": {"mimeType": mime, "data": b64}})
    return parts


def normalize_output_format(fmt: str | None) -> str | None:
    if fmt is None or fmt is False or fmt == "":
        return None
    f = str(fmt).strip().lower()
    if f == "jpg":
        f = "jpeg"
    return f


def parse_aspect_ratio(aspect: str) -> tuple[int, int]:
    """Parse 'W:H' into ints. 'auto' is not numeric."""
    a = (aspect or "").strip()
    if a.lower() == "auto":
        raise RuntimeError("aspect=auto has no numeric ratio")
    m = re.fullmatch(r"(\d+)\s*:\s*(\d+)", a)
    if not m:
        raise RuntimeError(f"invalid aspect ratio: {aspect}")
    w, h = int(m.group(1)), int(m.group(2))
    if w <= 0 or h <= 0:
        raise RuntimeError(f"invalid aspect ratio: {aspect}")
    return w, h


def normalize_gpt_image_resolution(
    resolution: str | None, *, note: bool = True
) -> str:
    """Normalize resolution; 2K/4K are CPA-US aliases that coerce to 1K."""
    if resolution is None or resolution == "":
        return "1K"
    res = str(resolution).strip()
    res_map = {x.lower(): x for x in RESOLUTIONS_GPT_IMAGE}
    if res in RESOLUTIONS_GPT_IMAGE:
        canonical = res
    elif res.lower() in res_map:
        canonical = res_map[res.lower()]
    else:
        raise RuntimeError(
            f"gpt-image-2 does not support resolution {resolution!r}; "
            f"allowed: {sorted(RESOLUTIONS_GPT_IMAGE)} "
            f"(only 1K/auto are real; 2K/4K coerce to 1K)"
        )
    if canonical in GPT_IMAGE_RESOLUTION_ALIASES:
        real = GPT_IMAGE_RESOLUTION_ALIASES[canonical]
        if note:
            print(
                f"  [note] gpt-image-2 CPA-US has no {canonical} resolution; "
                f"coerced to {real} (quality does not raise pixels; "
                f"use Gemini for true 2K/4K)",
                flush=True,
            )
        return real
    return canonical


def parse_gpt_image_size_string(size: str) -> str:
    """Normalize size to a CPA-US observed 1K preset (or auto).

    Exact dropdown sizes pass through. Known legacy OpenAI 2K/4K sizes are
    remapped to the same-aspect 1K preset. Arbitrary WxH is rejected.
    """
    s = (size or "").strip().lower().replace(" ", "")
    if s == "auto":
        return "auto"
    m = re.fullmatch(r"(\d+)x(\d+)", s)
    if not m:
        popular = sorted(GPT_IMAGE_POPULAR_SIZES)
        raise RuntimeError(
            f"invalid size {size!r}; use auto or a CPA-US 1K preset WxH. "
            f"Supported: {popular}"
        )
    normalized = f"{int(m.group(1))}x{int(m.group(2))}"
    if normalized in GPT_IMAGE_POPULAR_SIZES:
        return normalized
    if normalized in GPT_IMAGE_LEGACY_SIZE_ALIASES:
        mapped = GPT_IMAGE_LEGACY_SIZE_ALIASES[normalized]
        print(
            f"  [note] gpt-image-2 CPA-US has no {normalized}; "
            f"coerced to 1K preset {mapped}",
            flush=True,
        )
        return mapped
    popular = sorted(x for x in GPT_IMAGE_POPULAR_SIZES if x != "auto")
    raise RuntimeError(
        f"gpt-image-2 size {normalized} is not in the CPA-US 1K matrix. "
        f"Supported: {popular} (or auto). "
        f"Note: 2K/4K are not available on this channel; use Gemini for true 4K."
    )


def compute_size_from_aspect_resolution(aspect: str, resolution: str) -> str:
    """Map aspect + resolution to CPA-US 1K size (2K/4K coerce to 1K)."""
    if aspect == "auto" or resolution == "auto":
        return "auto"
    res = normalize_gpt_image_resolution(resolution)
    key = (aspect, res)
    if key in GPT_IMAGE_SIZE_MAP:
        mapped = GPT_IMAGE_SIZE_MAP[key]
        if mapped == "auto":
            return "auto"
        return parse_gpt_image_size_string(mapped)
    raise RuntimeError(
        f"cannot map gpt-image-2 size for aspect={aspect} resolution={resolution}; "
        f"allowed aspects: {sorted(ASPECTS_GPT_IMAGE)}"
    )


def gpt_image_size_for(task: dict, cfg: dict) -> str:
    """Map aspect/resolution or explicit size to CPA-US images size."""
    if task.get("size"):
        return parse_gpt_image_size_string(str(task["size"]))
    aspect = task["aspect"]
    resolution = normalize_gpt_image_resolution(task.get("resolution"))
    task["resolution"] = resolution
    key = (aspect, resolution)
    size_map = cfg.get("size_map") or {}
    if key in size_map:
        size = size_map[key]
        if size == "auto":
            return "auto"
        return parse_gpt_image_size_string(size)
    if aspect in cfg["aspects"] and resolution in cfg["resolutions"]:
        return compute_size_from_aspect_resolution(aspect, resolution)
    raise RuntimeError(
        f"{cfg['id']} cannot map aspect={aspect} resolution={resolution}; "
        f"use aspect in {sorted(cfg['aspects'])}, resolution 1K/auto "
        f"(2K/4K coerce to 1K), or --size from CPA-US 1K presets"
    )


def image_dimensions(data: bytes) -> tuple[int | None, int | None]:
    """Best-effort width/height from PNG/JPEG/WebP/GIF bytes."""
    if not data:
        return None, None
    # PNG
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        import struct
        w, h = struct.unpack(">II", data[16:24])
        return int(w), int(h)
    # GIF
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        import struct
        w, h = struct.unpack("<HH", data[6:10])
        return int(w), int(h)
    # JPEG
    if data[:2] == b"\xff\xd8":
        import struct
        i = 2
        n = len(data)
        while i + 9 < n:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return int(w), int(h)
            if marker == 0xD9 or marker == 0xDA:
                break
            if marker in (0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0x01) or marker == 0xFF:
                i += 2
                continue
            if i + 4 > n:
                break
            seglen = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + seglen
        return None, None
    # WebP (VP8X / VP8 / VP8L)
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and len(data) >= 30:
        import struct
        chunk = data[12:16]
        if chunk == b"VP8X" and len(data) >= 30:
            # canvas size is 24-bit little-endian minus 1
            w = 1 + int.from_bytes(data[24:27], "little")
            h = 1 + int.from_bytes(data[27:30], "little")
            return w, h
        if chunk == b"VP8 " and len(data) >= 30:
            # lossy: width/height at offset 26 (14-bit)
            w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
            h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
            return int(w), int(h)
        if chunk == b"VP8L" and len(data) >= 25:
            b0, b1, b2, b3 = data[21:25]
            w = 1 + (((b1 & 0x3F) << 8) | b0)
            h = 1 + (((b3 & 0xF) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
            return int(w), int(h)
    return None, None


def aspect_from_size_string(size: str) -> str | None:
    if not size or size == "auto":
        return "auto" if size == "auto" else None
    # Prefer exact CPA-US / remapped presets
    if size in GPT_IMAGE_SIZE_TO_ASPECT:
        return GPT_IMAGE_SIZE_TO_ASPECT[size]
    if size in GPT_IMAGE_LEGACY_SIZE_ALIASES:
        mapped = GPT_IMAGE_LEGACY_SIZE_ALIASES[size]
        return GPT_IMAGE_SIZE_TO_ASPECT.get(mapped)
    m = re.fullmatch(r"(\d+)x(\d+)", size)
    if not m:
        return None
    w, h = int(m.group(1)), int(m.group(2))
    # reduce fraction for display (custom sizes should already be rejected)
    from math import gcd
    g = gcd(w, h) or 1
    return f"{w // g}:{h // g}"


def validate_task(task):
    model = task.get("model") or DEFAULT_MODEL
    if model not in MODELS:
        raise RuntimeError(f"unknown model: {model}; available: {sorted(MODELS)}")
    cfg = MODELS[model]
    task["model"] = model
    task["provider"] = cfg["provider"]
    task["api"] = cfg["api"]

    prompt = (task.get("prompt") or "").strip()
    if not prompt:
        raise RuntimeError("prompt is required")
    if len(prompt) > cfg["max_prompt"]:
        raise RuntimeError(f"prompt too long (max {cfg['max_prompt']})")

    if "aspect" not in task and "aspect_ratio" in task:
        task["aspect"] = task["aspect_ratio"]
    if "resolution" not in task and "image_size" in task:
        task["resolution"] = task["image_size"]
    if "ref" not in task and "img_urls" in task:
        task["ref"] = task["img_urls"]

    # Explicit size short-circuits aspect defaults for gpt-image.
    if task.get("size") and cfg["api"] == "images":
        size = parse_gpt_image_size_string(str(task["size"]))
        task["size"] = size
        # keep aspect/resolution as metadata when possible
        if not task.get("aspect"):
            task["aspect"] = aspect_from_size_string(size) or "auto"
        if not task.get("resolution"):
            # CPA-US is 1K-only; auto size keeps resolution=auto
            task["resolution"] = "auto" if size == "auto" else "1K"
        else:
            # User-supplied 2K/4K on gpt-image → coerce to real tier
            task["resolution"] = normalize_gpt_image_resolution(task["resolution"])
        # still validate declared aspect if user supplied it
        if task.get("aspect") and task["aspect"] not in cfg["aspects"] and task["aspect"] != "auto":
            # allow free-form reduced ratios only if somehow present
            if not re.fullmatch(r"\d+:\d+", str(task["aspect"])):
                raise RuntimeError(
                    f"{model} does not support aspect {task['aspect']}; allowed: {sorted(cfg['aspects'])}"
                )
    else:
        if not task.get("aspect"):
            task["aspect"] = cfg["default_aspect"]
        if task["aspect"] not in cfg["aspects"]:
            raise RuntimeError(
                f"{model} does not support aspect {task['aspect']}; allowed: {sorted(cfg['aspects'])}"
            )

        if not task.get("resolution"):
            task["resolution"] = cfg["default_resolution"]
        res = str(task["resolution"]).strip()
        res_map = {x.lower(): x for x in cfg["resolutions"]}
        if res in cfg["resolutions"]:
            task["resolution"] = res
        elif res.lower() in res_map:
            task["resolution"] = res_map[res.lower()]
        else:
            raise RuntimeError(
                f"{model} does not support resolution {task['resolution']}; "
                f"allowed: {sorted(cfg['resolutions'])}"
            )
        # gpt-image: 2K/4K are aliases → coerce to real 1K
        if cfg["api"] == "images":
            task["resolution"] = normalize_gpt_image_resolution(task["resolution"])

    refs = task.get("ref") or []
    if isinstance(refs, str):
        refs = [refs]
        task["ref"] = refs
    if refs and len(refs) > cfg["max_ref"]:
        raise RuntimeError(f"{model} allows at most {cfg['max_ref']} refs")

    # quality / output_format: gpt-image only
    quality = task.get("quality")
    if quality not in (None, False, ""):
        if not cfg.get("supports_quality"):
            raise RuntimeError(f"{model} does not support quality (gpt-image only)")
        q = str(quality).strip().lower()
        if q not in (cfg.get("qualities") or set()):
            raise RuntimeError(
                f"{model} quality must be one of {sorted(cfg.get('qualities') or [])}"
            )
        task["quality"] = q
    elif cfg.get("supports_quality"):
        task["quality"] = cfg.get("default_quality") or "auto"
    else:
        task["quality"] = None

    out_fmt = normalize_output_format(task.get("output_format"))
    if out_fmt:
        if not cfg.get("supports_output_format"):
            raise RuntimeError(
                f"{model} does not support output_format; server returns image bytes"
            )
        if out_fmt not in (cfg.get("output_formats") or set()) and out_fmt != "jpeg":
            # jpeg already normalized; jpg accepted via normalize
            if out_fmt not in {"png", "jpeg", "webp"}:
                raise RuntimeError(
                    f"{model} output_format must be one of png/jpeg/webp"
                )
        if out_fmt not in (cfg.get("output_formats") or {"png", "jpeg", "webp"}):
            # allow jpeg even if set has jpg
            if out_fmt != "jpeg":
                raise RuntimeError(
                    f"{model} output_format must be one of {sorted(cfg.get('output_formats') or [])}"
                )
        task["output_format"] = out_fmt
    elif cfg.get("supports_output_format"):
        task["output_format"] = cfg.get("default_output_format") or "png"
    else:
        task["output_format"] = None

    google_search = bool(task.get("google_search"))
    if google_search and not cfg.get("supports_google_search"):
        raise RuntimeError(f"{model} does not support --google-search")
    task["google_search"] = google_search

    if cfg["api"] == "images":
        task["size"] = gpt_image_size_for(task, cfg)

    return task


def build_generate_content_body(task):
    parts = [{"text": task["prompt"]}]
    parts.extend(resolve_ref_parts(task.get("ref") or []))

    image_config = {
        "aspectRatio": task["aspect"],
        "imageSize": task["resolution"],
    }
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": image_config,
        },
    }
    if task.get("google_search"):
        body["tools"] = [{"google_search": {}}]
    return body


def extract_images_from_generate_content(resp):
    if not isinstance(resp, dict):
        raise RuntimeError(f"response is not object: {type(resp).__name__}")
    if resp.get("error"):
        err = resp["error"]
        if isinstance(err, dict):
            raise RuntimeError(f"CPA/Gemini error: {err.get('message') or err}")
        raise RuntimeError(f"CPA/Gemini error: {err}")

    candidates = resp.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"no candidates in response: keys={list(resp.keys())}")

    images = []
    texts = []
    for cand in candidates:
        content = cand.get("content") or {}
        for part in content.get("parts") or []:
            if not isinstance(part, dict):
                continue
            if "text" in part and part["text"]:
                texts.append(part["text"])
            ind = part.get("inlineData") or part.get("inline_data")
            if isinstance(ind, dict) and ind.get("data"):
                mime = ind.get("mimeType") or ind.get("mime_type") or "image/jpeg"
                try:
                    data = base64.b64decode(re.sub(r"\s+", "", ind["data"]))
                except Exception as e:
                    raise RuntimeError(f"inlineData base64 decode failed: {e}")
                images.append({"mime": mime, "data": data})
            fd = part.get("fileData") or part.get("file_data")
            if isinstance(fd, dict) and fd.get("fileUri"):
                images.append({"url": fd["fileUri"], "mime": fd.get("mimeType") or "image/jpeg"})

    if not images:
        raise RuntimeError(
            f"no image parts in response; texts={texts[:1]!r} finish={((candidates[0] or {}).get('finishReason'))}"
        )
    return images, texts


def extract_images_from_openai_images(resp):
    if not isinstance(resp, dict):
        raise RuntimeError(f"response is not object: {type(resp).__name__}")
    if resp.get("error"):
        err = resp["error"]
        if isinstance(err, dict):
            raise RuntimeError(f"CPA/OpenAI images error: {err.get('message') or err}")
        raise RuntimeError(f"CPA/OpenAI images error: {err}")
    data = resp.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"no data[] in images response: keys={list(resp.keys())}")
    images = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if item.get("b64_json"):
            raw = base64.b64decode(re.sub(r"\s+", "", item["b64_json"]))
            images.append({"mime": "image/png", "data": raw})
        elif item.get("url"):
            images.append({"url": item["url"], "mime": "image/png"})
    if not images:
        raise RuntimeError("images response data had no b64_json/url")
    return images, []


def guess_ext(mime_or_bytes, default="jpg"):
    if isinstance(mime_or_bytes, (bytes, bytearray)):
        b = mime_or_bytes
        if b[:3] == b"\xff\xd8\xff":
            return "jpg"
        if b[:8] == b"\x89PNG\r\n\x1a\n":
            return "png"
        if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
            return "webp"
        return default
    mime = (mime_or_bytes or "").lower()
    if "png" in mime:
        return "png"
    if "webp" in mime:
        return "webp"
    if "gif" in mime:
        return "gif"
    if "jpeg" in mime or "jpg" in mime:
        return "jpg"
    return default


def save_image_obj(img, dest):
    if "data" in img:
        dest.write_bytes(img["data"])
        return len(img["data"])
    url = img.get("url")
    if not url:
        raise RuntimeError(f"unknown image object: {img.keys()}")
    if url.startswith("data:"):
        m = re.match(r"data:([^;,]+)?(;base64)?,(.*)$", url, re.S)
        if not m:
            raise RuntimeError("invalid data URL")
        raw = re.sub(r"\s+", "", m.group(3))
        data = base64.b64decode(raw) if m.group(2) else raw.encode("utf-8")
        dest.write_bytes(data)
        return len(data)
    r = request_with_retry("GET", url, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"download failed HTTP {r.status_code}")
    dest.write_bytes(r.content)
    return len(r.content)


def generate_content_url(base: str, model_id: str) -> str:
    return f"{base}/v1beta/models/{model_id}:generateContent"


def submit_gemini(task):
    provider = "cpa-jp"
    require_api_key(provider)
    cfg = MODELS[task["model"]]
    base = provider_base(provider)
    body = build_generate_content_body(task)
    url = generate_content_url(base, cfg["id"])
    r = request_with_retry(
        "POST", url, headers=headers_for(provider), json=body, timeout=TIMEOUT_SUBMIT
    )
    try:
        d = r.json()
    except Exception:
        raise RuntimeError(f"non-JSON HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code >= 400:
        raise RuntimeError(
            format_http_error(r.status_code, r.text or json.dumps(d, ensure_ascii=False))
        )
    images, texts = extract_images_from_generate_content(d)
    tid = d.get("responseId") or d.get("id") or f"cpa-{int(time.time())}"
    return {
        "task_id": tid,
        "images": images,
        "texts": texts,
        "usage": d.get("usageMetadata") or d.get("usage"),
        "model": cfg["id"],
        "provider": provider,
        "api": "generateContent",
        "raw_model_version": d.get("modelVersion"),
        "base": base,
    }


def submit_gpt_image(task):
    provider = "cpa-us"
    require_api_key(provider)
    cfg = MODELS[task["model"]]
    base = provider_base(provider)
    size = task.get("size") or gpt_image_size_for(task, cfg)
    quality = task.get("quality") or cfg.get("default_quality") or "auto"
    output_format = task.get("output_format") or cfg.get("default_output_format") or "png"
    if output_format == "jpg":
        output_format = "jpeg"

    refs = task.get("ref") or []
    if refs:
        # image-to-image / edits (multipart)
        url = f"{base}/v1/images/edits"
        files = []
        opened = []
        try:
            for i, ref in enumerate(refs):
                name, mime, raw = load_ref_bytes(ref)
                # CPA/OpenAI variants accept image or image[]
                field = "image" if i == 0 and len(refs) == 1 else "image[]"
                files.append((field, (name or f"ref_{i}.png", raw, mime)))
            data = {
                "model": cfg["id"],
                "prompt": task["prompt"],
                "size": size,
                "n": "1",
                "quality": quality,
            }
            # Some gateways accept output_format on edits; ignore if rejected by caller retry path.
            if output_format:
                data["output_format"] = output_format
            headers = {"Authorization": f"Bearer {require_api_key(provider)}"}
            r = request_with_retry(
                "POST", url, headers=headers, data=data, files=files, timeout=TIMEOUT_SUBMIT
            )
        finally:
            for fh in opened:
                try:
                    fh.close()
                except Exception:
                    pass
    else:
        url = f"{base}/v1/images/generations"
        body = {
            "model": cfg["id"],
            "prompt": task["prompt"],
            "size": size,
            "n": 1,
            "quality": quality,
        }
        if output_format:
            body["output_format"] = output_format
        r = request_with_retry(
            "POST",
            url,
            headers=headers_for(provider),
            json=body,
            timeout=TIMEOUT_SUBMIT,
        )

    try:
        d = r.json()
    except Exception:
        raise RuntimeError(f"non-JSON HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code >= 400:
        raise RuntimeError(
            format_http_error(r.status_code, r.text or json.dumps(d, ensure_ascii=False))
        )
    images, texts = extract_images_from_openai_images(d)
    # Prefer declared output format mime when b64
    if output_format and images and "data" in images[0]:
        mime = {
            "png": "image/png",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
        }.get(output_format, images[0].get("mime") or "image/png")
        images[0]["mime"] = mime
    tid = d.get("id") or d.get("created") or f"gptimg-{int(time.time())}"
    return {
        "task_id": str(tid),
        "images": images,
        "texts": texts,
        "usage": d.get("usage"),
        "model": cfg["id"],
        "provider": provider,
        "api": "images/edits" if refs else "images/generations",
        "size": size,
        "quality": quality,
        "output_format": output_format,
        "base": base,
    }


def submit(task):
    task = validate_task(task)
    api = task["api"]
    if api == "generateContent":
        return submit_gemini(task)
    if api == "images":
        return submit_gpt_image(task)
    raise RuntimeError(f"unsupported api for model {task['model']}: {api}")


def list_models(provider: str | None = None):
    """Prefer OpenAI-compatible /v1/models on the provider base."""
    providers = [provider] if provider else list(PROVIDERS.keys())
    all_ids = []
    for p in providers:
        if not provider_api_key(p):
            continue
        base = provider_base(p)
        try:
            r = request_with_retry(
                "GET",
                f"{base}/v1/models",
                headers=headers_for(p),
                timeout=TIMEOUT_MODELS,
            )
            if r.status_code < 400:
                data = r.json().get("data") or []
                ids = [m.get("id") for m in data if isinstance(m, dict) and m.get("id")]
                all_ids.extend(ids)
                continue
        except Exception:
            pass
    # Always include configured skill models
    for mid in MODELS:
        if mid not in all_ids:
            all_ids.append(mid)
    # de-dupe preserve order
    seen = set()
    out = []
    for mid in all_ids:
        if mid in seen:
            continue
        seen.add(mid)
        out.append(mid)
    return out


def run_preflight(model: str | None = None):
    model = model or DEFAULT_MODEL
    if model not in MODELS:
        raise RuntimeError(f"unknown model: {model}; available: {sorted(MODELS)}")
    cfg = MODELS[model]
    provider = cfg["provider"]
    base = provider_base(provider)
    log_print(">> Preflight (multi-provider CPA image)")
    log_print(f"   script  : {Path(__file__).resolve()}")
    log_print(f"   model   : {model}")
    log_print(f"   provider: {provider} ({PROVIDERS[provider]['label']})")
    log_print(f"   api     : {cfg['api']}")
    log_print(f"   base    : {base}")
    if cfg["api"] == "generateContent":
        log_print("   endpoint: /v1beta/models/<model>:generateContent")
    else:
        log_print("   endpoint: /v1/images/generations (| /v1/images/edits with --ref)")
    log_print(f"   out     : {OUT_DIR}")
    require_api_key(provider)
    log_print("   api key : PASS")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    probe = OUT_DIR / ".cpa_preflight.tmp"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    log_print("   workdir : PASS")
    ids = list_models(provider)
    hit = model in ids
    log_print(f"   models  : {len(ids)} listed; {model}={'yes' if hit else 'NO'}")
    if not hit:
        log_print("   warn    : model not in /v1/models list; endpoint may still work")
    # show configured models map
    log_print("   configured models:")
    for mid, mcfg in MODELS.items():
        key_ok = "yes" if provider_api_key(mcfg["provider"]) else "NO"
        log_print(
            f"     - {mid} -> provider={mcfg['provider']} api={mcfg['api']} key={key_ok}"
        )
    log_print(">> Preflight OK")


def generate_one(task, name=None):
    task = validate_task(task)
    t0 = time.time()
    last_err = None
    result = None
    for attempt in range(MAX_RETRIES + 1):
        if attempt:
            log_print(f"  [retry] {RETRY_DELAY}s ({attempt}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
        try:
            result = submit(task)
            break
        except Exception as e:
            last_err = e
            if is_non_retryable_error(e):
                log_print(f"  [no-retry] {e}")
                break
            log_print(f"  [retryable] {e}")
    if result is None:
        raise RuntimeError(last_err or "generation failed")

    img = result["images"][0]
    if "data" in img:
        ext = guess_ext(img.get("mime") or img["data"])
    else:
        ext = guess_ext(img.get("mime"), "png" if task.get("api") == "images" else "jpg")
    # Prefer declared output format extension for gpt-image
    if task.get("output_format"):
        of = task["output_format"]
        ext = {"png": "png", "jpeg": "jpg", "jpg": "jpg", "webp": "webp"}.get(of, ext)
    base = make_output_basename(task["model"], task["prompt"], name=name or task.get("name"))
    dest = find_next_filename(base, ext, OUT_DIR)
    size = save_image_obj(img, dest)
    # Actual pixel size from saved file (CPA/upstream may rewrite requested size)
    actual_w = actual_h = None
    try:
        raw = dest.read_bytes()
        actual_w, actual_h = image_dimensions(raw)
    except Exception:
        pass
    if actual_w is None and "data" in img:
        actual_w, actual_h = image_dimensions(img["data"])
    actual_size = f"{actual_w}x{actual_h}" if actual_w and actual_h else None
    requested_size = result.get("size") or task.get("size")
    if (
        actual_size
        and requested_size
        and requested_size != "auto"
        and actual_size != requested_size
    ):
        log_print(
            f"  [note] requested size={requested_size} but actual output={actual_size}"
        )
    dur = time.time() - t0
    return {
        "task_id": result["task_id"],
        "path": dest,
        "size": size,
        "duration_s": dur,
        "model": task["model"],
        "provider": result.get("provider") or task["provider"],
        "api": result.get("api") or task["api"],
        "prompt": task["prompt"],
        "aspect": task.get("aspect"),
        "resolution": task.get("resolution"),
        "size_param": requested_size,
        "actual_size": actual_size,
        "actual_width": actual_w,
        "actual_height": actual_h,
        "quality": result.get("quality") or task.get("quality"),
        "output_format": result.get("output_format") or task.get("output_format"),
        "usage": result.get("usage"),
        "n_images": len(result["images"]),
    }


def run_single(args):
    task = {
        "prompt": args.prompt,
        "model": args.model,
        "aspect": args.aspect,
        "resolution": args.resolution,
        "size": args.size,
        "ref": args.ref,
        "google_search": args.google_search,
        "quality": args.quality,
        "output_format": args.output_format,
    }
    # drop Nones so validate defaults apply cleanly
    task = {k: v for k, v in task.items() if v is not None and v is not False}
    if args.google_search:
        task["google_search"] = True

    validated = validate_task(dict(task))
    provider = validated["provider"]
    api = validated["api"]
    base = provider_base(provider)
    log_print(f">> model: {validated['model']}  provider: {provider}  api: {api}")
    log_print(f">> base: {base}")
    log_print(f">> prompt: {args.prompt}")
    if validated.get("aspect"):
        log_print(f">> aspect: {validated['aspect']}")
    if validated.get("resolution"):
        log_print(f">> resolution: {validated['resolution']}")
    if validated.get("size"):
        log_print(f">> size: {validated['size']}")
    if validated.get("quality"):
        log_print(f">> quality: {validated['quality']}")
    if validated.get("output_format"):
        log_print(f">> output_format: {validated['output_format']}")
    if args.ref:
        log_print(f">> refs: {len(args.ref)}")
    if args.google_search:
        log_print(">> google_search: on")

    if getattr(args, "async_mode", False):
        submit_async_job(
            "single",
            {"task": validated, "name": args.name},
        )
        return
    try:
        info = generate_one(task, name=args.name)
    except Exception as e:
        log_print(f">> failed: {e}", file=sys.stderr)
        write_log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "model": args.model,
            "prompt": args.prompt,
            "status": "failed",
            "error": str(e),
            "provider": provider,
            "api": api,
        })
        emit_result(
            status="failed",
            model=args.model,
            provider=provider,
            api=api,
            error=str(e),
        )
        sys.exit(1)

    log_print(">> done")
    log_print(f"   model      : {info['model']}")
    log_print(f"   provider   : {info['provider']}")
    log_print(f"   api        : {info['api']}")
    log_print(f"   aspect     : {info['aspect']}")
    log_print(f"   resolution : {info['resolution']}")
    if info.get("size_param"):
        log_print(f"   size       : {info['size_param']}")
    if info.get("actual_size"):
        log_print(f"   actual     : {info['actual_size']}")
    if info.get("quality"):
        log_print(f"   quality    : {info['quality']}")
    log_print(f"   task_id    : {info['task_id']}")
    log_print(f"   duration   : {info['duration_s']:.1f}s")
    log_print(f"   file_size  : {info['size']/1024:.1f} KB")
    log_print(f"   path       : {info['path']}")
    if info.get("usage"):
        log_print(f"   usage      : {info['usage']}")
    emit_result(
        status="success",
        model=info["model"],
        provider=info["provider"],
        api=info["api"],
        task_id=info["task_id"],
        path=info["path"],
        aspect=info["aspect"],
        resolution=info["resolution"],
        size=info.get("size_param"),
        actual_size=info.get("actual_size"),
        quality=info.get("quality"),
        duration_s=round(info["duration_s"], 1),
        size_kb=round(info["size"] / 1024, 1),
    )
    write_log({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "task_id": info["task_id"],
        "model": info["model"],
        "provider": info["provider"],
        "api": info["api"],
        "prompt": info["prompt"],
        "aspect": info["aspect"],
        "resolution": info["resolution"],
        "size": info.get("size_param"),
        "actual_size": info.get("actual_size"),
        "quality": info.get("quality"),
        "duration_s": round(info["duration_s"], 1),
        "file_size_kb": round(info["size"] / 1024, 1),
        "file_path": str(info["path"]),
        "usage": info.get("usage"),
        "status": "success",
    })


def load_batch(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "tasks" in data:
        tasks = data["tasks"]
    else:
        tasks = data
    if not isinstance(tasks, list) or not tasks:
        raise RuntimeError("batch must be a non-empty task array or {tasks:[...]}")
    out = []
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            raise RuntimeError(f"task {i+1} must be an object")
        if "model" not in t:
            t["model"] = DEFAULT_MODEL
        out.append(validate_task(t))
    return out


def run_batch(args):
    tasks = load_batch(args.batch)
    n = len(tasks)
    models = sorted({t["model"] for t in tasks})
    log_print(
        f">> batch: {n} tasks, concurrent={args.concurrent}, models={models}"
    )
    if getattr(args, "async_mode", False):
        submit_async_job(
            "batch",
            {"tasks": tasks, "concurrent": args.concurrent},
        )
        return
    ok = fail = 0
    t0 = time.time()

    def one(idx, task):
        info = generate_one(task, name=task.get("name"))
        return idx, info

    with ThreadPoolExecutor(max_workers=max(1, args.concurrent)) as ex:
        futures = [ex.submit(one, i, t) for i, t in enumerate(tasks)]
        for fut in as_completed(futures):
            try:
                idx, info = fut.result()
                ok += 1
                log_print(
                    f"  [{idx+1}/{n}] OK {info['path'].name} "
                    f"({info['model']}/{info['aspect']}/{info['resolution']}, "
                    f"{info['duration_s']:.1f}s)"
                )
                emit_result(
                    status="success",
                    model=info["model"],
                    provider=info["provider"],
                    api=info["api"],
                    task_id=info["task_id"],
                    path=info["path"],
                    aspect=info["aspect"],
                    resolution=info["resolution"],
                    size=info.get("size_param"),
                    actual_size=info.get("actual_size"),
                    quality=info.get("quality"),
                    duration_s=round(info["duration_s"], 1),
                    size_kb=round(info["size"] / 1024, 1),
                )
                write_log({
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "task_id": info["task_id"],
                    "model": info["model"],
                    "provider": info["provider"],
                    "api": info["api"],
                    "prompt": info["prompt"],
                    "aspect": info["aspect"],
                    "resolution": info["resolution"],
                    "size": info.get("size_param"),
                    "actual_size": info.get("actual_size"),
                    "quality": info.get("quality"),
                    "duration_s": round(info["duration_s"], 1),
                    "file_size_kb": round(info["size"] / 1024, 1),
                    "file_path": str(info["path"]),
                    "status": "success",
                })
            except Exception as e:
                fail += 1
                log_print(f"  FAIL: {e}")
                emit_result(status="failed", error=str(e))
                write_log({
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "status": "failed",
                    "error": str(e),
                })

    total = time.time() - t0
    log_print(f">> batch done ok={ok} fail={fail} duration={total:.1f}s")
    emit_result(status="batch_done", ok=ok, fail=fail, duration_s=round(total, 1))
    if fail and not ok:
        sys.exit(1)


def build_arg_parser():
    ap = argparse.ArgumentParser(
        description=(
            "Genius CPA Image — multi-provider CPA image generation "
            "(Gemini generateContent + OpenAI images / gpt-image-2)"
        )
    )
    ap.add_argument("prompt", nargs="?", help="image prompt")
    ap.add_argument("--batch", help="batch JSON path")
    ap.add_argument("--concurrent", type=int, default=DEFAULT_CONCURRENT)
    ap.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=list(MODELS.keys()),
        help="model id; selects provider automatically",
    )
    ap.add_argument(
        "--aspect",
        default=None,
        help=(
            "aspect ratio. Gemini: many incl. 16:9/9:16/1:4...; "
            "gpt-image-2 CPA-US: 1:1 3:2 2:3 4:3 3:4 5:4 4:5 "
            "16:9 9:16 21:9 9:21 2:1 1:2 auto"
        ),
    )
    ap.add_argument(
        "--resolution",
        default=None,
        help=(
            "Gemini imageSize 0.5K/1K/2K/4K; "
            "gpt-image-2 CPA-US: only 1K/auto are real (2K/4K coerce to 1K)"
        ),
    )
    ap.add_argument(
        "--size",
        default=None,
        help=(
            "gpt-image-2 CPA-US 1K size presets only: auto or "
            "1024x1024 1672x941 941x1672 1443x1090 1090x1443 "
            "1536x1024 1024x1536 1408x1120 1120x1408 "
            "1920x832 832x1920 1792x896 896x1792. "
            "Legacy 2K/4K sizes (e.g. 3840x2160) coerce to same-aspect 1K."
        ),
    )
    ap.add_argument(
        "--quality",
        default=None,
        choices=sorted(GPT_IMAGE_QUALITIES),
        help="gpt-image-2 only: low|medium|high|auto",
    )
    ap.add_argument(
        "--output-format",
        dest="output_format",
        default=None,
        choices=["png", "jpeg", "jpg", "webp"],
        help="gpt-image-2 only: png|jpeg|webp",
    )
    ap.add_argument("--ref", nargs="+", help="reference image URL(s) or local path(s)")
    ap.add_argument(
        "--google-search",
        dest="google_search",
        action="store_true",
        help="Gemini only: enable tools.google_search grounding",
    )
    ap.add_argument("--name", default=None, help="output basename without extension")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--no-gen", action="store_true", help="required with --preflight")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--out", default=None, help="output directory (default ./genius_output)")
    ap.add_argument(
        "--async",
        dest="async_mode",
        action="store_true",
        help="submit single/batch job and return immediately",
    )
    ap.add_argument("--status", metavar="JOB_ID", help="show local async job status")
    ap.add_argument("--wait", metavar="JOB_ID", help="wait until local async job finishes")
    ap.add_argument("--list-jobs", action="store_true", help="list recent local async jobs")
    ap.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_WAIT_TIMEOUT,
        help=f"seconds for --wait (default {DEFAULT_WAIT_TIMEOUT})",
    )
    ap.add_argument("--_run-job", dest="run_job", metavar="JOB_ID", help=argparse.SUPPRESS)
    return ap


def main():
    configure_stdio()
    ap = build_arg_parser()
    args = ap.parse_args()

    global OUT_DIR, LOG_DIR, LOG_FILE, JOBS_DIR
    if args.out:
        OUT_DIR = Path(args.out).expanduser().resolve()
    else:
        OUT_DIR = Path(OUT_DIR).expanduser().resolve()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR = OUT_DIR / "Logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE = LOG_DIR / "cpa_image_log.jsonl"
    JOBS_DIR = OUT_DIR / "Jobs"
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        if args.run_job:
            clean_old_logs()
            run_job_worker(args.run_job)
            return
        if args.preflight:
            if not args.no_gen:
                raise RuntimeError("--preflight requires --no-gen")
            run_preflight(args.model)
            return
        if args.list_models:
            # If model selected, list that provider first; else all configured providers.
            provider = None
            if args.model in MODELS:
                # only force provider when user explicitly chose non-default? list both if keys exist
                provider = None
            for mid in list_models(provider):
                log_print(mid)
            return
        if args.list_jobs:
            run_list_jobs()
            return
        if args.status:
            run_status(args.status)
            return
        if args.wait:
            run_wait(args.wait, timeout=args.timeout)
            return
        clean_old_logs()
        if args.batch:
            run_batch(args)
        elif args.prompt:
            run_single(args)
        else:
            ap.error(
                "need prompt, --batch, --preflight, --list-models, "
                "--status, --wait, or --list-jobs"
            )
    except RuntimeError as e:
        sys.exit(f"ERROR: {e}")


if __name__ == "__main__":
    main()
