"""
Model client for genius-footage: one Gemini-style generateContent request per call (CPA relay by default),
plus the compressed whole-clip proxy. Config comes from the environment or scripts/.env:

    FOOTAGE_API_KEY (or CPA_API_KEY)   required
    FOOTAGE_BASE_URL                   default https://cpa-jp.charles-ai.space/v1
    FOOTAGE_MODEL                      default gemini-4-argon-high
    FOOTAGE_MAX_REQUESTS               model requests in flight across all clips of one run (default 8)
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

DEFAULT_BASE_URL = "https://cpa-jp.charles-ai.space/v1"
DEFAULT_MODEL = "gemini-4-argon-high"
RETRY_HTTP = {429, 500, 502, 503, 504}
RETRY_DELAYS = (5, 15, 30)
REFUSAL_RE = re.compile(r"content (?:policy|filter)", re.I)   # short canned refusals
PROXY_DIR = Path(tempfile.gettempdir()) / "genius-footage-proxy"
PROXY_FPS, PROXY_SCALE, AUDIO_KBPS = 2, 1280, 64
BUDGET_BYTES = 30 * 1024 * 1024        # one inline request
MAX_VIDEO_SEC = 1800                   # longer clips skip the whole-clip step
MAX_REQUESTS = 8                       # all clips of one run share this cap (more makes the CPA gateway 502)
EXIT_CODES = {"INPUT_NOT_FOUND": 3, "UNSUPPORTED_FORMAT": 4, "DEPENDENCY_MISSING": 5,
              "PROVIDER_ERROR": 6, "TIMEOUT": 7}


class FootageError(RuntimeError):
    """Failure carrying an error code (EXIT_CODES)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ── Config ───────────────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def _dotenv(path: Path = Path(__file__).parent / ".env") -> dict:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                out[name.strip()] = value.strip().strip('"').strip("'")
    return out


def _env(name: str) -> str:
    return (os.environ.get(name) or _dotenv().get(name) or "").strip()


def set_limit(n: int) -> None:
    """Model requests in flight for the whole process, however many clips run at once."""
    global _gate
    _gate = threading.BoundedSemaphore(max(1, n))


def conf(model: str | None = None) -> dict:
    return {"base_url": (_env("FOOTAGE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
            "model": model or _env("FOOTAGE_MODEL") or DEFAULT_MODEL,
            "api_key": _env("FOOTAGE_API_KEY") or _env("CPA_API_KEY")}


_gate = threading.BoundedSemaphore(max(1, int(_env("FOOTAGE_MAX_REQUESTS") or MAX_REQUESTS)))


def fingerprint(path: str) -> str:
    p, st = Path(path), Path(path).stat()
    h = hashlib.sha1(str(p.resolve()).encode("utf-8", errors="replace"))
    h.update(f"{st.st_size}{int(st.st_mtime)}".encode())
    return h.hexdigest()[:16]


# ── Request ──────────────────────────────────────────────────────────────

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".mp4": "video/mp4", ".mov": "video/quicktime"}


def _post(url: str, key: str, body: dict, timeout: float) -> dict:
    proxy = next((os.environ[n] for n in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY",
                                          "all_proxy") if os.environ.get(n)), None)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {}))
    data = json.dumps(body).encode("utf-8")
    for attempt, delay in enumerate((*RETRY_DELAYS, None), 1):
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {key}", "x-goog-api-key": key})
        try:
            with _gate, opener.open(req, timeout=timeout) as resp:  # the slot is free again while retrying
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", errors="replace")[:300]
            err, transient = FootageError("PROVIDER_ERROR", f"API error {e.code}: {msg}"), e.code in RETRY_HTTP
        except (socket.timeout, TimeoutError) as e:
            raise FootageError("TIMEOUT", f"No response within {timeout:g}s") from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise FootageError("TIMEOUT", f"No response within {timeout:g}s") from e
            err, transient = FootageError("PROVIDER_ERROR", f"Network error: {e.reason}"), True
        except (http.client.HTTPException, ConnectionError) as e:  # getresponse() bypasses URLError
            err, transient = FootageError("PROVIDER_ERROR", f"Connection dropped: {e}"), True
        if delay is None or not transient:  # timeouts are not retried: a slow request would only repeat
            raise err
        print(f"[genius-footage] {err} — retry {attempt}/{len(RETRY_DELAYS)} in {delay}s…", file=sys.stderr)
        time.sleep(delay)


