#!/usr/bin/env python3
"""Genius Subtitle 花字模式: designed captions on a finished video, driven by one file, huazi.json.

  huazi.py templates                                       list built-in and custom templates
  huazi.py new-template <id> [--from TEMPLATE] [--name N]  copy a template as a custom one to edit
  huazi.py init <video> [--dir DIR] [--overlays X.overlays.json] [--template T] [--brand HEX]
  huazi.py preview <dir> [--ids H03,N3] [--template T] [--brand HEX]   style sheet on real frames
  huazi.py render <dir> [--ids ...] [--format hevc|prores] [--no-burn]   one alpha MOV per item + burned preview
  huazi.py --check

Templates are HTML/CSS (assets/huazi/templates/<id>/style.css + optional decorate.js) laid out by
assets/huazi/runtime.js and captured frame by frame through a headless Chromium browser (Chrome, Edge,
Chromium or Brave; HUAZI_BROWSER overrides) over the DevTools protocol. Stdlib only, plus ffmpeg/ffprobe.
Failures print `Error [CODE]: ...` to stderr and exit with EXIT_CODES[CODE].
"""
from __future__ import annotations

import argparse, base64, json, os, platform, re, shutil, socket, struct, subprocess, sys, tempfile, time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from subs import EXIT_CODES, SubsError, ffmpeg, log, probe, run  # noqa: E402

SKILL = Path(__file__).resolve().parents[1]
ASSETS = SKILL / "assets/huazi"
TEMPLATES = ASSETS / "templates"
TYPES = ("title", "stack", "number", "list", "name")
ALIGNS = ("left", "right", "center")
SAFE = {"x": 0.075, "top": 0.07}      # side margin and top margin, share of width / height
BOTTOM = 0.80                          # an item's bottom edge stays above this share of the height (subtitle zone)


