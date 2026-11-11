"""
Shared pieces of genius-footage: the model client (one Gemini-style generateContent request per call, CPA relay
by default), the HTTP retry loop, storyboard questions asked side by side (ask), and the per-file cache
(whole-clip proxy, measured cuts, transcript). Config comes from the environment or scripts/.env:

    FOOTAGE_API_KEY (or CPA_API_KEY)   required
    FOOTAGE_BASE_URL                   default https://cpa-jp.charles-ai.space/v1
    FOOTAGE_MODEL                      default gemini-4-argon-high
    FOOTAGE_MAX_REQUESTS               model requests in flight across all clips of one run (default 8)
"""

from __future__ import annotations

import base64
import contextlib
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
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

DEFAULT_BASE_URL = "https://cpa-jp.charles-ai.space/v1"
DEFAULT_MODEL = "gemini-4-argon-high"
RETRY_HTTP = {429, 500, 502, 503, 504}
RETRY_DELAYS = (5, 15, 30)
REFUSAL_RE = re.compile(r"content (?:policy|filter)", re.I)   # short canned refusals
CACHE_DIR = Path(tempfile.gettempdir()) / "genius-footage-proxy"   # proxies, measured cuts, transcripts
PROXY_FPS, PROXY_SCALE, AUDIO_KBPS = 2, 1280, 64
BUDGET_BYTES = 30 * 1024 * 1024        # one inline request
MAX_VIDEO_SEC = 1800                   # longer clips skip the whole-clip step
MAX_REQUESTS = 8                       # all clips of one run share this cap (more makes the CPA gateway 502)
EXIT_CODES = {"INPUT_NOT_FOUND": 3, "UNSUPPORTED_FORMAT": 4, "DEPENDENCY_MISSING": 5,
              "PROVIDER_ERROR": 6, "TIMEOUT": 7}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v", ".mxf"}
ctx = threading.local()                # .tag = short clip name, prefixed to log lines when several clips run


class FootageError(RuntimeError):
    """Failure carrying an error code (EXIT_CODES)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def tagged(fn):
    """fn run in a worker thread keeps the calling clip's log tag."""
    tag = getattr(ctx, "tag", None)

    def call(*a, **k):
        ctx.tag = tag
        return fn(*a, **k)
    return call


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
    global _gate, _limit
    _limit = max(1, n)
    _gate = threading.BoundedSemaphore(_limit)


set_limit(int(_env("FOOTAGE_MAX_REQUESTS") or MAX_REQUESTS))


def conf(model: str | None = None) -> dict:
    return {"base_url": (_env("FOOTAGE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
            "model": model or _env("FOOTAGE_MODEL") or DEFAULT_MODEL,
            "api_key": _env("FOOTAGE_API_KEY") or _env("CPA_API_KEY")}


# ── Per-file cache ───────────────────────────────────────────────────────

def fingerprint(path: str) -> str:
    p, st = Path(path), Path(path).stat()
    h = hashlib.sha1(str(p.resolve()).encode("utf-8", errors="replace"))
    h.update(f"{st.st_size}{int(st.st_mtime)}".encode())
    return h.hexdigest()[:16]


def cached(src: str, name: str, fn, code: str):
    """fn()'s JSON result, kept in CACHE_DIR per file fingerprint and per version of the script that makes it
    (code = that script's path): a rerun, or another mode on the same clip, does not measure or transcribe again."""
    version = hashlib.sha1(Path(code).read_bytes()).hexdigest()[:8]
    path = CACHE_DIR / f"{fingerprint(src)}-{name}-{version}.json"
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            pass
    out = fn()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}-{threading.get_ident()}.part")
    tmp.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    return out


# ── Request ──────────────────────────────────────────────────────────────

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".mp4": "video/mp4", ".mov": "video/quicktime"}


def post(url: str, headers: dict, body: dict, timeout: float, opener=None, gate=None):
    """POST JSON → (response headers, JSON body). 429 / 5xx / network errors are retried after RETRY_DELAYS;
    a timeout is not (a slow request would only repeat). gate: a semaphore held while the request is in flight."""
    data = json.dumps(body).encode("utf-8")
    opener = opener or urllib.request.build_opener()
    for attempt, delay in enumerate((*RETRY_DELAYS, None), 1):
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"Content-Type": "application/json", **headers})
        try:
            with gate or contextlib.nullcontext(), opener.open(req, timeout=timeout) as resp:  # the slot is free again while retrying
                raw = resp.read().decode("utf-8")
                return resp.headers, (json.loads(raw) if raw.strip() else {})
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
        except ValueError as e:
            err, transient = FootageError("PROVIDER_ERROR", f"Response is not JSON: {e}"), False
        if delay is None or not transient:
            raise err
        print(f"[genius-footage] {err} — retry {attempt}/{len(RETRY_DELAYS)} in {delay}s…", file=sys.stderr)
        time.sleep(delay)


