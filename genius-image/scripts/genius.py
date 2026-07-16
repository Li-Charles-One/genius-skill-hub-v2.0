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
PREMIUM_ASPECTS    = {"1:1","2:3","3:2","5:4","4:5","9:16","16:9","4:3","3:4","21:9","9:21","auto"}
NANO_ASPECTS       = {"1:1","2:3","3:2","3:4","4:3","4:5","5:4","9:16","16:9","1:4","4:1","1:8","8:1","21:9","auto"}

MODELS = {
    "gpt-image-2":          {"id": "openai/gpt-image-2",          "max_ref": 16, "max_prompt": 5000,  "extra": set(),                            "resolutions": {"1K","2K","4K"}, "aspects": GPT_IMAGE_2_ASPECTS, "default_aspect": "auto", "default_resolution": "1K"},
    "gpt-image-2-premium":  {"id": "openai/gpt-image-2-premium",  "max_ref": 14, "max_prompt": 10000, "extra": {"quality"},                     "resolutions": {"1K","2K","4K"}, "aspects": PREMIUM_ASPECTS,     "default_aspect": "1:1",  "default_resolution": "1K", "default_quality": "medium"},
    "nano-banana-2":        {"id": "google/nano-banana-2",        "max_ref": 14, "max_prompt": 20000, "extra": {"google_search","output_format"}, "resolutions": {"1K","2K","4K"}, "aspects": NANO_ASPECTS,        "default_aspect": "1:1",  "default_resolution": "1K"},
    "nano-banana-2-lite":   {"id": "google/nano-banana-2-lite",   "max_ref": 10, "max_prompt": 20000, "extra": set(),                            "resolutions": None,             "aspects": NANO_ASPECTS,        "default_aspect": "1:1"},
}

ASPECTS = sorted(set().union(*(cfg["aspects"] for cfg in MODELS.values())))

WEBHOOK_PORT = 8765
TUNNEL_START_TIMEOUT = 60
TIMEOUT_SUBMIT = 30
TIMEOUT_DOWNLOAD = 180
TIMEOUT_CALLBACK = 300
WAIT_PROGRESS_INTERVAL = 15
TASKINFO_POLL_INTERVAL = 30
POLL_ONLY_INTERVAL = 5
MAX_RETRIES = 3
DEFAULT_CONCURRENT = 5
MAX_TASK_RETRIES = 3
RETRY_DELAY = 5
DOWNLOAD_RETRIES = 3

ERROR_MAP = {
    401: "API Key 无效", 402: "积分不足", 403: "API Key 已禁用", 404: "任务不存在",
    422: "参数错误", 429: "限速", 455: "维护中",
    500: "服务器错误", 501: "生成失败", 505: "功能禁用",
}

results = {}
results_lock = threading.Lock()
results_event = threading.Event()
active_task_ids = set()
active_task_ids_lock = threading.Lock()

def log_print(*args, **kwargs):
    kwargs.setdefault("flush", True)
    print(*args, **kwargs)

def configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(line_buffering=True)
        except Exception:
            pass

def register_task(tid):
    if not tid:
        return
    with active_task_ids_lock:
        active_task_ids.add(tid)

def unregister_task(tid):
    if not tid:
        return
    with active_task_ids_lock:
        active_task_ids.discard(tid)