def call(c: dict, files: list[str], prompt: str, timeout: float) -> str:
    """One request: local files (inline) before the prompt. A canned refusal is a PROVIDER_ERROR."""
    parts = [{"inline_data": {"mime_type": MIME.get(Path(f).suffix.lower(), "application/octet-stream"),
                              "data": base64.b64encode(Path(f).read_bytes()).decode("ascii")}} for f in files]
    root = re.sub(r"/(v1|v1beta/openai|openai)$", "", c["base_url"])
    data = _post(f"{root}/v1beta/models/{c['model']}:generateContent", c["api_key"],
                 {"contents": [{"role": "user", "parts": parts + [{"text": prompt}]}],
                  "generationConfig": {"maxOutputTokens": 32768}}, timeout)
    texts, thoughts = [], []
    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            if isinstance(part, dict) and part.get("text"):
                (thoughts if part.get("thought") else texts).append(part["text"])
    text = "\n".join(texts or thoughts).strip()
    if not text:
        err = data.get("error")
        raise FootageError("PROVIDER_ERROR", f"API error: {err.get('message') if isinstance(err, dict) else err}"
                           if err else f"Empty model response: {json.dumps(data, ensure_ascii=False)[:300]}")
    if len(text) < 300 and REFUSAL_RE.search(text):
        raise FootageError("PROVIDER_ERROR", f"Model refused: {text}")
    return text


# ── Whole-clip proxy ─────────────────────────────────────────────────────

def video_proxy(src: str, duration: float) -> str:
    """2 fps, ≤1280 px, H.264 + mono AAC, sized to fit one request; cached by file fingerprint."""
    kbps = int(max(50, min(1500, BUDGET_BYTES * 8 / 1000 * 0.92 / max(duration, 1) - AUDIO_KBPS)))
    PROXY_DIR.mkdir(parents=True, exist_ok=True)
    out = PROXY_DIR / f"{fingerprint(src)}-{kbps}k.mp4"
    if out.is_file() and out.stat().st_size:
        return str(out)
    if not shutil.which("ffmpeg"):
        raise FootageError("DEPENDENCY_MISSING", "ffmpeg not found on PATH")
    s, tmp = PROXY_SCALE, out.with_suffix(".part.mp4")
    vf = f"fps={PROXY_FPS},scale='if(gte(iw,ih),min({s},iw),-2)':'if(gte(iw,ih),-2,min({s},ih))'"
    encoders = (["h264_videotoolbox"] if sys.platform == "darwin" else []) + ["libx264"]
    for enc in encoders:
        p = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-vf", vf, "-c:v", enc,
                            "-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.25)}k", "-bufsize", f"{kbps * 2}k",
                            "-c:a", "aac", "-b:a", f"{AUDIO_KBPS}k", "-ac", "1", "-movflags", "+faststart", str(tmp)],
                           capture_output=True, text=True)
        if p.returncode == 0 and tmp.is_file() and tmp.stat().st_size:
            tmp.replace(out)
            print(f"[genius-footage] whole-clip proxy via {enc}: {out.stat().st_size / 1048576:.1f}MB → {out}",
                  file=sys.stderr)
            return str(out)
        tmp.unlink(missing_ok=True)
    raise FootageError("UNSUPPORTED_FORMAT", f"cannot encode a proxy of {src}: {p.stderr.strip()[-300:]}")
