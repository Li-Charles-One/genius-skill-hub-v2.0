#!/usr/bin/env python3
"""
genius-image generation script.
Single image, batch (concurrent), or async polling via GRSai API.

Usage:
  python scripts/generate.py "a cat in space"                           # single, defaults: gpt-image-2, 16:9
  python scripts/generate.py "prompt" --model nano-banana-2 --size 2K   # nano model
  python scripts/generate.py "prompt" --aspect 1:1 --out ./img          # custom aspect + output dir
  python scripts/generate.py --batch prompts.txt --concurrency 3        # batch from file
  python scripts/generate.py "prompt" --async                           # async + polling
  python scripts/generate.py "prompt" --ref https://example.com/img.png # with reference image

Env:
  GRSAI_API_KEY    API key (required)
  GRSAI_BASE_URL   Base URL (default: https://grsaiapi.com)
"""

import argparse
import base64
import concurrent.futures
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

MODELS = ["gpt-image-2", "gpt-image-2-vip", "nano-banana-2", "nano-banana-pro"]
NANO_MODELS = {"nano-banana-2", "nano-banana-pro"}
VIP_MODELS = {"gpt-image-2-vip"}


def load_api_key() -> str:
    """Resolve GRSAI_API_KEY from env or ~/.codex/.env."""
    key = os.environ.get("GRSAI_API_KEY", "").strip()
    if key:
        return key
    env_file = Path.home() / ".codex" / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GRSAI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    return key
    raise SystemExit("GRSAI_API_KEY not found. Set env var or add to ~/.codex/.env")


def image_to_base64(path: str) -> str:
    """Convert local image file to base64 data URI."""
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Reference image not found: {path}")
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode()
    ext = p.suffix.lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/png")
    return f"data:{mime};base64,{b64}"


def build_body(model: str, prompt: str, aspect_ratio: str, image_size: str,
               images: list[str], reply_type: str) -> dict:
    """Build request body, omitting imageSize for gpt models."""
    body: dict = {
        "model": model,
        "prompt": prompt,
        "images": images or [],
        "aspectRatio": aspect_ratio,
        "replyType": reply_type,
    }
    if model in NANO_MODELS and image_size:
        body["imageSize"] = image_size
    return body


class GenerateError(Exception):
    def __init__(self, status: str, error: str = ""):
        self.status = status
        self.error = error
        super().__init__(f"{status}: {error}" if error else status)