def install_signal_handlers():
    import signal
    def _on_signal(signum, frame):
        with active_task_ids_lock:
            tids = list(active_task_ids)
        if tids:
            log_print(f"\n>> 收到中断信号({signum})，进行中的 task_id:", file=sys.stderr)
            for tid in tids:
                log_print(f"   task_id={tid}", file=sys.stderr)
                log_print(f"   补下: python \"{Path(__file__).resolve()}\" --fetch-task {tid}", file=sys.stderr)
        raise SystemExit(130)
    for name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, _on_signal)
        except Exception:
            pass

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
            log_print(f"\n  [webhook] {tid[:8]}... → {st}")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            log_print(f"\n  [webhook] 解析失败: {e}")
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
            log_print(f"  [tunnel] 公网 URL: {m.group(0)}")
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
    # resolution: 仅对支持 resolution 的模型处理
    if cfg.get("resolutions") is not None:
        if not task.get("resolution"):
            task["resolution"] = cfg["default_resolution"]
        if task["resolution"] not in cfg["resolutions"]:
            raise RuntimeError(f"{task['model']} 不支持分辨率 {task['resolution']}，可用: {sorted(cfg['resolutions'])}")
    elif task.get("resolution"):
        raise RuntimeError(f"{task['model']} 不支持 resolution 参数")
    if "quality" in cfg["extra"]:
        if not task.get("quality"):
            task["quality"] = cfg.get("default_quality", "medium")
    if task["aspect"] not in cfg["aspects"]:
        raise RuntimeError(f"{task['model']} 不支持宽高比 {task['aspect']}")
    if task.get("quality") and "quality" not in cfg["extra"]:
        raise RuntimeError(f"{task['model']} 不支持 quality 参数")
    if task.get("google_search") and "google_search" not in cfg["extra"]:
        raise RuntimeError(f"{task['model']} 不支持 google_search 参数")
    if task.get("output_format") not in (None, "png") and "output_format" not in cfg["extra"]:
        raise RuntimeError(f"{task['model']} 不支持 output_format 参数")
    if task["model"] == "gpt-image-2" and task.get("resolution") == "4K" and task["aspect"] == "1:1":
        raise RuntimeError("gpt-image-2 的 4K 分辨率不支持 1:1 宽高比")
    if task["model"] == "gpt-image-2" and task["aspect"] == "auto" and task.get("resolution") != "1K":
        raise RuntimeError("gpt-image-2 的 auto 宽高比仅支持 1K 分辨率")
    if task.get("ref") and len(task["ref"]) > cfg["max_ref"]:
        raise RuntimeError(f"{task['model']} 最多 {cfg['max_ref']} 张参考图")
    return task

def is_generation_retryable(res):
    result = res.get("result") if isinstance(res, dict) else None
    return isinstance(result, dict) and result.get("code") == 501

def wait_for_completion(tid, deadline, poll_only=False):
    t0 = time.time()
    last_progress = t0
    # poll-only: first TaskInfo almost immediately; hybrid: wait longer for webhook
    last_poll = 0 if poll_only else t0
    poll_interval = POLL_ONLY_INTERVAL if poll_only else TASKINFO_POLL_INTERVAL
    mode = "poll-only" if poll_only else "hybrid"
    while time.time() < deadline:
        with results_lock:
            if tid in results:
                return results[tid].get("data", results[tid])
        now = time.time()
        if now - last_progress >= WAIT_PROGRESS_INTERVAL:
            elapsed = int(now - t0)
            remaining = max(0, int(deadline - now))
            log_print(f"  [wait/{mode}] {tid[:8]}... still waiting  elapsed={elapsed}s  remaining≈{remaining}s")
            last_progress = now
        if now - last_poll >= poll_interval:
            last_poll = now
            try:
                info = get_task_info(tid)
                if info and info.get("status") in {"success", "failed"}:
                    with results_lock:
                        results[tid] = {"data": info}
                    log_print(f"  [poll] {tid[:8]}... TaskInfo → {info.get('status')}")
                    return info
                st = info.get("status") if isinstance(info, dict) else "unknown"
                log_print(f"  [poll] {tid[:8]}... TaskInfo status={st}")
            except Exception as e:
                log_print(f"  [poll] TaskInfo 查询失败: {e}")
        time.sleep(1)
    log_print(f"  [warn] 等待超时，最终 TaskInfo 恢复: {tid}")
    try:
        info = get_task_info(tid)
    except Exception as e:
        raise TimeoutError(
            f"等待超时 {TIMEOUT_CALLBACK}s，task_id={tid}，TaskInfo 失败: {e}。"
            f"稍后可用 --fetch-task {tid} 补下。"
        ) from e
    if info and info.get("status") in {"success", "failed"}:
        with results_lock:
            results[tid] = {"data": info}
        log_print(f"  [recover] {tid[:8]}... TaskInfo → {info.get('status')}")
        return info
    status = info.get("status") if isinstance(info, dict) else "unknown"
    raise TimeoutError(
        f"等待超时 {TIMEOUT_CALLBACK}s，task_id={tid}，TaskInfo 状态: {status}。"
        f"稍后可用 --fetch-task {tid} 补下。"
    )

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

