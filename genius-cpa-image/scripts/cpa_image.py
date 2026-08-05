#!/usr/bin/env python3
"""Genius CPA Image — JP CPA via official Gemini generateContent.

Endpoint:
  POST {CPA_JP_BASE}/v1beta/models/{model}:generateContent

Default model: gemini-3.1-flash-image
Auth: CPA_JP_API_KEY (alias CPA_API_KEY)
Base: CPA_JP_BASE (default https://cpa-jp.charles-ai.space)

Native image controls (imageConfig):
  aspectRatio, imageSize (0.5K/1K/2K/4K)
Also: reference images, google_search tool.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests

API_KEY = os.getenv("CPA_JP_API_KEY") or os.getenv("CPA_API_KEY")
BASE = (os.getenv("CPA_JP_BASE") or "https://cpa-jp.charles-ai.space").rstrip("/")

HERE = Path(__file__).resolve().parent
OUT_DIR = Path.cwd() / "genius_output"
LOG_DIR = OUT_DIR / "Logs"
LOG_FILE = LOG_DIR / "cpa_image_log.jsonl"
LOG_MAX_SIZE = 10 * 1024 * 1024
LOG_ARCHIVE_DAYS = 7

# Official Gemini 3.1 Flash Image ratios (incl. extreme)
ASPECTS = {
    "1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4",
    "9:16", "16:9", "21:9", "1:4", "4:1", "1:8", "8:1",
}
RESOLUTIONS = {"0.5K", "1K", "2K", "4K"}

MODELS = {
    "gemini-3.1-flash-image": {
        "id": "gemini-3.1-flash-image",
        "max_ref": 14,
        "max_prompt": 20000,
        "default_aspect": "1:1",
        "default_resolution": "1K",
        "aspects": ASPECTS,
        "resolutions": RESOLUTIONS,
    },
}

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


def require_api_key():
    if not API_KEY:
        raise RuntimeError("CPA_JP_API_KEY (or CPA_API_KEY) not set")
    return API_KEY


def headers():
    return {
        "Authorization": f"Bearer {require_api_key()}",
        "Content-Type": "application/json",
    }


def request_with_retry(method, url, retries=MAX_RETRIES, **kwargs):
    last = None
    for i in range(retries):
        try:
            r = requests.request(method, url, **kwargs)
            if r.status_code == 429:
                time.sleep(2 ** i + 1)
                continue
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(2 ** i)
    raise RuntimeError(f"request failed {retries} times: {last}")


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


def write_log(entry):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > LOG_MAX_SIZE:
        archive = LOG_DIR / f"cpa_image_log_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
        LOG_FILE.rename(archive)
        log_print(f"  [log] rotated: {archive.name}")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def clean_old_logs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - LOG_ARCHIVE_DAYS * 86400
    for f in LOG_DIR.glob("cpa_image_log_*.jsonl"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            log_print(f"  [log] removed archive: {f.name}")


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


def resolve_ref_parts(refs):
    """Return Gemini parts for reference images (inlineData or file URI text fallback)."""
    parts = []
    for ref in refs or []:
        if not isinstance(ref, str):
            raise RuntimeError(f"ref must be string, got {type(ref).__name__}")
        low = ref.lower()
        if low.startswith("data:"):
            m = re.match(r"data:([^;,]+);base64,(.+)$", ref, re.S)
            if not m:
                raise RuntimeError("invalid data URL ref")
            mime, b64 = m.group(1), re.sub(r"\s+", "", m.group(2))
            parts.append({"inlineData": {"mimeType": mime, "data": b64}})
            continue
        if low.startswith(("http://", "https://")):
            # Native generateContent prefers inline/file; fetch remote URL to inline.
            r = request_with_retry("GET", ref, timeout=60)
            if r.status_code != 200:
                raise RuntimeError(f"failed to fetch ref URL HTTP {r.status_code}: {ref}")
            ctype = (r.headers.get("Content-Type") or "image/png").split(";")[0].strip()
            if not ctype.startswith("image/"):
                # still try
                ctype = "image/png"
            b64 = base64.b64encode(r.content).decode("ascii")
            parts.append({"inlineData": {"mimeType": ctype, "data": b64}})
            continue
        p = Path(ref).expanduser()
        if not p.is_file():
            raise RuntimeError(f"ref is neither URL nor local file: {ref}")
        mime, b64 = load_local_image_b64(p)
        parts.append({"inlineData": {"mimeType": mime, "data": b64}})
    return parts


def validate_task(task):
    model = task.get("model") or "gemini-3.1-flash-image"
    if model not in MODELS:
        raise RuntimeError(f"unknown model: {model}; available: {sorted(MODELS)}")
    cfg = MODELS[model]
    task["model"] = model

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

    if not task.get("aspect"):
        task["aspect"] = cfg["default_aspect"]
    if task["aspect"] not in cfg["aspects"]:
        raise RuntimeError(
            f"{model} does not support aspect {task['aspect']}; allowed: {sorted(cfg['aspects'])}"
        )

    if not task.get("resolution"):
        task["resolution"] = cfg["default_resolution"]
    # normalize case: 1k -> 1K
    res = str(task["resolution"]).strip()
    res_map = {x.lower(): x for x in cfg["resolutions"]}
    if res in cfg["resolutions"]:
        task["resolution"] = res
    elif res.lower() in res_map:
        task["resolution"] = res_map[res.lower()]
    else:
        raise RuntimeError(
            f"{model} does not support resolution {task['resolution']}; allowed: {sorted(cfg['resolutions'])}"
        )

    refs = task.get("ref") or []
    if refs and len(refs) > cfg["max_ref"]:
        raise RuntimeError(f"{model} allows at most {cfg['max_ref']} refs")

    # not Gemini imageConfig fields
    if task.get("quality") not in (None, False, ""):
        raise RuntimeError(f"{model} does not support quality (gpt-image only)")
    if task.get("output_format") not in (None, False, ""):
        raise RuntimeError(
            f"{model} does not support output_format; server returns image bytes (often jpeg)"
        )

    task["google_search"] = bool(task.get("google_search"))
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
        # some proxies wrap differently
        raise RuntimeError(f"no candidates in response: keys={list(resp.keys())}")

    images = []  # list of (mime, bytes) or data-url strings
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
            # rare: fileData / url
            fd = part.get("fileData") or part.get("file_data")
            if isinstance(fd, dict) and fd.get("fileUri"):
                images.append({"url": fd["fileUri"], "mime": fd.get("mimeType") or "image/jpeg"})

    if not images:
        raise RuntimeError(
            f"no image parts in response; texts={texts[:1]!r} finish={((candidates[0] or {}).get('finishReason'))}"
        )
    return images, texts


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


def generate_content_url(model_id):
    # Official Gemini path proxied by CPA
    return f"{BASE}/v1beta/models/{model_id}:generateContent"


def submit(task):
    require_api_key()
    cfg = MODELS[task["model"]]
    body = build_generate_content_body(task)
    url = generate_content_url(cfg["id"])
    r = request_with_retry("POST", url, headers=headers(), json=body, timeout=TIMEOUT_SUBMIT)
    try:
        d = r.json()
    except Exception:
        raise RuntimeError(f"non-JSON HTTP {r.status_code}: {r.text[:300]}")
    if r.status_code >= 400:
        err = d.get("error") if isinstance(d, dict) else d
        if isinstance(err, dict):
            raise RuntimeError(f"HTTP {r.status_code}: {err.get('message') or err}")
        raise RuntimeError(f"HTTP {r.status_code}: {err or d}")
    images, texts = extract_images_from_generate_content(d)
    # use response id if any, else timestamp
    tid = d.get("responseId") or d.get("id") or f"cpa-{int(time.time())}"
    return {
        "task_id": tid,
        "images": images,
        "texts": texts,
        "usage": d.get("usageMetadata") or d.get("usage"),
        "model": cfg["id"],
        "raw_model_version": d.get("modelVersion"),
    }


def list_models():
    """Prefer OpenAI-compatible /v1/models on CPA; fall back to configured keys."""
    require_api_key()
    try:
        r = request_with_retry("GET", f"{BASE}/v1/models", headers=headers(), timeout=TIMEOUT_MODELS)
        if r.status_code < 400:
            data = r.json().get("data") or []
            return [m.get("id") for m in data if isinstance(m, dict) and m.get("id")]
    except Exception:
        pass
    return list(MODELS.keys())


def run_preflight():
    log_print(">> Preflight (CPA JP official generateContent)")
    log_print(f"   script  : {Path(__file__).resolve()}")
    log_print(f"   base    : {BASE}")
    log_print(f"   endpoint: /v1beta/models/<model>:generateContent")
    log_print(f"   out     : {OUT_DIR}")
    require_api_key()
    log_print("   api key : PASS")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    probe = OUT_DIR / ".cpa_preflight.tmp"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    log_print("   workdir : PASS")
    ids = list_models()
    hit = "gemini-3.1-flash-image" in ids
    log_print(f"   models  : {len(ids)} listed; gemini-3.1-flash-image={'yes' if hit else 'NO'}")
    if not hit:
        log_print("   warn    : model not in /v1/models list; generateContent may still work")
    # lightweight endpoint existence check with tiny request is expensive; skip generation
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
            log_print(f"  [retryable] {e}")
    if result is None:
        raise RuntimeError(last_err or "generation failed")

    img = result["images"][0]
    if "data" in img:
        ext = guess_ext(img.get("mime") or img["data"])
    else:
        ext = guess_ext(img.get("mime"), "jpg")
    base = make_output_basename(task["model"], task["prompt"], name=name or task.get("name"))
    dest = find_next_filename(base, ext, OUT_DIR)
    size = save_image_obj(img, dest)
    dur = time.time() - t0
    return {
        "task_id": result["task_id"],
        "path": dest,
        "size": size,
        "duration_s": dur,
        "model": task["model"],
        "prompt": task["prompt"],
        "aspect": task.get("aspect"),
        "resolution": task.get("resolution"),
        "usage": result.get("usage"),
        "n_images": len(result["images"]),
    }


def run_single(args):
    task = {
        "prompt": args.prompt,
        "model": args.model,
        "aspect": args.aspect,
        "resolution": args.resolution,
        "ref": args.ref,
        "google_search": args.google_search,
    }
    log_print(f">> model: {args.model}  api: generateContent  base: {BASE}")
    log_print(f">> prompt: {args.prompt}")
    if args.aspect:
        log_print(f">> aspect: {args.aspect}")
    if args.resolution:
        log_print(f">> resolution: {args.resolution}")
    if args.ref:
        log_print(f">> refs: {len(args.ref)}")
    if args.google_search:
        log_print(">> google_search: on")
    try:
        info = generate_one(task, name=args.name)
    except Exception as e:
        log_print(f">> failed: {e}", file=sys.stderr)
        write_log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "model": args.model, "prompt": args.prompt,
            "status": "failed", "error": str(e), "provider": "cpa-jp",
            "api": "generateContent",
        })
        emit_result(status="failed", model=args.model, provider="cpa-jp", error=str(e))
        sys.exit(1)

    log_print(">> done")
    log_print(f"   model      : {info['model']}")
    log_print(f"   aspect     : {info['aspect']}")
    log_print(f"   resolution : {info['resolution']}")
    log_print(f"   task_id    : {info['task_id']}")
    log_print(f"   duration   : {info['duration_s']:.1f}s")
    log_print(f"   size       : {info['size']/1024:.1f} KB")
    log_print(f"   path       : {info['path']}")
    if info.get("usage"):
        log_print(f"   usage      : {info['usage']}")
    emit_result(
        status="success", model=info["model"], provider="cpa-jp",
        api="generateContent",
        task_id=info["task_id"], path=info["path"],
        aspect=info["aspect"], resolution=info["resolution"],
        duration_s=round(info["duration_s"], 1),
        size_kb=round(info["size"] / 1024, 1),
    )
    write_log({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "task_id": info["task_id"], "model": info["model"], "provider": "cpa-jp",
        "api": "generateContent",
        "prompt": info["prompt"], "aspect": info["aspect"], "resolution": info["resolution"],
        "duration_s": round(info["duration_s"], 1),
        "file_size_kb": round(info["size"] / 1024, 1),
        "file_path": str(info["path"]), "usage": info.get("usage"),
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
            t["model"] = "gemini-3.1-flash-image"
        out.append(validate_task(t))
    return out


def run_batch(args):
    tasks = load_batch(args.batch)
    n = len(tasks)
    log_print(f">> batch: {n} tasks, concurrent={args.concurrent}, api=generateContent, base={BASE}")
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
                    f"({info['aspect']}/{info['resolution']}, {info['duration_s']:.1f}s)"
                )
                emit_result(
                    status="success", model=info["model"], provider="cpa-jp",
                    api="generateContent",
                    task_id=info["task_id"], path=info["path"],
                    aspect=info["aspect"], resolution=info["resolution"],
                    duration_s=round(info["duration_s"], 1),
                    size_kb=round(info["size"] / 1024, 1),
                )
                write_log({
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "task_id": info["task_id"], "model": info["model"], "provider": "cpa-jp",
                    "api": "generateContent",
                    "prompt": info["prompt"], "aspect": info["aspect"],
                    "resolution": info["resolution"],
                    "duration_s": round(info["duration_s"], 1),
                    "file_size_kb": round(info["size"] / 1024, 1),
                    "file_path": str(info["path"]), "status": "success",
                })
            except Exception as e:
                fail += 1
                log_print(f"  FAIL: {e}")
                emit_result(status="failed", provider="cpa-jp", error=str(e))
                write_log({
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "provider": "cpa-jp", "api": "generateContent",
                    "status": "failed", "error": str(e),
                })

    total = time.time() - t0
    log_print(f">> batch done ok={ok} fail={fail} duration={total:.1f}s")
    emit_result(status="batch_done", ok=ok, fail=fail, duration_s=round(total, 1))
    if fail and not ok:
        sys.exit(1)


def main():
    configure_stdio()
    ap = argparse.ArgumentParser(
        description="Genius CPA Image — official Gemini generateContent via JP CPA"
    )
    ap.add_argument("prompt", nargs="?", help="image prompt")
    ap.add_argument("--batch", help="batch JSON path")
    ap.add_argument("--concurrent", type=int, default=DEFAULT_CONCURRENT)
    ap.add_argument("--model", default="gemini-3.1-flash-image", choices=list(MODELS.keys()))
    ap.add_argument("--aspect", default=None, choices=sorted(ASPECTS),
                    help="imageConfig.aspectRatio")
    ap.add_argument("--resolution", default=None, choices=sorted(RESOLUTIONS),
                    help="imageConfig.imageSize (0.5K/1K/2K/4K)")
    ap.add_argument("--ref", nargs="+", help="reference image URL(s) or local path(s)")
    ap.add_argument("--google-search", dest="google_search", action="store_true",
                    help="enable tools.google_search grounding")
    ap.add_argument("--name", default=None, help="output basename without extension")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--no-gen", action="store_true", help="required with --preflight")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--out", default=None, help="output directory (default ./genius_output)")
    args = ap.parse_args()

    global OUT_DIR, LOG_DIR, LOG_FILE
    if args.out:
        OUT_DIR = Path(args.out)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR = OUT_DIR / "Logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE = LOG_DIR / "cpa_image_log.jsonl"

    try:
        if args.preflight:
            if not args.no_gen:
                raise RuntimeError("--preflight requires --no-gen")
            run_preflight()
            return
        if args.list_models:
            for mid in list_models():
                log_print(mid)
            return
        clean_old_logs()
        if args.batch:
            run_batch(args)
        elif args.prompt:
            run_single(args)
        else:
            ap.error("need prompt, --batch, --preflight, or --list-models")
    except RuntimeError as e:
        sys.exit(f"ERROR: {e}")


if __name__ == "__main__":
    main()
