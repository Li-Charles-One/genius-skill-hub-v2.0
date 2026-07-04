import os, sys, time, json, re, argparse, subprocess, threading, requests, base64, mimetypes, shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue, Empty

API_KEY = os.getenv("CRUN_API_KEY")

BASE = "https://api.crun.ai"
HERE = Path(__file__).parent
SKILL_ROOT = HERE.parent
CLOUDFLARED_CANDIDATES = [HERE / "bin" / "cloudflared.exe", SKILL_ROOT / "bin" / "cloudflared.exe", Path("bin/cloudflared.exe")]
CLOUDFLARED = next((str(c) for c in CLOUDFLARED_CANDIDATES if c.exists()), None) or shutil.which("cloudflared")
OUT_DIR = Path.cwd() / "genius_output"
LOG_DIR = OUT_DIR / "Logs"
LOG_FILE = LOG_DIR / "genius_log.jsonl"
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_ARCHIVE_DAYS = 7

GPT_IMAGE_2_ASPECTS = {"1:1","2:3","3:2","5:4","4:5","9:16","16:9","4:3","3:4","21:9","auto"}
PREMIUM_ASPECTS = {"1:1","2:3","3:2","5:4","4:5","9:16","16:9","4:3","3:4"}
NANO_ASPECTS = {"1:1","2:3","3:2","3:4","4:3","4:5","5:4","9:16","16:9","1:4","4:1","1:8","8:1","21:9","auto"}

MODELS = {
    "gpt-image-2":           {"id": "openai/gpt-image-2",           "max_ref": 16, "max_prompt": 5000,  "extra": set(),                              "resolutions": {"1K","2K","4K"}, "aspects": GPT_IMAGE_2_ASPECTS, "default_aspect": "auto", "default_resolution": "1K"},
    "gpt-image-2-premium":   {"id": "openai/gpt-image-2-premium",   "max_ref": 14, "max_prompt": 10000, "extra": {"quality"},                       "resolutions": {"1K","2K","3K"}, "aspects": PREMIUM_ASPECTS,     "default_aspect": "1:1",  "default_resolution": "1K", "default_quality": "medium"},
    "nano-banana-2":         {"id": "google/nano-banana-2",         "max_ref": 14, "max_prompt": 20000, "extra": {"google_search", "output_format"}, "resolutions": {"1K","2K","4K"}, "aspects": NANO_ASPECTS,        "default_aspect": "1:1",  "default_resolution": "1K"},
    "nano-banana-pro":       {"id": "google/nano-banana-pro",       "max_ref": 8,  "max_prompt": None,  "extra": {"output_format"},                 "resolutions": {"1K","2K","4K"}, "aspects": NANO_ASPECTS,        "default_aspect": "1:1",  "default_resolution": "1K"},
}

ASPECTS = sorted(set().union(*(cfg["aspects"] for cfg in MODELS.values())))

WEBHOOK_PORT = 8765
TUNNEL_START_TIMEOUT = 60
TIMEOUT_SUBMIT = 30
TIMEOUT_DOWNLOAD = 180
TIMEOUT_CALLBACK = 300
MAX_RETRIES = 3
DEFAULT_CONCURRENT = 5
MAX_TASK_RETRIES = 3
RETRY_DELAY = 5

ERROR_MAP = {
    401: "API Key 无效", 402: "积分不足", 403: "API Key 已禁用", 404: "任务不存在",
    422: "参数错误", 429: "限速", 455: "维护中",
    500: "服务器错误", 501: "生成失败", 505: "功能禁用",
}

results = {}
results_lock = threading.Lock()
results_event = threading.Event()

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            tid = data.get("task_id") or data.get("data", {}).get("task_id")
            if not tid:
                raise ValueError("missing task_id in callback payload")
            with results_lock:
                results[tid] = data
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            st = data.get("status", "unknown")
            print(f"\n  [webhook] {tid[:8]}... → {st}")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            print(f"\n  [webhook] 解析失败: {e}")
    def log_message(self, *args): pass

