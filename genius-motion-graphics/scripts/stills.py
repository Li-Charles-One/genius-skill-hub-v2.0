#!/usr/bin/env python3
"""批量出关键帧：一次打包连续出每帧透明 PNG（render_stills.mjs）→ 铺纯色底预览 JPG → 拼 2 列对照图 contact.jpg。

在 Remotion 工作台根目录运行（Windows / macOS / Linux 通用，需要 node 和 ffmpeg）：
    python stills.py --comp <合成> --frames 8,20,45,90 [--bg 2a2f38] [--scale 1.5] [--project <项目>] [--out <目录>]
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"failed: {' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--comp", required=True, help="合成 ID")
    ap.add_argument("--frames", default="8,20,45,90", help="逗号分隔的帧号")
    ap.add_argument("--bg", default="2a2f38", help="预览底色 hex，深色文字用 ffffff")
    ap.add_argument("--scale", help="渲染缩放，如 1.5 出 4K；宽高须为整数")
    ap.add_argument("--project", help="项目文件夹名；输出到 out/<project>/stills/<comp 小写>")
    ap.add_argument("--out", help="输出目录，覆盖默认位置")
    a = ap.parse_args()

    node, ffmpeg = shutil.which("node"), shutil.which("ffmpeg")
    if not node or not ffmpeg:
        sys.exit("需要 node 和 ffmpeg 在 PATH 里")
    if not Path("node_modules/remotion").exists():
        sys.exit("当前目录不是装好依赖的 Remotion 工作台")

    base = Path("out") / a.project if a.project else Path("out")
    out = Path(a.out) if a.out else base / "stills" / a.comp.lower()
    out.mkdir(parents=True, exist_ok=True)
    frames = [int(f) for f in a.frames.split(",") if f.strip()]
    run([node, str(Path(__file__).resolve().parent / "render_stills.mjs"), "--comp", a.comp, "--out", str(out),
         "--frames", ",".join(map(str, frames)), *(["--scale", a.scale] if a.scale else [])])
    previews = []
    for f in frames:
        png = out / f"f{f}.png"
        jpg = out / f"preview-f{f}.jpg"
        run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=0x{a.bg}:s=16x16", "-i", str(png),
             "-filter_complex", "[0][1]scale2ref[bg][fg];[bg][fg]overlay,scale=1280:-1", "-frames:v", "1", str(jpg)])
        previews.append(jpg)
        print(f"frame {f} -> {png}")

    if len(previews) % 2:
        previews.append(previews[-1])  # 奇数张时补齐一格
    inputs = [arg for p in previews for arg in ("-i", str(p))]
    n = len(previews) // 2
    if n == 1:
        graph = "[0][1]hstack"
    else:
        rows = [f"[{2 * r}][{2 * r + 1}]hstack[r{r}]" for r in range(n)]
        graph = ";".join(rows) + ";" + "".join(f"[r{r}]" for r in range(n)) + f"vstack={n}"
    sheet = out / "contact.jpg"
    run([ffmpeg, "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-frames:v", "1", str(sheet)])
    print(f"contact sheet -> {sheet}")


if __name__ == "__main__":
    main()