def build_payload(task, callback_url=None):
    task = validate_task(task)
    cfg = MODELS[task["model"]]
    inp = {"prompt": task["prompt"], "aspect_ratio": task["aspect"]}
    # resolution: 仅对支持的模型写入
    if cfg.get("resolutions") is not None:
        inp["resolution"] = task["resolution"]
    if task.get("ref"):
        inp["img_urls"] = resolve_refs(task["ref"])
    if "google_search" in cfg["extra"] and task.get("google_search"):
        inp["google_search"] = True
    if "output_format" in cfg["extra"]:
        fmt = task.get("output_format") or cfg.get("default_output_format", "png")
        inp["output_format"] = fmt
    if "quality" in cfg["extra"]:
        inp["quality"] = task.get("quality") or cfg.get("default_quality", "medium")
    payload = {"model": cfg["id"], "input": inp}
    if callback_url:
        payload["callback_url"] = callback_url
    return payload

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

def download(url, dest, retries=DOWNLOAD_RETRIES):
    last = None
    for attempt in range(retries):
        try:
            r = request_with_retry("GET", url, timeout=TIMEOUT_DOWNLOAD)
            if r.status_code != 200:
                raise RuntimeError(f"下载失败 HTTP {r.status_code}")
            content_type = r.headers.get("Content-Type", "")
            if content_type and not content_type.startswith("image/"):
                raise RuntimeError(f"下载内容不是图片: {content_type}")
            dest.write_bytes(r.content)
            return len(r.content)
        except Exception as e:
            last = e
            if attempt < retries - 1:
                wait = 2 ** attempt
                log_print(f"  [download] 失败重试 {attempt+1}/{retries-1}，{wait}s 后: {e}")
                time.sleep(wait)
    raise RuntimeError(f"下载失败（已重试 {retries} 次）: {last}")

def safe_filename_stem(text, max_len=36):
    text = (text or "").strip()
    parts = []
    for ch in text:
        if ch.isalnum() or ch in "-_" or "\u4e00" <= ch <= "\u9fff":
            parts.append(ch)
        elif ch.isspace() or ch in ".,，。、/\\:：;；!！?？\"'“”‘’()（）[]【】{}":
            parts.append("_")
    stem = re.sub(r"_+", "_", "".join(parts)).strip("_")
    if not stem:
        stem = "output"
    return stem[:max_len]

def make_output_basename(model, prompt, name=None):
    if name:
        return safe_filename_stem(name, max_len=48)
    return f"{model}_{safe_filename_stem(prompt)}"

def find_next_filename(base, ext, out_dir):
    i = 1
    while True:
        dest = out_dir / f"{base}_{i}.{ext}"
        if not dest.exists(): return dest
        i += 1

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

def pick_webhook_port(preferred=None):
    import socket
    preferred = preferred or WEBHOOK_PORT
    candidates = [preferred] + [p for p in range(preferred + 1, preferred + 30) if p != preferred]
    for port in candidates:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
                if port != preferred:
                    log_print(f"  [port] {preferred} 占用，改用 {port}")
                return port
            except OSError:
                continue
    raise RuntimeError(f"端口 {preferred}-{preferred+29} 均不可用")