def generate_one(model: str, prompt: str, aspect_ratio: str, image_size: str,
                 images: list[str], base_url: str, key: str, timeout: int = 180,
                 reply_type: str = "json") -> dict:
    """Send one generate request, return parsed JSON response. Raises GenerateError on failure."""
    body = json.dumps(build_body(model, prompt, aspect_ratio, image_size, images, reply_type)).encode()
    req = urllib.request.Request(
        f"{base_url}/v1/api/generate",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.request.HTTPError as e:
        try:
            data = json.loads(e.read())
        except Exception:
            raise GenerateError("failed", f"HTTP {e.code}") from e
    except OSError as e:
        raise GenerateError("failed", str(e)) from e

    status = data.get("status", "")
    if status == "succeeded":
        return data
    if status == "running":
        return data  # async initial response
    raise GenerateError(status, data.get("error", ""))


def poll_async(task_id: str, base_url: str, key: str, max_wait: int = 300, interval: int = 5) -> dict:
    """Poll async result until success/failure/timeout."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        req = urllib.request.Request(
            f"{base_url}/v1/api/result?id={task_id}",
            headers={"Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        status = data.get("status", "")
        progress = data.get("progress", 0)
        if status == "succeeded":
            return data
        if status in ("failed", "violation"):
            raise GenerateError(status, data.get("error", ""))
        sys.stderr.write(f"  progress: {progress}%\r")
        sys.stderr.flush()
        time.sleep(interval)
    raise GenerateError("timeout", f"polling exceeded {max_wait}s for task {task_id}")


def download(url: str, out_path: str) -> int:
    """Download image to path, return file size in bytes."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    urllib.request.urlretrieve(url, out_path)
    return os.path.getsize(out_path)


def slugify(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:8]


def run_single(args, key: str, base_url: str):
    images = []
    if args.ref:
        for r in args.ref:
            if r.startswith("http://") or r.startswith("https://"):
                images.append(r)
            else:
                images.append(image_to_base64(r))

    t0 = time.time()
    sys.stderr.write(f"{args.model} | {args.aspect} | 生成中，预计 30-60 秒...\n")
    sys.stderr.flush()

    if args.async_mode:
        data = generate_one(args.model, args.prompt, args.aspect, args.image_size,
                            images, base_url, key, reply_type="async")
        task_id = data["id"]
        print(f"task_id: {task_id}")
        data = poll_async(task_id, base_url, key)
    else:
        data = generate_one(args.model, args.prompt, args.aspect, args.image_size,
                            images, base_url, key)

    elapsed = round(time.time() - t0, 1)
    url = data["results"][0]["url"]
    out_dir = args.out or os.path.join(os.getcwd(), "outputs", "genius-image")
    fname = f"genius-{slugify(args.prompt)}.png"
    fpath = os.path.join(out_dir, fname)
    size = download(url, fpath)

    if args.json:
        print(json.dumps({"ok": True, "time": elapsed, "path": fpath, "size": size, "url": url},
                         ensure_ascii=False))
    else:
        print(f"\n{elapsed}s | {size//1024}KB")
        print(f"![{args.prompt[:40]}]({fpath})")
        print(f"<!-- raw: {url} -->")


def run_batch(args, key: str, base_url: str):
    prompts: list[str] = []
    if args.batch:
        for line in Path(args.batch).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                prompts.append(line)
    if args.prompt:
        prompts.extend(args.prompt)
    if not prompts:
        raise SystemExit("No prompts provided. Use --batch FILE or positional prompt arguments.")

    print(f"批量生成 {len(prompts)} 张 | {args.model} | {args.aspect} | {args.concurrency} 并发")
    print(f"预计 {len(prompts) * 50 // args.concurrency}s 左右...")

    out_dir = args.out or os.path.join(os.getcwd(), "outputs", "genius-image")
    results: list[dict] = []
    t_start = time.time()

    def worker(idx: int, prompt: str):
        t0 = time.time()
        try:
            data = generate_one(args.model, prompt, args.aspect, args.image_size, [], base_url, key)
            url = data["results"][0]["url"]
            fname = f"genius-{idx+1:02d}-{slugify(prompt)}.png"
            fpath = os.path.join(out_dir, fname)
            size = download(url, fpath)
            return {"idx": idx, "ok": True, "time": round(time.time() - t0, 1),
                    "path": fpath, "size": size, "url": url, "prompt": prompt}
        except Exception as e:
            return {"idx": idx, "ok": False, "time": round(time.time() - t0, 1),
                    "error": str(e), "prompt": prompt}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        tasks = [ex.submit(worker, i, p) for i, p in enumerate(prompts)]
        for f in concurrent.futures.as_completed(tasks):
            results.append(f.result())

    total = round(time.time() - t_start, 1)
    results.sort(key=lambda r: r["idx"])

    if args.json:
        print(json.dumps({"total_time": total, "results": results}, ensure_ascii=False))
    else:
        print(f"\n总耗时: {total}s | 成功: {sum(1 for r in results if r['ok'])}/{len(results)}\n")
        for r in results:
            if r["ok"]:
                print(f"  ✅ #{r['idx']+1} | {r['time']}s | {r['size']//1024}KB")
                print(f"     ![{r['prompt'][:50]}]({r['path']})")
                print(f"     <!-- raw: {r['url']} -->")
            else:
                print(f"  ❌ #{r['idx']+1} | {r['time']}s | {r['error']}")


def main():
    parser = argparse.ArgumentParser(description="GRSai image generation")
    parser.add_argument("prompt", nargs="*", help="Prompt(s) — one per image (batch mode when multiple)")
    parser.add_argument("--batch", help="File with one prompt per line (# comments)")
    parser.add_argument("--model", default="gpt-image-2", choices=MODELS)
    parser.add_argument("--aspect", default="16:9", help="Aspect ratio (e.g. 16:9, 1:1) or pixel value (e.g. 1024x1024)")
    parser.add_argument("--image-size", dest="image_size", default="1K", choices=["1K", "2K", "4K"],
                        help="Resolution for nano-banana models (default: 1K)")
    parser.add_argument("--async", dest="async_mode", action="store_true",
                        help="Use async + polling (for long-running single tasks)")
    parser.add_argument("--ref", action="append", help="Reference image URL or local path (repeatable)")
    parser.add_argument("--concurrency", type=int, default=3, help="Batch concurrency (default: 3)")
    parser.add_argument("--out", help="Output directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    key = load_api_key()
    base_url = os.environ.get("GRSAI_BASE_URL", "https://grsaiapi.com").rstrip("/")

    # detect batch mode
    is_batch = bool(args.batch) or len(args.prompt) > 1
    if not is_batch and not args.prompt:
        parser.error("No prompt given")
    if is_batch and len(args.prompt) <= 1 and not args.batch:
        is_batch = False

    if is_batch:
        run_batch(args, key, base_url)
    else:
        run_single(args, key, base_url)


if __name__ == "__main__":
    main()
