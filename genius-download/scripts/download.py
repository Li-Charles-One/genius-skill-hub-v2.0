#!/usr/bin/env python3
"""
Genius Download — video links (or share messages with one) → local mp4 files.

抖音 / 小红书: the RedFox API first (REDFOX_API_KEY), then yt-dlp (小红书, link must carry xsec_token), then the
logged-in ego browser; every other site: yt-dlp. Routes, measurements and why not simpler: references/routes.md.

Usage:
    python3 download.py <link|share message> [...] [--dir DIR] [--jobs N] [--cookies-from-browser chrome]
                        [--output text|json]
    python3 download.py --check

Failures print `Error [CODE]: ...` and exit with EXIT_CODES[CODE]; with --output json each item carries its error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

DEFAULT_DIR = "~/Downloads/genius-download"
EXIT_CODES = {"INPUT_NOT_FOUND": 3, "UNSUPPORTED_FORMAT": 4, "DEPENDENCY_MISSING": 5, "PROVIDER_ERROR": 6, "TIMEOUT": 7}


class DownloadError(RuntimeError):
    """Failure carrying an error code (EXIT_CODES)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


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

BROWSER_SITES = r"https?://([\w-]+\.)?(douyin\.com|iesdouyin\.com|xiaohongshu\.com|xhslink\.com)/"
# Runs in ego-browser's Node.js: open the page, find the real video URL, save it from the page (its cookies go along).
BROWSER_JS = r"""
const task = await taskSpace(__NAME__);
const page = task.page("p1");
let res = {};
try {
  let url = __URL__, vid = __VID__;
  if (/douyin\.com/.test(url)) {
    // A fresh tab opening /video/<id> gets sent to another video; the 精选 player opens the right one.
    // Its <video> plays a blob:, so take the file URL the player requests, tagged __vid=<id>.
    if (!vid) {
      await page.goto(url, { timeout: 45000 });
      const u = await page.url();
      vid = (u.match(/\/video\/(\d+)/) || u.match(/modal_id=(\d+)/) || [])[1];
      if (!vid) throw new Error("找不到视频 ID：" + u);
    }
    await page.cdp("Network.enable", {});
    await page.events();
    await page.goto("https://www.douyin.com/jingxuan?modal_id=" + vid, { timeout: 45000 });
    let src = null;
    for (let k = 0; k < 30 && !src; k++) {
      await page.waitForTimeout(1000);
      src = (await page.events()).filter((e) => e.method === "Network.requestWillBeSent").map((e) => e.params.request.url)
        .find((u) => /douyinvod\.com|\/aweme\/v1\/play/.test(u) && u.includes("__vid=" + vid));
    }
    const wall = await page.evaluate(() => !!document.querySelector("[class*=login-container], [class*=verify], #captcha_container"));
    if (!src) res = { error: wall ? "wall" : "no-video", url: await page.url() };
    else {
      const r = await page.fetch(src, { saveAs: __PART__, timeout: 300000 });
      const title = await page.evaluate(() => document.title);
      res = r.ok ? { title, url: "https://www.douyin.com/video/" + vid } : { error: "HTTP " + r.status };
    }
  } else {
    // 小红书: the note data in the page has the file (its <video> plays a blob:)
    await page.goto(url, { timeout: 45000 });
    await page.waitForFunction(() => Object.keys(window.__INITIAL_STATE__?.note?.noteDetailMap || {}).length, undefined,
      { timeout: 25000 }).catch(() => {});
    const info = await page.evaluate(() => {
      const m = window.__INITIAL_STATE__?.note?.noteDetailMap || {};
      const note = Object.values(m).map((x) => x?.note).find((n) => n?.video) || {};
      const all = Object.values(note.video?.media?.stream || {}).flat().filter((x) => x?.masterUrl);
      return { src: all.sort((a, b) => (b.height || 0) - (a.height || 0))[0]?.masterUrl, title: note.title || document.title,
               url: location.href, wall: !!document.querySelector("[class*=login-container], [class*=verify]") };
    });
    if (!info.src) res = { error: info.wall ? "wall" : "no-video", url: info.url };
    else {
      const r = await page.fetch(info.src, { saveAs: __PART__, timeout: 300000 });
      res = r.ok ? { title: info.title, url: info.url } : { error: "HTTP " + r.status, url: info.url };
    }
  }
} catch (e) { res = { error: String(e?.message || e).slice(0, 300) }; }
await task.finish({ keep: [] });
console.log("@@RESULT " + JSON.stringify(res));
"""


def _safe(title: str, limit: int = 60) -> str:
    t = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", re.sub(r"\s*[-|]\s*(抖音|小红书|小紅書)\s*$", "", title)).strip() or "video"
    while len(t.encode("utf-8")) > limit:
        t = t[:-1]
    return t