def setup_delivery(poll_only=False, port=None):
    """Return (callback_url, server, tunnel_proc, port_used). poll-only skips tunnel."""
    if poll_only:
        log_print(">> [1/4] poll-only 模式：跳过 webhook + tunnel，仅轮询 TaskInfo")
        return None, None, None, None
    port_used = pick_webhook_port(port or WEBHOOK_PORT)
    log_print(f">> [1/4] 启动 webhook + tunnel（port {port_used}）...")
    server = start_webhook(port_used)
    public_url, tunnel_proc = start_tunnel(port_used)
    return f"{public_url}/webhook", server, tunnel_proc, port_used

def write_log(entry):
    LOG_DIR.mkdir(exist_ok=True)
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > LOG_MAX_SIZE:
        archive = LOG_DIR / f"genius_log_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
        LOG_FILE.rename(archive)
        log_print(f"  [log] 日志已轮转: {archive.name}")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def clean_old_logs():
    import time as _t
    LOG_DIR.mkdir(exist_ok=True)
    cutoff = _t.time() - LOG_ARCHIVE_DAYS * 86400
    for f in LOG_DIR.glob("genius_log_*.jsonl"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            log_print(f"  [log] 清理过期归档: {f.name}")

def try_recover_task_urls(tid):
    if not tid:
        return None, []
    try:
        info = get_task_info(tid)
    except Exception as e:
        log_print(f"  [recover] TaskInfo 失败: {e}")
        return None, []
    if not info:
        return None, []
    urls = extract_media_urls(info)
    return info, urls

def run_fetch_task(tid, name=None):
    log_print(f">> 从 task_id 补下: {tid}")
    info = get_task_info(tid)
    if not info:
        raise RuntimeError(f"TaskInfo 为空: {tid}")
    status = info.get("status")
    log_print(f"   status: {status}")
    if status != "success":
        raise RuntimeError(f"任务尚未成功，status={status}，task_id={tid}")
    media_urls = extract_media_urls(info)
    if not media_urls:
        img_url = extract_image_url(info)
        media_urls = [img_url]
    img_url = media_urls[0]
    base = make_output_basename("fetch", tid[:8], name=name or f"fetch_{tid[:8]}")
    dest = find_next_filename(base, "png", OUT_DIR)
    size = download(img_url, dest)
    log_print(f">> 补下完成 ✅")
    log_print(f"   task_id   : {tid}")
    log_print(f"   media_url : {img_url}")
    log_print(f"   文件大小  : {size/1024:.1f} KB")
    log_print(f"   保存路径  : {dest}")
    emit_result(status="fetched", task_id=tid, path=dest, media_url=img_url, size_kb=round(size/1024, 1))
    write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
               "task_id": tid, "file_path": str(dest), "file_size_kb": round(size/1024, 1),
               "media_urls": media_urls, "status": "fetched"})
    return dest