# ---------- browser over the DevTools protocol ----------
def find_browser() -> str | None:
    env = os.environ.get("HUAZI_BROWSER")
    if env:
        return env if Path(env).exists() else None
    sysname = platform.system()
    if sysname == "Darwin":
        cands = [f"/Applications/{a}.app/Contents/MacOS/{a}" for a in
                 ("Google Chrome", "Microsoft Edge", "Chromium", "Brave Browser")]
    elif sysname == "Windows":
        pf = [os.environ.get(k, "") for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        cands = [str(Path(p) / s) for p in pf if p for s in
                 ("Google/Chrome/Application/chrome.exe", "Microsoft/Edge/Application/msedge.exe")]
    else:
        cands = [shutil.which(n) or "" for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge")]
    return next((c for c in cands if c and Path(c).exists()), None)


class Browser:
    """One headless page: load a file, wait for window.hzReady, seek, screenshot (alpha kept)."""

    def __init__(self, w: int, h: int):
        exe = find_browser()
        if not exe:
            raise SubsError("DEPENDENCY_MISSING", "no Chrome / Edge / Chromium / Brave found (set HUAZI_BROWSER)")
        self.tmp = tempfile.mkdtemp(prefix="huazi-browser-")
        self.proc = subprocess.Popen([exe, "--headless=new", "--remote-debugging-port=0", f"--user-data-dir={self.tmp}",
                                      "--allow-file-access-from-files", "--hide-scrollbars", "--disable-gpu", "--no-first-run",
                                      "--force-device-scale-factor=1", f"--window-size={w},{h}", "about:blank"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file, t0 = Path(self.tmp) / "DevToolsActivePort", time.time()
        while not port_file.exists() or not port_file.read_text().strip():
            if time.time() - t0 > 30:
                self.close(); raise SubsError("TIMEOUT", "browser did not open its DevTools port in 30 s")
            time.sleep(0.1)
        port = int(port_file.read_text().split()[0])
        targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=10).read())
        ws = next(t["webSocketDebuggerUrl"] for t in targets if t.get("type") == "page")
        self._connect(ws); self.n = 0
        self.call("Page.enable"); self.call("Runtime.enable")
        self.call("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": False})
        self.call("Emulation.setDefaultBackgroundColorOverride", {"color": {"r": 0, "g": 0, "b": 0, "a": 0}})
        self.w, self.h = w, h

    # minimal WebSocket client (RFC 6455): masked text frames out, unmasked frames in
    def _connect(self, url: str) -> None:
        m = re.match(r"ws://([^:/]+):(\d+)(/.*)", url)
        host, port, path = m.group(1), int(m.group(2)), m.group(3)
        self.sock = socket.create_connection((host, port), timeout=120)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        if b" 101 " not in buf.split(b"\r\n")[0]:
            raise SubsError("PROVIDER_ERROR", "DevTools WebSocket handshake failed")
        self.rest = buf.split(b"\r\n\r\n", 1)[1]

    def _read(self, n: int) -> bytes:
        while len(self.rest) < n:
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                raise SubsError("PROVIDER_ERROR", "browser closed the DevTools connection")
            self.rest += chunk
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def _send(self, text: str) -> None:
        data = text.encode(); mask = os.urandom(4); n = len(data)
        head = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else
                                bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536 else
                                bytes([0x80 | 127]) + struct.pack(">Q", n))
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _recv(self) -> dict:
        msg = b""
        while True:
            b0, b1 = self._read(2); n = b1 & 0x7F
            if n == 126: n = struct.unpack(">H", self._read(2))[0]
            elif n == 127: n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n); op = b0 & 0x0F
            if op == 0x8:
                raise SubsError("PROVIDER_ERROR", "browser closed the DevTools connection")
            if op in (0x9, 0xA):
                continue
            msg += payload
            if b0 & 0x80:
                return json.loads(msg)

    def call(self, method: str, params: dict | None = None) -> dict:
        self.n += 1; my = self.n
        self._send(json.dumps({"id": my, "method": method, "params": params or {}}))
        while True:
            r = self._recv()
            if r.get("id") == my:
                if "error" in r:
                    raise SubsError("PROVIDER_ERROR", f"{method}: {r['error'].get('message')}")
                return r.get("result", {})

    def eval(self, expr: str):
        r = self.call("Runtime.evaluate", {"expression": expr, "awaitPromise": True, "returnByValue": True})
        if "exceptionDetails" in r:
            raise SubsError("UNSUPPORTED_FORMAT", "template error: " + json.dumps(r["exceptionDetails"], ensure_ascii=False)[:600])
        return r.get("result", {}).get("value")

    def load(self, page: Path) -> dict:
        self.call("Page.navigate", {"url": page.resolve().as_uri()})
        t0 = time.time()
        while self.eval("document.readyState") != "complete" or not self.eval("!!window.hzReady"):
            if time.time() - t0 > 30:
                raise SubsError("TIMEOUT", f"{page.name} did not load in 30 s")
            time.sleep(0.05)
        return self.eval("window.hzReady")

    def shot(self, t: float, out: Path) -> None:
        self.eval(f"window.hzSeek({t:.5f})")
        r = self.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False,
                                                  "clip": {"x": 0, "y": 0, "width": self.w, "height": self.h, "scale": 1}})
        out.write_bytes(base64.b64decode(r["data"]))

    def close(self) -> None:
        try:
            self.sock.close()
        except Exception:
            pass
        if getattr(self, "proc", None):
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        shutil.rmtree(self.tmp, ignore_errors=True)


# ---------- document ----------
def load(dir_: str) -> dict:
    f = Path(dir_) / "huazi.json"
    if not f.exists():
        raise SubsError("INPUT_NOT_FOUND", f"{f} not found (run `huazi.py init <video>` first)")
    d = json.loads(f.read_text(encoding="utf-8")); d["_dir"] = str(Path(dir_).resolve())
    return d