def start_webhook(port):
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server

def start_tunnel(port):
    if not CLOUDFLARED:
        searched = [str(c) for c in CLOUDFLARED_CANDIDATES] + ["PATH: cloudflared"]
        raise RuntimeError(f"cloudflared not found. Searched: {searched}")
    proc = subprocess.Popen(
        [CLOUDFLARED, "tunnel", "--url", f"http://localhost:{port}", "--no-autoupdate"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    lines = Queue()
    def collect_output():
        try:
            for line in proc.stdout:
                lines.put(line)
        except Exception:
            pass
    threading.Thread(target=collect_output, daemon=True).start()
    t0 = time.time()
    while time.time() - t0 < TUNNEL_START_TIMEOUT:
        if proc.poll() is not None:
            break
        try:
            line = lines.get(timeout=0.5)
        except Empty:
            continue
        m = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
        if m:
            print(f"  [tunnel] 公网 URL: {m.group(0)}")
            return m.group(0), proc
    proc.terminate()
    raise RuntimeError(f"cloudflared {TUNNEL_START_TIMEOUT} 秒内未拿到公网 URL")

def request_with_retry(method, url, retries=MAX_RETRIES, **kwargs):
    last = None
    for i in range(retries):
        try:
            r = requests.request(method, url, **kwargs)
            if r.status_code == 429:
                w = 2 ** i + 1; time.sleep(w); continue
            return r
        except requests.RequestException as e:
            last = e; time.sleep(2 ** i)
    raise RuntimeError(f"请求失败 {retries} 次: {last}")

def get_balance():
    if not API_KEY: raise RuntimeError("CRUN_API_KEY not set")
    r = request_with_retry("GET", f"{BASE}/api/v1/client/account/balance",
                           headers={"X-API-KEY": API_KEY}, timeout=15)
    d = r.json()
    if d.get("code") != 200: raise RuntimeError(f"balance fail: {d}")
    return d["data"]["balance"]

def get_task_info(tid):
    if not API_KEY: raise RuntimeError("CRUN_API_KEY not set")
    r = request_with_retry("GET", f"{BASE}/api/v1/client/job/TaskInfo",
                           headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"},
                           params={"task_id": tid}, timeout=15)
    d = r.json()
    if d.get("code") != 200: raise RuntimeError(f"task info fail [{d.get('code')}]: {ERROR_MAP.get(d.get('code'), d)}")
    return d.get("data")

def validate_task(task):
    if task["model"] not in MODELS: raise RuntimeError(f"未知模型: {task['model']}")
    cfg = MODELS[task["model"]]
    prompt = task.get("prompt", "")
    if not prompt: raise RuntimeError("任务缺少 prompt")
    max_prompt = cfg.get("max_prompt")
    if max_prompt and len(prompt) > max_prompt:
        raise RuntimeError(f"{task['model']} prompt 最多 {max_prompt} 字符")
    if "aspect" not in task and "aspect_ratio" in task:
        task["aspect"] = task["aspect_ratio"]
    if "ref" not in task and "img_urls" in task:
        task["ref"] = task["img_urls"]
    if not task.get("aspect"):
        task["aspect"] = cfg["default_aspect"]
    if not task.get("resolution"):
        task["resolution"] = cfg["default_resolution"]
    if "quality" in cfg["extra"]:
        if not task.get("quality"):
            task["quality"] = cfg.get("default_quality", "medium")
    if task["aspect"] not in cfg["aspects"]:
        raise RuntimeError(f"{task['model']} 不支持宽高比 {task['aspect']}")
    if task["resolution"] not in cfg["resolutions"]:
        raise RuntimeError(f"{task['model']} 不支持分辨率 {task['resolution']}")
    if task.get("quality") and "quality" not in cfg["extra"]:
        raise RuntimeError(f"{task['model']} 不支持 quality 参数")
    if task.get("google_search") and "google_search" not in cfg["extra"]:
        raise RuntimeError(f"{task['model']} 不支持 google_search 参数")
    if task.get("output_format") not in (None, "png") and "output_format" not in cfg["extra"]:
        raise RuntimeError(f"{task['model']} 不支持 output_format 参数")
    if task["model"] == "gpt-image-2" and task["resolution"] == "4K" and task["aspect"] == "1:1":
        raise RuntimeError("gpt-image-2 的 4K 分辨率不支持 1:1 宽高比")
    if task["model"] == "gpt-image-2" and task["aspect"] == "auto" and task["resolution"] != "1K":
        raise RuntimeError("gpt-image-2 的 auto 宽高比仅支持 1K 分辨率")
    if task.get("ref") and len(task["ref"]) > cfg["max_ref"]:
        raise RuntimeError(f"{task['model']} 最多 {cfg['max_ref']} 张参考图")
    return task

def is_generation_retryable(res):
    result = res.get("result") if isinstance(res, dict) else None
    return isinstance(result, dict) and result.get("code") == 501

def wait_for_completion(tid, deadline):
    while time.time() < deadline:
        with results_lock:
            if tid in results:
                return results[tid].get("data", results[tid])
        time.sleep(1)
    print(f"  [warn] 未收到回调，使用 TaskInfo 单次恢复: {tid[:8]}...")
    info = get_task_info(tid)
    if info and info.get("status") in {"success", "failed"}:
        with results_lock:
            results[tid] = {"data": info}
        return info
    status = info.get("status") if isinstance(info, dict) else "unknown"
    raise TimeoutError(f"回调超时 {TIMEOUT_CALLBACK}s，TaskInfo 状态: {status}")

def resolve_refs(refs):
    """把参考图列表里的每一项归一化成 API 能收的格式：
    - http:// 或 https:// URL → 原样保留
    - data:image base64 → 原样保留
    - 其余按本地文件路径处理 → 读出来编码成 data:image/<mime>;base64,<...>
    缺失的本地文件直接报错，避免把无效字符串丢给服务端拿 502。
    """
    resolved = []
    for ref in refs:
        if not isinstance(ref, str):
            raise RuntimeError(f"参考图必须是字符串（URL 或本地路径），实际是 {type(ref).__name__}")
        low = ref.lower()
        if low.startswith(("http://", "https://", "data:")):
            resolved.append(ref)
            continue
        # 当作本地文件
        p = Path(ref).expanduser()
        if not p.is_file():
            raise RuntimeError(f"参考图不是 http(s) URL 也找不到本地文件：{ref}")
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        resolved.append(f"data:{mime};base64,{b64}")
    return resolved

def build_payload(task, callback_url):
    task = validate_task(task)
    cfg = MODELS[task["model"]]
    inp = {"prompt": task["prompt"], "aspect_ratio": task["aspect"], "resolution": task["resolution"]}
    if task.get("ref"):
        inp["img_urls"] = resolve_refs(task["ref"])
    if "google_search" in cfg["extra"] and task.get("google_search"):
        inp["google_search"] = True
    if "output_format" in cfg["extra"] and task.get("output_format", "png") != "png":
        inp["output_format"] = task["output_format"]
    if "quality" in cfg["extra"]:
        inp["quality"] = task.get("quality", cfg.get("default_quality", "medium"))
    return {"model": cfg["id"], "callback_url": callback_url, "input": inp}

def submit(payload):
    if not API_KEY: raise RuntimeError("CRUN_API_KEY not set")
    r = request_with_retry("POST", f"{BASE}/api/v1/client/job/CreateTask",
                           headers={"X-API-KEY": API_KEY, "Content-Type": "application/json"},
                           json=payload, timeout=TIMEOUT_SUBMIT)
    d = r.json()
    if d.get("code") != 200:
        raise RuntimeError(f"submit fail [{d.get('code')}]: {ERROR_MAP.get(d.get('code'), d)}")
    return d["data"]["task_id"]

def extract_image_url(res):
    nested = res.get("result", {}) if isinstance(res.get("result"), dict) else {}
    urls = nested.get("media_urls") or res.get("media_urls") or []
    if isinstance(urls, str): urls = [urls]
    if not urls:
        for v in res.values():
            if isinstance(v, str) and v.startswith("http"): return v
    if not urls: raise RuntimeError(f"未找到图片 URL: {res}")
    return urls[0]

def extract_media_urls(res):
    nested = res.get("result", {}) if isinstance(res.get("result"), dict) else {}
    urls = nested.get("media_urls") or res.get("media_urls") or []
    if isinstance(urls, str):
        return [urls]
    return list(urls) if isinstance(urls, list) else []

def download(url, dest):
    r = request_with_retry("GET", url, timeout=TIMEOUT_DOWNLOAD)
    if r.status_code != 200:
        raise RuntimeError(f"下载失败 HTTP {r.status_code}")
    content_type = r.headers.get("Content-Type", "")
    if content_type and not content_type.startswith("image/"):
        raise RuntimeError(f"下载内容不是图片: {content_type}")
    dest.write_bytes(r.content)
    return len(r.content)

def find_next_filename(base, ext, out_dir):
    i = 1
    while True:
        dest = out_dir / f"{base}_{i}.{ext}"
        if not dest.exists(): return dest
        i += 1

def write_log(entry):
    LOG_DIR.mkdir(exist_ok=True)
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > LOG_MAX_SIZE:
        archive = LOG_DIR / f"genius_log_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
        LOG_FILE.rename(archive)
        print(f"  [log] 日志已轮转: {archive.name}")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def clean_old_logs():
    import time as _t
    LOG_DIR.mkdir(exist_ok=True)
    cutoff = _t.time() - LOG_ARCHIVE_DAYS * 86400
    for f in LOG_DIR.glob("genius_log_*.jsonl"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            print(f"  [log] 清理过期归档: {f.name}")

def run_preflight(no_gen):
    if not no_gen:
        raise RuntimeError("preflight 必须搭配 --no-gen，避免误触发生成")
    print(">> Preflight: key + workdir + tunnel（不生成图片，不消耗生成积分）")
    print(f"   skill script : {Path(__file__).resolve()}")
    print(f"   workdir      : {Path.cwd()}")
    print(f"   output dir   : {OUT_DIR}")

    balance = get_balance()
    print(f"   API key      : PASS（余额 {balance}）")

    OUT_DIR.mkdir(exist_ok=True)
    probe = OUT_DIR / ".genius_preflight.tmp"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    print("   workdir      : PASS（genius_output 可写）")

    server, tunnel_proc = None, None
    try:
        server = start_webhook(WEBHOOK_PORT)
        public_url, tunnel_proc = start_tunnel(WEBHOOK_PORT)
        print(f"   tunnel       : PASS（{public_url}）")
    finally:
        if tunnel_proc: tunnel_proc.terminate()
        if server: server.shutdown()
    print(">> Preflight OK")

def load_batch(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 兼容两种顶层格式：纯任务数组 [ {...}, {...} ]，或包装对象 { "tasks": [...] }
    if isinstance(data, dict) and "tasks" in data:
        tasks = data["tasks"]
    else:
        tasks = data
    if not isinstance(tasks, list):
        raise RuntimeError(
            "batch 文件顶层必须是任务数组 [ {...}, {...} ]，"
            "或包含 \"tasks\" 数组的对象 { \"tasks\": [...] }；"
            f"实际拿到的是 {type(tasks).__name__}"
        )
    if not tasks:
        raise RuntimeError("批量任务不能为空")
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            raise RuntimeError(f"第 {i+1} 个任务必须是对象 {{...}}，实际是 {type(t).__name__}")
        if "model" not in t: t["model"] = "gpt-image-2-premium"
        validate_task(t)
    return tasks

def run_single(args):
    t0 = time.time()
    task = {"prompt": args.prompt, "model": args.model, "aspect": args.aspect,
            "resolution": args.resolution, "ref": args.ref,
            "google_search": args.google_search, "output_format": args.output_format,
            "quality": args.quality}
    task = validate_task(task)

    print(f">> model: {task['model']}  prompt: {task['prompt']}")
    try:
        before = get_balance(); print(f">> 积分余额: {before}")
    except Exception as e:
        print(f"  [warn] 查余额失败: {e}"); before = None

    server, tunnel_proc = None, None
    try:
        print(">> [1/4] 启动 webhook + tunnel...")
        server = start_webhook(WEBHOOK_PORT)
        public_url, tunnel_proc = start_tunnel(WEBHOOK_PORT)
        callback_url = f"{public_url}/webhook"

        tid = None
        res = None
        for attempt in range(MAX_TASK_RETRIES + 1):
            if attempt:
                print(f"  [retry] 501 生成失败，{RETRY_DELAY}s 后重试 ({attempt}/{MAX_TASK_RETRIES})")
                time.sleep(RETRY_DELAY)
            print(f">> [2/4] 提交任务...")
            payload = build_payload(task, callback_url)
            tid = submit(payload)
            print(f"  task_id: {tid}")
            print(f">> [3/4] 等待回调（超时 {TIMEOUT_CALLBACK}s）...")
            res = wait_for_completion(tid, time.time() + TIMEOUT_CALLBACK)
            if res.get("status") == "success" or not is_generation_retryable(res) or attempt >= MAX_TASK_RETRIES:
                break

        if res.get("status") != "success":
            raise RuntimeError(f"任务失败: {res}")

        media_urls = extract_media_urls(res)
        img_url = media_urls[0] if media_urls else extract_image_url(res)
        safe = "".join(c if c.isalnum() else "_" for c in task["prompt"][:30]).strip("_") or "output"
        ext = task.get("output_format", "png")
        dest = find_next_filename(f"{task['model']}_{safe}", ext, OUT_DIR)
        size = download(img_url, dest)
        total = time.time() - t0

        try: after = get_balance()
        except: after = None
        consumed = (before - after) if (before is not None and after is not None) else None

        print(f">> [4/4] 完成 ✅")
        print(f"   模型     : {task['model']}")
        print(f"   总耗时   : {total:.1f}s")
        print(f"   文件大小 : {size/1024:.1f} KB")
        if consumed is not None: print(f"   积分消耗 : {consumed}（{before} → {after}）")
        print(f"   保存路径 : {dest}")

        write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                   "task_id": tid, "model": task["model"], "prompt": task["prompt"],
                   "aspect": task["aspect"], "resolution": task["resolution"],
                   "duration_s": round(total, 1), "credits": consumed,
                   "file_size_kb": round(size/1024, 1), "file_path": str(dest),
                   "media_urls": media_urls,
                    "status": "success"})

    except Exception as e:
        print(f">> 失败: {e}", file=sys.stderr)
        write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                   "model": task["model"], "prompt": task["prompt"],
                   "status": "failed", "error": str(e)})
        sys.exit(1)
    finally:
        if tunnel_proc: tunnel_proc.terminate()
        if server: server.shutdown()