def run_preflight(no_gen, poll_only=False, port=None):
    if not no_gen:
        raise RuntimeError("preflight 必须搭配 --no-gen，避免误触发生成")
    log_print(">> Preflight: key + workdir + delivery（不生成图片，不消耗生成积分）")
    log_print(f"   skill script : {Path(__file__).resolve()}")
    log_print(f"   workdir      : {Path.cwd()}")
    log_print(f"   output dir   : {OUT_DIR}")
    log_print(f"   mode         : {'poll-only' if poll_only else 'webhook+tunnel'}")

    balance = get_balance()
    log_print(f"   API key      : PASS（余额 {balance}）")

    OUT_DIR.mkdir(exist_ok=True)
    probe = OUT_DIR / ".genius_preflight.tmp"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    log_print("   workdir      : PASS（genius_output 可写）")

    if poll_only:
        log_print("   tunnel       : SKIP（--poll-only）")
        log_print(">> Preflight OK")
        return

    server, tunnel_proc = None, None
    try:
        port_used = pick_webhook_port(port or WEBHOOK_PORT)
        server = start_webhook(port_used)
        public_url, tunnel_proc = start_tunnel(port_used)
        log_print(f"   tunnel       : PASS（{public_url}，port {port_used}）")
    finally:
        if tunnel_proc: tunnel_proc.terminate()
        if server: server.shutdown()
    log_print(">> Preflight OK")

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
    poll_only = bool(getattr(args, "poll_only", False))
    task = {"prompt": args.prompt, "model": args.model, "aspect": args.aspect,
            "resolution": args.resolution, "ref": args.ref,
            "google_search": args.google_search, "output_format": args.output_format,
            "quality": args.quality}
    task = validate_task(task)

    log_print(f">> model: {task['model']}  prompt: {task['prompt']}")
    try:
        before = get_balance(); log_print(f">> 积分余额: {before}")
    except Exception as e:
        log_print(f"  [warn] 查余额失败: {e}"); before = None

    server, tunnel_proc = None, None
    tid = None
    try:
        callback_url, server, tunnel_proc, _port = setup_delivery(
            poll_only=poll_only, port=getattr(args, "port", None))

        res = None
        for attempt in range(MAX_TASK_RETRIES + 1):
            if attempt:
                log_print(f"  [retry] 501 生成失败，{RETRY_DELAY}s 后重试 ({attempt}/{MAX_TASK_RETRIES})")
                time.sleep(RETRY_DELAY)
            log_print(">> [2/4] 提交任务...")
            payload = build_payload(task, callback_url)
            tid = submit(payload)
            register_task(tid)
            log_print(f"  task_id: {tid}")
            write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                       "task_id": tid, "model": task["model"], "prompt": task["prompt"],
                       "aspect": task.get("aspect"), "resolution": task.get("resolution"),
                       "status": "submitted", "mode": "poll-only" if poll_only else "webhook"})
            poll_hint = f"每 {POLL_ONLY_INTERVAL}s 轮询 TaskInfo" if poll_only else f"每 {WAIT_PROGRESS_INTERVAL}s 心跳，每 {TASKINFO_POLL_INTERVAL}s 轮询 TaskInfo"
            log_print(f">> [3/4] 等待完成（超时 {TIMEOUT_CALLBACK}s；{poll_hint}）...")
            res = wait_for_completion(tid, time.time() + TIMEOUT_CALLBACK, poll_only=poll_only)
            if res.get("status") == "success" or not is_generation_retryable(res) or attempt >= MAX_TASK_RETRIES:
                break

        if res.get("status") != "success":
            raise RuntimeError(f"任务失败 task_id={tid}: {res}")

        media_urls = extract_media_urls(res)
        img_url = media_urls[0] if media_urls else extract_image_url(res)
        ext = task.get("output_format") or "png"
        base = make_output_basename(task["model"], task["prompt"], name=getattr(args, "name", None))
        dest = find_next_filename(base, ext, OUT_DIR)
        size = download(img_url, dest)
        total = time.time() - t0

        try: after = get_balance()
        except: after = None
        consumed = (before - after) if (before is not None and after is not None) else None

        log_print(">> [4/4] 完成 ✅")
        log_print(f"   模型     : {task['model']}")
        log_print(f"   task_id  : {tid}")
        log_print(f"   media_url: {img_url}")
        log_print(f"   总耗时   : {total:.1f}s")
        log_print(f"   文件大小 : {size/1024:.1f} KB")
        if consumed is not None: log_print(f"   积分消耗 : {consumed}（{before} → {after}）")
        log_print(f"   保存路径 : {dest}")
        emit_result(status="success", model=task["model"], task_id=tid, path=dest,
                    media_url=img_url, duration_s=round(total, 1),
                    size_kb=round(size/1024, 1), credits=consumed)

        write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                   "task_id": tid, "model": task["model"], "prompt": task["prompt"],
                   "aspect": task["aspect"], "resolution": task["resolution"],
                   "duration_s": round(total, 1), "credits": consumed,
                   "file_size_kb": round(size/1024, 1), "file_path": str(dest),
                   "media_urls": media_urls,
                    "status": "success"})

    except Exception as e:
        log_print(f">> 失败: {e}", file=sys.stderr)
        entry = {"timestamp": datetime.now().isoformat(timespec="seconds"),
                 "model": task["model"], "prompt": task["prompt"],
                 "status": "failed", "error": str(e)}
        if tid:
            entry["task_id"] = tid
            log_print(f"   task_id: {tid}", file=sys.stderr)
            info, urls = try_recover_task_urls(tid)
            if info is not None:
                entry["task_status"] = info.get("status")
            if urls:
                entry["media_urls"] = urls
                log_print(f"   可恢复 media_url: {urls[0]}", file=sys.stderr)
            log_print(f"   补下命令: python \"{Path(__file__).resolve()}\" --fetch-task {tid} --out \"{OUT_DIR}\"", file=sys.stderr)
            emit_result(status="failed", task_id=tid, error=str(e),
                        media_url=(urls[0] if urls else None))
        else:
            emit_result(status="failed", error=str(e))
        write_log(entry)
        sys.exit(1)
    finally:
        unregister_task(tid)
        if tunnel_proc: tunnel_proc.terminate()
        if server: server.shutdown()