def save(d: dict) -> None:
    out = {k: v for k, v in d.items() if not k.startswith("_")}
    (Path(d["_dir"]) / "huazi.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


def template_dir(tid: str) -> Path:
    t = TEMPLATES / tid
    if not (t / "style.css").exists():
        have = ", ".join(sorted(p.name for p in TEMPLATES.iterdir() if (p / "style.css").exists()))
        raise SubsError("INPUT_NOT_FOUND", f"template {tid} not found (have: {have})")
    return t


def rgb(hex_: str) -> tuple[int, int, int]:
    h = hex_.strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise SubsError("UNSUPPORTED_FORMAT", f"brand colour must be 6 hex digits, got {hex_}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def brand_vars(hex_: str) -> dict:
    r, g, b = rgb(hex_)
    mix = lambda c, t, k: round(c + (t - c) * k)  # noqa: E731
    return {"brand": f"{r},{g},{b}",
            "brandLight": f"{mix(r, 255, .45)},{mix(g, 255, .45)},{mix(b, 255, .45)}",
            "brandDeep": f"{mix(r, 0, .45)},{mix(g, 0, .45)},{mix(b, 0, .45)}"}


def guess(o: dict, w: int, h: int) -> dict:
    """An overlays.json entry (genius-footage) → a huazi item with a first-guess type; the agent refines it."""
    parts = [p.strip() for p in o["text"].split("/") if p.strip()]
    bx, by, bw, bh = o.get("box_px") or [w * .1, h * .4, w * .4, h * .15]
    cx = (bx + bw / 2) / w
    align = "left" if cx < 0.42 else "right" if cx > 0.58 else "center"
    fields: dict = {}
    if o.get("cat") == "人名条":
        typ, fields = "name", {"name": parts[0].replace(" ", ""), "role": " ".join(parts[1:])}
    elif len(parts) == 1:
        typ, fields = "title", {"lines": parts}
    elif len(parts) == 2:
        typ, fields = "stack", {"lines": parts}
    else:
        typ, fields = "stack", {"lines": parts[:2], "items": parts[2:]}
    return {"id": o["id"], "source_text": o["text"], "type": typ, "align": align, "y": round(by / h, 3),
            "in": o["in"], "out": o["out"], "fields": fields}


def check_item(it: dict, frames: int) -> list[str]:
    bad = []
    if it.get("type") not in TYPES: bad.append(f"{it.get('id')}: type must be one of {TYPES}")
    if it.get("align") not in ALIGNS: bad.append(f"{it.get('id')}: align must be one of {ALIGNS}")
    if not (0 <= it.get("in", -1) < it.get("out", -1) < frames): bad.append(f"{it.get('id')}: in/out outside the video")
    f = it.get("fields", {})
    if it.get("type") == "name" and not f.get("name"): bad.append(f"{it['id']}: name type needs fields.name")
    if it.get("type") != "name" and not f.get("lines"): bad.append(f"{it['id']}: needs fields.lines")
    if it.get("type") == "number" and not (f.get("number") or {}).get("value"): bad.append(f"{it['id']}: number type needs fields.number.value")
    return bad


def pick(d: dict, ids: str | None) -> list[dict]:
    items = d.get("items") or []
    if ids:
        want = [x.strip() for x in ids.split(",") if x.strip()]
        miss = [x for x in want if x not in {i["id"] for i in items}]
        if miss:
            raise SubsError("INPUT_NOT_FOUND", f"no item {', '.join(miss)} in huazi.json")
        items = [i for i in items if i["id"] in want]
    if not items:
        raise SubsError("INPUT_NOT_FOUND", "no items in huazi.json (add them, or init with --overlays)")
    bad = [m for i in items for m in check_item(i, d["info"]["frames"])]
    if bad:
        raise SubsError("UNSUPPORTED_FORMAT", "; ".join(bad))
    return items


def page(d: dict, it: dict, tid: str, brand: str, work: Path, bg: Path | None = None) -> Path:
    t = template_dir(tid); W, H = d["info"]["width"], d["info"]["height"]
    item = dict(it); item["duration"] = (it["out"] - it["in"] + 1) / d["info"]["fps"]
    spec = {"W": W, "H": H, "safe": d.get("safe", SAFE), "bottomLimit": d.get("bottom_limit", BOTTOM),
            "item": item, "bg": bg.resolve().as_uri() if bg else None, **brand_vars(brand)}
    deco = f'<script src="{(t / "decorate.js").as_uri()}"></script>' if (t / "decorate.js").exists() else ""
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<base href="{ASSETS.as_uri()}/">
<link rel="stylesheet" href="{(ASSETS / 'base.css').as_uri()}">
<link rel="stylesheet" href="{(t / 'style.css').as_uri()}">
<style>html,body{{width:{W}px;height:{H}px}}</style></head>
<body><div id="stage"></div>
<script>window.HZ_SPEC = {json.dumps(spec, ensure_ascii=False)};</script>{deco}
<script src="{(ASSETS / 'runtime.js').as_uri()}"></script></body></html>"""
    p = work / f"{it['id']}_{tid}.html"; p.write_text(html, encoding="utf-8")
    return p


# ---------- commands ----------
def cmd_templates(a) -> None:
    rows = []
    for t in sorted(TEMPLATES.iterdir()):
        mf = t / "meta.json"
        if mf.exists():
            m = json.loads(mf.read_text(encoding="utf-8"))
            rows.append({"id": t.name, "name": m.get("name"), "custom": bool(m.get("custom")),
                         "default_brand": m.get("default_brand"), "description": m.get("description")})
    print(json.dumps(rows, ensure_ascii=False, indent=1))


def cmd_new_template(a) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]*", a.id):
        raise SubsError("UNSUPPORTED_FORMAT", "template id: lowercase letters, digits and hyphens")
    src, dst = template_dir(a.src), TEMPLATES / a.id
    if dst.exists():
        raise SubsError("UNSUPPORTED_FORMAT", f"{dst} exists")
    shutil.copytree(src, dst)
    m = json.loads((dst / "meta.json").read_text(encoding="utf-8"))
    m.update({"id": a.id, "name": a.name or a.id, "custom": True, "based_on": a.src})
    (dst / "meta.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"template": str(dst), "edit": ["style.css", "decorate.js", "meta.json"]}, ensure_ascii=False))


def cmd_init(a) -> None:
    video = Path(a.video).expanduser().resolve()
    if not video.exists():
        raise SubsError("INPUT_NOT_FOUND", f"{video} not found")
    dir_ = Path(a.dir).expanduser().resolve() if a.dir else video.with_name(video.stem + "-huazi")
    if (dir_ / "huazi.json").exists() and not a.force:
        raise SubsError("UNSUPPORTED_FORMAT", f"{dir_ / 'huazi.json'} exists (use --force to overwrite)")
    template_dir(a.template)
    info = probe(video); items = []
    ov = Path(a.overlays).expanduser() if a.overlays else video.with_suffix(".overlays.json")
    if a.overlays and not ov.exists():
        raise SubsError("INPUT_NOT_FOUND", f"{ov} not found")
    if ov.exists():
        o = json.loads(ov.read_text(encoding="utf-8"))
        items = [guess(x, info["width"], info["height"]) for x in o.get("overlays", []) if x.get("cat") in ("花字", "人名条")]
    meta = json.loads((TEMPLATES / a.template / "meta.json").read_text(encoding="utf-8"))
    dir_.mkdir(parents=True, exist_ok=True)
    d = {"version": 1, "video": os.path.relpath(video, dir_), "title": video.stem, "info": info, "template": a.template,
         "brand": (a.brand or meta.get("default_brand") or "1E6BFF").lstrip("#"), "safe": SAFE, "bottom_limit": BOTTOM,
         "items": items, "_dir": str(dir_)}
    rgb(d["brand"]); save(d)
    print(json.dumps({"dir": str(dir_), "items": len(items), "from": str(ov) if ov.exists() else None,
                      "template": a.template, "brand": d["brand"]}, ensure_ascii=False))


def grab(video: Path, n: int, fps: float, out: Path) -> None:
    ffmpeg("-ss", f"{n / fps:.4f}", "-i", video, "-frames:v", "1", "-q:v", "2", out)


def cmd_preview(a) -> None:
    d = load(a.dir); items = pick(d, a.ids)
    tids = [t.strip() for t in (a.template or d["template"]).split(",")]
    brand = (a.brand or d["brand"]).lstrip("#"); rgb(brand)
    video = (Path(d["_dir"]) / d["video"]).resolve(); fps = d["info"]["fps"]
    out_dir = Path(d["_dir"]) / "preview"; work = Path(d["_dir"]) / "work/preview"
    out_dir.mkdir(parents=True, exist_ok=True); work.mkdir(parents=True, exist_ok=True)
    b = Browser(d["info"]["width"], d["info"]["height"]); sheets = []
    try:
        for tid in tids:
            shots = []
            for it in items:
                n = it.get("preview_frame") or it["in"] + round((it["out"] - it["in"]) * 0.6)
                bg = work / f"bg_{it['id']}.jpg"
                if not bg.exists():
                    grab(video, n, fps, bg)
                b.load(page(d, it, tid, brand, work, bg))
                s = work / f"{it['id']}_{tid}.png"; b.shot(min(1.6, (it["out"] - it["in"]) / fps * 0.6), s); shots.append(s)
            sheet = out_dir / f"preview_{tid}.png"
            cols = 2 if len(shots) > 1 else 1
            while len(shots) % cols:
                shots.append(shots[-1])
            if len(shots) == 1:
                shutil.copy(shots[0], sheet)
            else:
                lay ="|".join(f"{'+'.join(['w0'] * (i % cols)) or '0'}_{'+'.join(['h0'] * (i // cols)) or '0'}" for i in range(len(shots)))
                args = [x for s in shots for x in ("-i", s)]
                ffmpeg(*args, "-filter_complex", f"xstack=inputs={len(shots)}:layout={lay}", sheet)
            sheets.append(str(sheet))
    finally:
        b.close()
    print(json.dumps({"sheets": sheets, "items": [i["id"] for i in items], "brand": brand}, ensure_ascii=False))


def cmd_render(a) -> None:
    d = load(a.dir); items = pick(d, a.ids)
    tid = d["template"]; brand = d["brand"]; rgb(brand)
    fmt = a.format or ("hevc" if hevc_alpha() else "prores")
    if fmt == "hevc" and not hevc_alpha():
        raise SubsError("DEPENDENCY_MISSING", "HEVC with alpha needs ffmpeg's hevc_videotoolbox (macOS); use --format prores")
    fps = d["info"]["fps"]; video = (Path(d["_dir"]) / d["video"]).resolve()
    out_dir = Path(d["_dir"]) / "out"; work = Path(d["_dir"]) / "work/render"
    out_dir.mkdir(parents=True, exist_ok=True); work.mkdir(parents=True, exist_ok=True)
    b = Browser(d["info"]["width"], d["info"]["height"]); movs = []
    try:
        for it in items:
            frames = work / it["id"]; shutil.rmtree(frames, ignore_errors=True); frames.mkdir()
            info = b.load(page(d, it, tid, brand, work))
            count = it["out"] - it["in"] + 1; t0 = time.time()
            for k in range(count):
                b.shot(k / fps, frames / f"{k:05d}.png")
            mov = out_dir / f"{it['id']}.mov"
            ffmpeg("-framerate", f"{fps}", "-i", frames / "%05d.png", *ENCODE[fmt], mov)
            shutil.rmtree(frames, ignore_errors=True)
            it["render"] = {"mov": mov.name, "format": fmt, "alpha": ALPHA[fmt],
                            "box": info.get("box") if isinstance(info, dict) else None, "template": tid, "brand": brand}
            movs.append((it, mov)); log(f"{it['id']}: {count} frames in {time.time() - t0:.1f}s")
    finally:
        b.close()
    save(d)
    res = {"movs": [str(m) for _, m in movs], "format": fmt, "alpha": ALPHA[fmt], "template": tid, "brand": brand}
    if not a.no_burn:
        allit = [i for i in d["items"] if (out_dir / f"{i['id']}.mov").exists()]
        out = out_dir / f"{d['title']}_huazi.mp4"; args = ["-i", video]; chain = []; last = "0:v"
        for k, it in enumerate(allit, 1):
            args += ["-i", out_dir / f"{it['id']}.mov"]
            chain.append(f"[{k}:v]setpts=PTS+{it['in'] / fps:.5f}/TB[s{k}]")
            mode = "premultiplied" if (it.get("render") or {}).get("alpha") == "premultiplied" else "straight"
            chain.append(f"[{last}][s{k}]overlay=0:0:alpha={mode}:eof_action=pass:enable='between(n,{it['in']},{it['out']})'[v{k}]"); last = f"v{k}"
        ffmpeg(*args, "-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "0:a?", "-c:v", "libx264", "-crf", "18",
               "-pix_fmt", "yuv420p", "-c:a", "copy", out, timeout=7200)
        res["video"] = str(out)
    alpha_note = "HEVC，预乘透明（premultiplied）" if fmt == "hevc" else "ProRes 4444，直通透明（straight）"
    lines = [f"# {d['title']} 花字清单", "", f"模板 `{tid}` · 品牌色 #{brand} · {d['info']['width']}×{d['info']['height']} · {fps} fps · {alpha_note}", "",
             "| 编号 | 文字 | 入点 | 出点 | 文件 |", "|---|---|---|---|---|"]
    for it in d["items"]:
        f = it.get("fields", {}); txt = f.get("name", "") + (" / " + f["role"] if f.get("role") else "") if it["type"] == "name" else " / ".join(f.get("lines", []))
        mov = (it.get("render") or {}).get("mov", "—")
        lines.append(f"| {it['id']} | {txt} | f{it['in']} | f{it['out']} | {mov} |")
    (out_dir / "huazi.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    res["list"] = str(out_dir / "huazi.md")
    print(json.dumps(res, ensure_ascii=False))


# Browser screenshots carry straight alpha. ProRes 4444 is tagged straight, so frames go in as they are.
# VideoToolbox tags HEVC-with-alpha as premultiplied, so frames are premultiplied first; otherwise
# semi-transparent glows come out too bright in Final Cut / Premiere / QuickTime.
ENCODE = {
    "hevc": ["-vf", "format=rgba,premultiply=inplace=1", "-c:v", "hevc_videotoolbox", "-pix_fmt", "bgra",
             "-alpha_quality", "0.9", "-q:v", "70", "-tag:v", "hvc1"],
    "prores": ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"],
}
ALPHA = {"hevc": "premultiplied", "prores": "straight"}


def hevc_alpha() -> bool:
    return bool(shutil.which("ffmpeg")) and "hevc_videotoolbox" in run(["ffmpeg", "-hide_banner", "-encoders"], check=False).stdout


def font_installed(name: str) -> bool:
    if shutil.which("fc-list"):
        return name in run(["fc-list", ":", "family"], check=False).stdout
    home = Path.home()
    dirs = [home / "Library/Fonts", Path("/Library/Fonts"), Path("C:/Windows/Fonts"), home / "AppData/Local/Microsoft/Windows/Fonts"]
    key = name.replace(" ", "").lower()
    return any(key in p.name.replace(" ", "").lower() for d_ in dirs if d_.exists() for p in d_.iterdir())


def selfcheck() -> None:
    res = {"ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe"), "browser": find_browser()}
    res["prores_ks"] = bool(res["ffmpeg"]) and "prores_ks" in run(["ffmpeg", "-hide_banner", "-encoders"], check=False).stdout
    res["hevc_alpha"] = hevc_alpha()
    res["default_format"] = "hevc (premultiplied alpha)" if res["hevc_alpha"] else "prores 4444 (straight alpha)"
    res["source_han_sans_sc"] = font_installed("Source Han Sans SC")
    res["templates"] = sorted(p.name for p in TEMPLATES.iterdir() if (p / "style.css").exists())
    res["ok"] = bool(res["ffmpeg"] and res["ffprobe"] and res["browser"] and res["prores_ks"])
    if not res["source_han_sans_sc"]:
        res["hint"] = "install Source Han Sans SC (SIL OFL): https://github.com/adobe-fonts/source-han-sans/releases"
    res["os"] = platform.system()
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if not res["ok"]:
        sys.exit(2)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="huazi.py", description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="check ffmpeg (prores_ks), browser, fonts, templates")
    sp = ap.add_subparsers(dest="cmd")
    s = sp.add_parser("templates"); s.set_defaults(fn=cmd_templates)
    s = sp.add_parser("new-template"); s.add_argument("id"); s.add_argument("--from", dest="src", default="t1-light-band")
    s.add_argument("--name"); s.set_defaults(fn=cmd_new_template)
    s = sp.add_parser("init"); s.add_argument("video"); s.add_argument("--dir"); s.add_argument("--overlays")
    s.add_argument("--template", default="t1-light-band"); s.add_argument("--brand"); s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_init)
    s = sp.add_parser("preview"); s.add_argument("dir"); s.add_argument("--ids"); s.add_argument("--template", help="one id or several, comma-separated")
    s.add_argument("--brand"); s.set_defaults(fn=cmd_preview)
    s = sp.add_parser("render"); s.add_argument("dir"); s.add_argument("--ids"); s.add_argument("--no-burn", action="store_true")
    s.add_argument("--format", choices=["hevc", "prores"], help="alpha MOV codec (default hevc on macOS, else prores)")
    s.set_defaults(fn=cmd_render)
    a = ap.parse_args(argv)
    try:
        if a.check:
            selfcheck(); return 0
        if not hasattr(a, "fn"):
            ap.print_help(); return 1
        a.fn(a); return 0
    except SubsError as e:
        print(f"Error [{e.code}]: {e}", file=sys.stderr)
        return EXIT_CODES.get(e.code, 1)


if __name__ == "__main__":
    sys.exit(main())