def call(c: dict, files: list[str], prompt: str, timeout: float) -> str:
    """One request: local files (inline) before the prompt. A canned refusal is a PROVIDER_ERROR."""
    parts = [{"inline_data": {"mime_type": MIME.get(Path(f).suffix.lower(), "application/octet-stream"),
                              "data": base64.b64encode(Path(f).read_bytes()).decode("ascii")}} for f in files]
    root = re.sub(r"/(v1|v1beta/openai|openai)$", "", c["base_url"])
    proxy = next((os.environ[n] for n in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY",
                                          "all_proxy") if os.environ.get(n)), None)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {}))
    _, data = post(f"{root}/v1beta/models/{c['model']}:generateContent",
                   {"Authorization": f"Bearer {c['api_key']}", "x-goog-api-key": c["api_key"]},
                   {"contents": [{"role": "user", "parts": parts + [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 32768}}, timeout, opener, _gate)
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


def parse_json(text: str, open_ch: str, close_ch: str):
    a, b = text.find(open_ch), text.rfind(close_ch)
    try:
        return json.loads(text[a:b + 1]) if a != -1 and b > a else None
    except ValueError:
        return None


def ask(c: dict, jobs: list[tuple[list[str], str]], ids: list[list[str]] | None = None,
        failed: list | None = None, timeout: float = 300) -> list[list | None]:
    """One request per (files, prompt), all in flight at once under the global cap. Each answer is the objects
    of the JSON array the model returned, in input order; None = no answer.
    A request that failed, returned no array, or left out some of ids[k] (the "id" values job k must answer
    for) is asked once more, and the second answer's objects follow the first's (so the first one wins for
    an id answered twice). A request that failed both times leaves its error in `failed`."""
    def one(job) -> tuple[list | None, FootageError | None]:
        try:
            ans = parse_json(call(c, job[0], job[1], timeout), "[", "]")
        except FootageError as e:
            print(f"[genius-footage] request failed [{e.code}]: {e}", file=sys.stderr)
            return None, e
        return ([x for x in ans if isinstance(x, dict)] if isinstance(ans, list) else None), None

    def short(k: int, ans: list | None) -> bool:
        return ans is None or bool(ids and set(ids[k]) - {str(x.get("id")) for x in ans})

    with ThreadPoolExecutor(_limit) as ex:
        first = list(ex.map(tagged(one), jobs))
        answers = [a for a, _ in first]
        again = [k for k, a in enumerate(answers) if short(k, a)]
        if again:
            print(f"[genius-footage] {len(again)} answer(s) missing or short, asking once more…", file=sys.stderr)
        for k, (a, err) in zip(again, list(ex.map(tagged(one), [jobs[k] for k in again]))):
            if a is not None:
                answers[k] = (answers[k] or []) + a
            elif answers[k] is None and failed is not None and (err or first[k][1]):
                failed.append(err or first[k][1])
    return answers


# ── Whole-clip proxy ─────────────────────────────────────────────────────

PROXY_VF = (f"fps={PROXY_FPS},scale='if(gte(iw,ih),min({PROXY_SCALE},iw),-2)':"
            f"'if(gte(iw,ih),-2,min({PROXY_SCALE},ih))'")
PROXY_ENCODERS = (["h264_videotoolbox"] if sys.platform == "darwin" else []) + ["libx264"]


def proxy_file(src: str, duration: float) -> tuple[Path, int]:
    """(where the whole-clip proxy of src is cached, its video bitrate in kbps)."""
    kbps = int(max(50, min(1500, BUDGET_BYTES * 8 / 1000 * 0.92 / max(duration, 1) - AUDIO_KBPS)))
    return CACHE_DIR / f"{fingerprint(src)}-{kbps}k.mp4", kbps


def proxy_output(kbps: int, enc: str, path: Path) -> list[str]:
    return ["-c:v", enc, "-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.25)}k", "-bufsize", f"{kbps * 2}k",
            "-c:a", "aac", "-b:a", f"{AUDIO_KBPS}k", "-ac", "1", "-movflags", "+faststart", str(path)]


def video_proxy(src: str, duration: float) -> str:
    """2 fps, ≤1280 px, H.264 + mono AAC, sized to fit one request; cached by file fingerprint."""
    out, kbps = proxy_file(src, duration)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if out.is_file() and out.stat().st_size:
        return str(out)
    if not shutil.which("ffmpeg"):
        raise FootageError("DEPENDENCY_MISSING", "ffmpeg not found on PATH")
    tmp = out.with_suffix(".part.mp4")
    for enc in PROXY_ENCODERS:
        p = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-vf", PROXY_VF,
                            *proxy_output(kbps, enc, tmp)], capture_output=True, text=True)
        if p.returncode == 0 and tmp.is_file() and tmp.stat().st_size:
            tmp.replace(out)
            print(f"[genius-footage] whole-clip proxy via {enc}: {out.stat().st_size / 1048576:.1f}MB → {out}",
                  file=sys.stderr)
            return str(out)
        tmp.unlink(missing_ok=True)
    raise FootageError("UNSUPPORTED_FORMAT", f"cannot encode a proxy of {src}: {p.stderr.strip()[-300:]}")