def run_batch(args):
    t0 = time.time()
    poll_only = bool(getattr(args, "poll_only", False))
    tasks = load_batch(args.batch)
    n = len(tasks)
    log_print(f">> 批量模式: {n} 个任务，并发 {args.concurrent}，mode={'poll-only' if poll_only else 'webhook'}")

    try:
        before = get_balance(); log_print(f">> 积分余额: {before}")
    except Exception as e:
        log_print(f"  [warn] 查余额失败: {e}"); before = None

    server, tunnel_proc = None, None
    task_map = {}
    tids = []
    try:
        callback_url, server, tunnel_proc, _port = setup_delivery(
            poll_only=poll_only, port=getattr(args, "port", None))
        batch_poll_interval = POLL_ONLY_INTERVAL if poll_only else TASKINFO_POLL_INTERVAL

        log_print(f">> [2/4] 并发提交 {n} 个任务（并发数 {args.concurrent}）...")
        def submit_one(idx, task):
            payload = build_payload(task, callback_url)
            tid = submit(payload)
            register_task(tid)
            task_map[tid] = {**task, "idx": idx, "submit_time": time.time()}
            write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                       "task_id": tid, "model": task.get("model"), "prompt": task.get("prompt"),
                       "status": "submitted", "mode": "poll-only" if poll_only else "webhook"})
            log_print(f"  [{idx+1}/{n}] {tid} ({task['model']}) - 已提交")
            return tid

        with ThreadPoolExecutor(max_workers=args.concurrent) as ex:
            futures = [ex.submit(submit_one, i, t) for i, t in enumerate(tasks)]
            tids = [f.result() for f in as_completed(futures)]

        log_print(f">> [3/4] 等待所有任务（超时 {TIMEOUT_CALLBACK}s；每 {batch_poll_interval}s 轮询 TaskInfo）...")
        deadline = time.time() + TIMEOUT_CALLBACK
        last_poll = 0 if poll_only else time.time()
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
                        log_print(f"\n  {tid[:8]}... 失败（{res.get('result', {}).get('message', 'unknown')}），{RETRY_DELAY}s 后重试 ({retry_count+1}/{MAX_TASK_RETRIES})")
                        time.sleep(RETRY_DELAY)
                        try:
                            task_for_retry = {k: v for k, v in task_info.items() if k not in ("idx", "submit_time", "retry_count")}
                            payload = build_payload(task_for_retry, callback_url)
                            new_tid = submit(payload)
                            register_task(new_tid)
                            unregister_task(tid)
                            task_map[new_tid] = {**task_for_retry, "idx": task_info.get("idx"), "retry_count": retry_count + 1, "submit_time": time.time()}
                            write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                                       "task_id": new_tid, "model": task_for_retry.get("model"),
                                       "prompt": task_for_retry.get("prompt"), "status": "submitted",
                                       "retry_of": tid})
                            tids.append(new_tid)
                            active_tids.remove(tid)
                            inactive_tids.add(tid)
                            active_tids.add(new_tid)
                            log_print(f"  重试已提交: {new_tid}")
                        except Exception as e:
                            log_print(f"  重试提交失败: {e}")

            now = time.time()
            if now - last_poll >= batch_poll_interval:
                last_poll = now
                for tid in list(active_tids):
                    with results_lock:
                        if tid in results:
                            continue
                    try:
                        info = get_task_info(tid)
                        if info and info.get("status") in {"success", "failed"}:
                            with results_lock:
                                results[tid] = {"data": info}
                            log_print(f"  [poll] {tid[:8]}... TaskInfo → {info.get('status')}")
                        elif info:
                            log_print(f"  [poll] {tid[:8]}... TaskInfo status={info.get('status')}")
                    except Exception as e:
                        log_print(f"  [poll] TaskInfo 查询失败 {tid[:8]}...: {e}")

            time.sleep(1 if poll_only else 2)
            with results_lock:
                done = sum(1 for tid in active_tids if tid in results)
            log_print(f"  进度: {done}/{len(active_tids)} 完成")

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
                    log_print(f"  [recover] {tid[:8]}... TaskInfo: {info.get('status')}")
            except Exception as e:
                log_print(f"  [warn] TaskInfo 恢复失败 {tid[:8]}...: {e}")

        log_print(">> [4/4] 下载图片 + 写日志...")
        ok, fail = 0, 0
        for tid in tids:
            if tid in inactive_tids:
                continue
            with results_lock:
                res_data = results.get(tid)
            task_info = task_map.get(tid, {})
            if not res_data:
                log_print(f"  {tid} 超时未完成；可稍后 --fetch-task {tid}"); fail += 1
                write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                           "task_id": tid, "model": task_info.get("model"),
                           "prompt": task_info.get("prompt"), "status": "timeout"})
                emit_result(status="timeout", task_id=tid)
                continue
            res = res_data.get("data", res_data)
            if res.get("status") != "success":
                log_print(f"  {tid[:8]}... 生成失败: {res.get('result', {})}"); fail += 1
                write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                           "task_id": tid, "model": task_info.get("model"),
                           "prompt": task_info.get("prompt"), "status": "failed",
                           "error": str(res)})
                emit_result(status="failed", task_id=tid)
                continue
            try:
                media_urls = extract_media_urls(res)
                img_url = media_urls[0] if media_urls else extract_image_url(res)
                ext = task_info.get("output_format") or "png"
                base = make_output_basename(task_info["model"], task_info.get("prompt", ""),
                                           name=task_info.get("name"))
                dest = find_next_filename(base, ext, OUT_DIR)
                size = download(img_url, dest)
                dur = time.time() - task_info["submit_time"]
                log_print(f"  {tid[:8]}... ✅ {dest.name} ({size/1024:.0f} KB, {dur:.1f}s)")
                log_print(f"     media_url: {img_url}")
                emit_result(status="success", task_id=tid, model=task_info["model"],
                            path=dest, media_url=img_url, duration_s=round(dur, 1),
                            size_kb=round(size/1024, 1))
                write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                           "task_id": tid, "model": task_info["model"], "prompt": task_info["prompt"],
                           "aspect": task_info.get("aspect"), "resolution": task_info.get("resolution"),
                           "duration_s": round(dur, 1), "file_size_kb": round(size/1024, 1),
                           "file_path": str(dest), "media_urls": media_urls, "status": "success"})
                ok += 1
            except Exception as e:
                log_print(f"  {tid[:8]}... 下载失败: {e}；可稍后 --fetch-task {tid}"); fail += 1
                write_log({"timestamp": datetime.now().isoformat(timespec="seconds"),
                           "task_id": tid, "model": task_info.get("model"),
                           "prompt": task_info.get("prompt"), "status": "download_failed",
                           "error": str(e)})
                emit_result(status="download_failed", task_id=tid, error=str(e))

        try: after = get_balance()
        except: after = None
        consumed = (before - after) if (before is not None and after is not None) else None
        total = time.time() - t0

        log_print("\n>> 批量完成 ✅")
        log_print(f"   成功/失败 : {ok}/{fail}")
        log_print(f"   总耗时    : {total:.1f}s（平均 {total/n:.1f}s/张）")
        if consumed is not None: log_print(f"   积分消耗  : {consumed}（{before} → {after}）")
        log_print(f"   日志文件  : {LOG_FILE}")
        emit_result(status="batch_done", ok=ok, fail=fail, duration_s=round(total, 1), credits=consumed)

    except Exception as e:
        log_print(f">> 失败: {e}", file=sys.stderr)
        if tids:
            log_print(f"   已提交 task_id: {', '.join(tids)}", file=sys.stderr)
            emit_result(status="failed", error=str(e), task_ids=",".join(tids))
        else:
            emit_result(status="failed", error=str(e))
        sys.exit(1)
    finally:
        for tid in list(active_task_ids):
            unregister_task(tid)
        if tunnel_proc: tunnel_proc.terminate()
        if server: server.shutdown()