def _video_id(url: str) -> str | None:
    m = re.search(r"/(?:video|note|explore|discovery/item|search_result)/([0-9a-f]{24}|\d{15,})", url)
    return m.group(1) if m else None


def fetch_browser(url: str, out_dir: Path) -> str:
    """抖音 / 小红书: the logged-in ego browser opens the page and saves the video it plays."""
    exe = shutil.which("ego-browser")
    if not exe:
        raise DownloadError("DEPENDENCY_MISSING", "抖音、小红书要用 ego 浏览器下载：先装 ego lite（ego-browser 技能）")
    vid = _video_id(url)
    old = list(out_dir.glob(f"* [{vid}].mp4")) if vid else []
    if old:
        return str(old[0])
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = hashlib.sha1(f"{url}{os.getpid()}{threading.get_ident()}".encode()).hexdigest()[:8]
    part = out_dir / f".part-{tag}.mp4"
    js = (BROWSER_JS.replace("__NAME__", json.dumps(f"genius-download {tag}"))
          .replace("__URL__", json.dumps(url)).replace("__VID__", json.dumps(vid))
          .replace("__PART__", json.dumps(str(part.resolve()))))
    print(f"[genius-download] downloading {url} in the ego browser…", file=sys.stderr)
    try:
        p = subprocess.run([exe, "nodejs"], input=js, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired as e:
        part.unlink(missing_ok=True)
        raise DownloadError("TIMEOUT", f"浏览器下载超过 10 分钟：{url}") from e
    line = next((x for x in reversed((p.stdout + "\n" + p.stderr).splitlines()) if "@@RESULT " in x), None)
    res = json.loads(line.split("@@RESULT ", 1)[1]) if line else {"error": (p.stderr or p.stdout).strip()[-300:]}
    landed = _video_id(res.get("url") or "") or (re.search(r"modal_id=(\d+)", res.get("url") or "") or [None, None])[1]
    if vid and landed and landed != vid:  # the site sent us to another video: this one is gone or private
        res = {"error": f"视频打不开（被删、不公开或需要权限），网站跳到了 {res.get('url')}"}
    if res.get("error") or not part.is_file() or not part.stat().st_size:
        part.unlink(missing_ok=True)
        err = res.get("error", "no file")
        hint = "：在 ego 浏览器里登录这个网站（或过验证）后重跑" if err == "wall" else ""
        raise DownloadError("PROVIDER_ERROR", f"浏览器下载失败 {url}：{err}{hint}")
    out = out_dir / f"{_safe(res.get('title') or '')} [{_video_id(res.get('url') or '') or vid or tag}].mp4"
    part.replace(out)
    print(f"[genius-download] downloaded → {out}", file=sys.stderr)
    return str(out)


REDFOX = "https://redfox.hk/story/api/parseWork/videoDownload/"


def fetch_redfox(text: str, url: str, out_dir: Path) -> str | None:
    """抖音 / 小红书 via the RedFox API (REDFOX_API_KEY, about ¥0.03 a call): it returns the video file URL.
    text may be a whole share message; it is sent as-is. None when no key or on failure (a fallback follows)."""
    key = _env("REDFOX_API_KEY")
    if not key:
        return None
    vid = _video_id(url)
    old = list(out_dir.glob(f"* [{vid}].mp4")) if vid else []
    if old:
        return str(old[0])
    site = "douyin" if re.search(r"douyin\.com/", url) else "xhs"
    print(f"[genius-download] downloading {url} via RedFox…", file=sys.stderr)
    req = urllib.request.Request(REDFOX + site, data=json.dumps({"url": text}).encode("utf-8"), method="POST",
                                 headers={"REDFOX_API_KEY": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"[genius-download] RedFox failed ({e}), falling back…", file=sys.stderr)
        return None
    data = res.get("data") or {}
    src = data.get("videoUrl") or next((x.get("downloadUrl") for x in data.get("resources") or []
                                        if x.get("type") == "video" and x.get("downloadUrl")), None)
    if res.get("code") != 2000 or not src:
        print(f"[genius-download] RedFox: code {res.get('code')} {res.get('msg') or res.get('message') or ''}"
              f"{'' if src else '（没有视频）'}, falling back…", file=sys.stderr)
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = vid or hashlib.sha1(text.encode()).hexdigest()[:10]
    part = out_dir / f".part-{tag}.mp4"
    try:
        dl = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0", "Referer": f"https://www.{'douyin' if site == 'douyin' else 'xiaohongshu'}.com/"})
        with urllib.request.urlopen(dl, timeout=600) as r, open(part, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 20)
    except Exception as e:
        part.unlink(missing_ok=True)
        print(f"[genius-download] RedFox file download failed ({e}), falling back…", file=sys.stderr)
        return None
    out = out_dir / f"{_safe(data.get('title') or (data.get('desc') or '').split(chr(10))[0])} [{tag}].mp4"
    part.replace(out)
    print(f"[genius-download] downloaded → {out}", file=sys.stderr)
    return str(out)


def fetch(text: str, out_dir: Path, cookies: str | None = None) -> str:
    """A link (or a share message with one) → a local mp4, kept in out_dir. 抖音 / 小红书: RedFox first, then
    the logged-in ego browser (抖音) or yt-dlp and the browser (小红书, needs xsec_token); other sites yt-dlp."""
    m = re.search(r"https?://[^\s，。！]+", text)
    if not m:
        raise DownloadError("INPUT_NOT_FOUND", f"没有找到链接：{text[:80]}")
    url = m.group(0)
    browser = re.match(BROWSER_SITES, url)
    if browser:
        got = fetch_redfox(text, url, out_dir)
        if got:
            return got
    if re.match(r"https?://(www\.)?xiaohongshu\.com/", url) and "xsec_token=" not in url:
        raise DownloadError("UNSUPPORTED_FORMAT", f"小红书链接要带 xsec_token（从搜索结果或分享里复制完整链接），"
                                                 f"不带时网站不给看这条笔记：{url}")
    if browser and "xiaohongshu.com/" not in url:  # 抖音 (and xhslink short links) go straight to the browser
        return fetch_browser(url, out_dir)
    exe = shutil.which("yt-dlp")
    if not exe:
        raise DownloadError("DEPENDENCY_MISSING", "链接需要 yt-dlp：brew install yt-dlp")
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "--no-playlist", "--no-progress", "-f", "bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b",
           "--merge-output-format", "mp4", "-o", str(out_dir / "%(title).60B [%(id)s].%(ext)s"),
           "--print", "after_move:filepath"] + (["--cookies-from-browser", cookies] if cookies else [])
    print(f"[genius-download] downloading {url}…", file=sys.stderr)
    try:
        p = subprocess.run(cmd + [url], capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired as e:
        raise DownloadError("TIMEOUT", f"下载超过 30 分钟：{url}") from e
    path = (p.stdout.strip().splitlines() or [""])[-1]
    if p.returncode or not Path(path).is_file():
        if browser:
            print(f"[genius-download] yt-dlp failed, trying the ego browser…", file=sys.stderr)
            return fetch_browser(url, out_dir)
        raise DownloadError("PROVIDER_ERROR", f"下载失败 {url}：{p.stderr.strip()[-300:]}")
    print(f"[genius-download] downloaded → {path}", file=sys.stderr)
    return path


# ── CLI ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Genius Download: video links → local mp4 (B 站, 抖音, 小红书, YouTube…)")
    parser.add_argument("links", nargs="*", help="Links, or whole share messages containing one")
    parser.add_argument("--dir", default=DEFAULT_DIR, help=f"Where files go (default {DEFAULT_DIR})")
    parser.add_argument("--jobs", "-j", type=int, default=4, help="Links at once (default 4)")
    parser.add_argument("--cookies-from-browser", default=None, help="yt-dlp cookies for links that need a login (chrome, safari…)")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    parser.add_argument("--check", action="store_true", help="Show yt-dlp, the RedFox key and the ego browser")
    args = parser.parse_args()
    if args.check:
        ytdlp = shutil.which("yt-dlp")
        print(f"yt-dlp:       {ytdlp or 'not installed (B 站 / YouTube / other sites unsupported)'}\n"
              f"redfox:       key={'yes' if _env('REDFOX_API_KEY') else 'no (抖音 / 小红书 via the ego browser)'}\n"
              f"ego-browser:  {shutil.which('ego-browser') or 'not installed'}\n"
              f"dir:          {Path(args.dir).expanduser()}")
        print("ok" if ytdlp else "NOT READY")
        sys.exit(0 if ytdlp else 2)
    if not args.links:
        parser.error("at least one link is required (unless --check)")
    out_dir = Path(args.dir).expanduser()

    def one(text: str) -> dict:
        try:
            return {"input": text, "path": fetch(text, out_dir, args.cookies_from_browser)}
        except DownloadError as e:
            return {"input": text, "error": {"code": e.code, "message": str(e)}}

    with ThreadPoolExecutor(max(1, min(args.jobs, len(args.links)))) as ex:
        results = list(ex.map(one, args.links))
    if args.output == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("\n".join(f"已下载：`{r['path']}`" if "path" in r else f"Error [{r['error']['code']}]: {r['error']['message']}"
                        for r in results))
    errs = [r["error"] for r in results if "error" in r]
    for e in errs:
        print(f"Error [{e['code']}]: {e['message']}", file=sys.stderr)
    if errs:
        sys.exit(EXIT_CODES.get(errs[0]["code"], 1))


if __name__ == "__main__":
    main()