def run_batch(args):
    t0 = time.time()
    tasks = load_batch(args.batch)
    n = len(tasks)
    print(f">> 批量模式: {n} 个任务，并发 {args.concurrent}")

    try:
        before = get_balance(); print(f">> 积分余额: {before}")
    except Exception as e:
        print(f"  [warn] 查余额失败: {e}"); before = None

    server, tunnel_proc = None, None
    task_map = {}
    try:
        print(">> [1/4] 启动 webhook + tunnel...")
        server = start_webhook(WEBHOOK_PORT)
        public_url, tunnel_proc = start_tunnel(WEBHOOK_PORT)
        callback_url = f"{public_url}/webhook"

        print(f">> [2/4] 并发提交 {n} 个任务（并发数 {args.concurrent}）...")
        def submit_one(idx, task):
            payload = build_payload(task, callback_url)
            tid = submit(payload)
            task_map[tid] = {**task, "idx": idx, "submit_time": time.time()}
            print(f"  [{idx+1}/{n}] {tid[:8]}... ({task['model']}) - 已提交")
            return tid

        with ThreadPoolExecutor(max_workers=args.concurrent) as ex:
            futures = [ex.submit(submit_one, i, t) for i, t in enumerate(tasks)]
            tids = [f.result() for f in as_completed(futures)]

        print(f">> [3/4] 等待所有回调（超时 {TIMEOUT_CALLBACK}s）...")
        deadline = time.time() + TIMEOUT_CALLBACK
        active_tids = set(tids)
        inactive_tids = set()
        while time.time() < deadline:
            with results_lock:
                done = sum(1 for tid in active_tids if tid in results)
            if done >= len(active_tids): break

            for tid in list(active_tids):
                with results_lock:
                    res_data = results.get(tid)
                if not res_data: continue
                res = res_data.get("data", res_data)
                if res.get("status") == "failed" and is_generation_retryable(res):
                    task_info = task_map.get(tid, {})
                    retry_count = task_info.get("retry_count", 0)
                    if retry_count < MAX_TASK_RETRIES:
                        print(f"\n  {tid[:8]}... 失败（{res.get('result', {}).get('message', 'unknown')}），{RETRY_DELAY}s 后重试 ({retry_count+1}/{MAX_TASK_RETRIES})")
                        time.sleep(RETRY_DELAY)
                        try:
                            task_for_retry = {k: v for k, v in task_info.items() if k not in ("idx", "submit_time", "retry_count")}
                            payload = build_payload(task_for_retry, callback_url)
                            new_tid = submit(payload)
                            task_map[new_tid] = {**task_for_retry, "idx": task_info.get("idx"), "retry_count": retry_count + 1, "submit_time": time.time()}
                            tids.append(new_tid)
                            active_tids.remove(tid)
                            inactive_tids.add(tid)
                            active_tids.add(new_tid)
                            print(f"  重试已提交: {new_tid[:8]}...")
                        except Exception as e:
                            print(f"  重试提交失败: {e}")
            time.sleep(2)
            with results_lock:
                done = sum(1 for tid in active_tids if tid in results)
            print(f"\r  进度: {done}/{len(active_tids)} 完成", end="", flush=True)
        print()

        for tid in list(active_tids):
            with results_lock:
                has_result = tid in results
            if has_result:
                continue
            try:
                info = get_task_info(tid)
                if info and info.get("status") in {"success", "failed"}:
                    with results_lock:
                        results[tid] = {"data": info}
                    print(f"  [recover] {tid[:8]}... TaskInfo: {info.get('status')}")
            except Exception as e:
                print(f"  [warn] TaskInfo 恢复失败 {tid[:8]}...: {e}")

        print(f">> [4/4] 下载图片 + 写日志...")
        ok, fail = 0, 0
        for tid in tids:
            if tid in inactive_tids:
                continue
            with results_lock:
                res_data = results.get(tid)
            task_info = task_map.get(tid, {})
            if not res_data:
                print(f"  {tid[:8]}... 超时未收到回调"); fail += 1
                write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                           "task_id": tid, "model": task_info.get("model"),
                           "prompt": task_info.get("prompt"), "status": "timeout"})
                continue
            res = res_data.get("data", res_data)
            if res.get("status") != "success":
                print(f"  {tid[:8]}... 生成失败: {res.get('result', {})}"); fail += 1
                write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                           "task_id": tid, "model": task_info.get("model"),
                           "prompt": task_info.get("prompt"), "status": "failed",
                           "error": str(res)})
                continue
            try:
                media_urls = extract_media_urls(res)
                img_url = media_urls[0] if media_urls else extract_image_url(res)
                safe = "".join(c if c.isalnum() else "_" for c in task_info["prompt"][:30]).strip("_") or "output"
                ext = task_info.get("output_format", "png")
                dest = find_next_filename(f"{task_info['model']}_{safe}", ext, OUT_DIR)
                size = download(img_url, dest)
                dur = time.time() - task_info["submit_time"]
                print(f"  {tid[:8]}... ✅ {dest.name} ({size/1024:.0f} KB, {dur:.1f}s)")
                write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                           "task_id": tid, "model": task_info["model"], "prompt": task_info["prompt"],
                           "aspect": task_info.get("aspect"), "resolution": task_info.get("resolution"),
                           "duration_s": round(dur, 1), "file_size_kb": round(size/1024, 1),
                           "file_path": str(dest), "media_urls": media_urls, "status": "success"})
                ok += 1
            except Exception as e:
                print(f"  {tid[:8]}... 下载失败: {e}"); fail += 1

        try: after = get_balance()
        except: after = None
        consumed = (before - after) if (before is not None and after is not None) else None
        total = time.time() - t0

        print(f"\n>> 批量完成 ✅")
        print(f"   成功/失败 : {ok}/{fail}")
        print(f"   总耗时    : {total:.1f}s（平均 {total/n:.1f}s/张）")
        if consumed is not None: print(f"   积分消耗  : {consumed}（{before} → {after}）")
        print(f"   日志文件  : {LOG_FILE}")

    except Exception as e:
        print(f">> 失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if tunnel_proc: tunnel_proc.terminate()
        if server: server.shutdown()

def main():
    ap = argparse.ArgumentParser(description="Genius 生图 v5 - 多模型异步批量")
    ap.add_argument("prompt", nargs="?", help="单张模式：生图 prompt")
    ap.add_argument("--batch", help="批量模式：JSON 配置文件路径")
    ap.add_argument("--concurrent", type=int, default=DEFAULT_CONCURRENT, help=f"并发数（默认 {DEFAULT_CONCURRENT}）")
    ap.add_argument("--model", default="gpt-image-2", choices=list(MODELS.keys()))
    ap.add_argument("--aspect", default=None, choices=ASPECTS, help="宽高比（不传则使用模型默认值）")
    ap.add_argument("--resolution", default=None, choices=["1K","2K","3K","4K"], help="分辨率（不传则使用模型默认值）")
    ap.add_argument("--quality", default=None, choices=["low","medium","high"], help="画质（仅 gpt-image-2-premium，不传则使用模型默认值）")
    ap.add_argument("--ref", nargs="+", help="参考图 URL 或本地图片路径；本地文件会自动转 base64")
    ap.add_argument("--google-search", dest="google_search", action="store_true")
    ap.add_argument("--output-format", default="png", choices=["png","jpg"])
    ap.add_argument("--balance", action="store_true")
    ap.add_argument("--preflight", action="store_true", help="检查 key/workdir/tunnel，不生成图片")
    ap.add_argument("--no-gen", action="store_true", help="与 --preflight 搭配，显式禁止生成")
    ap.add_argument("--out", default=None, help="输出目录（默认 ./genius_output/）")
    args = ap.parse_args()

    global OUT_DIR, LOG_FILE, LOG_DIR
    if args.out:
        OUT_DIR = Path(args.out)
    OUT_DIR.mkdir(exist_ok=True)
    LOG_DIR = OUT_DIR / "Logs"
    LOG_DIR.mkdir(exist_ok=True)
    LOG_FILE = LOG_DIR / "genius_log.jsonl"

    if args.balance:
        if not API_KEY: sys.exit("ERROR: set $env:CRUN_API_KEY first")
        print(f">> 当前积分余额: {get_balance()}"); return

    if args.preflight:
        if not API_KEY: sys.exit("ERROR: set $env:CRUN_API_KEY first")
        try:
            run_preflight(args.no_gen)
        except RuntimeError as e:
            sys.exit(f"ERROR: {e}")
        return

    if not API_KEY: sys.exit("ERROR: set $env:CRUN_API_KEY first")

    clean_old_logs()

    try:
        if args.batch:
            run_batch(args)
        elif args.prompt:
            run_single(args)
        else:
            ap.error("需要 prompt 或 --batch")
    except RuntimeError as e:
        sys.exit(f"ERROR: {e}")

if __name__ == "__main__":
    main()