def main():
    configure_stdio()
    install_signal_handlers()
    ap = argparse.ArgumentParser(description="Genius 生图 v5 - 多模型异步批量")
    ap.add_argument("prompt", nargs="?", help="单张模式：生图 prompt")
    ap.add_argument("--batch", help="批量模式：JSON 配置文件路径")
    ap.add_argument("--concurrent", type=int, default=DEFAULT_CONCURRENT, help=f"并发数（默认 {DEFAULT_CONCURRENT}）")
    ap.add_argument("--model", default="gpt-image-2", choices=list(MODELS.keys()))
    ap.add_argument("--aspect", default=None, choices=ASPECTS, help="宽高比（不传则使用模型默认值）")
    ap.add_argument("--resolution", default=None, choices=["1K","2K","4K"], help="分辨率（不传则使用模型默认值）")
    ap.add_argument("--quality", default=None, choices=["low","medium","high"], help="画质（仅 gpt-image-2-premium，不传则使用模型默认值）")
    ap.add_argument("--ref", nargs="+", help="参考图 URL 或本地图片路径；本地文件会自动转 base64")
    ap.add_argument("--google-search", dest="google_search", action="store_true")
    ap.add_argument("--output-format", default=None, choices=["png","jpg","webp"], help="输出格式（仅 nano-banana-2 支持；其余默认 png）")
    ap.add_argument("--name", default=None, help="输出文件名主干（不含扩展名）；不传则 model_prompt 自动生成")
    ap.add_argument("--poll-only", dest="poll_only", action="store_true",
                    help="仅轮询 TaskInfo，不启动 webhook/cloudflared（Agent 环境推荐）")
    ap.add_argument("--port", type=int, default=None, help=f"webhook 端口（默认 {WEBHOOK_PORT}；占用时自动顺延）")
    ap.add_argument("--balance", action="store_true")
    ap.add_argument("--preflight", action="store_true", help="检查 key/workdir/delivery，不生成图片")
    ap.add_argument("--no-gen", action="store_true", help="与 --preflight 搭配，显式禁止生成")
    ap.add_argument("--fetch-task", dest="fetch_task", default=None, help="用已有 task_id 从 TaskInfo 补下结果图（无需 tunnel）")
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
        log_print(f">> 当前积分余额: {get_balance()}"); return

    if args.preflight:
        if not API_KEY: sys.exit("ERROR: set $env:CRUN_API_KEY first")
        try:
            run_preflight(args.no_gen, poll_only=args.poll_only, port=args.port)
        except RuntimeError as e:
            sys.exit(f"ERROR: {e}")
        return

    if args.fetch_task:
        if not API_KEY: sys.exit("ERROR: set $env:CRUN_API_KEY first")
        try:
            run_fetch_task(args.fetch_task, name=args.name)
        except Exception as e:
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
            ap.error("需要 prompt、--batch 或 --fetch-task")
    except RuntimeError as e:
        sys.exit(f"ERROR: {e}")

if __name__ == "__main__":
    main()
