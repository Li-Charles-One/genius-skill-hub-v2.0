#!/usr/bin/env python3
"""出成片，默认 H.265，渲完自动校验并删中间文件。

在 Remotion 工程根目录运行：
    python deliver.py --comp <合成> --out out/<项目>/<名字>-2k-hevc.mov            # 透明，H.265 带 Alpha（默认）
    python deliver.py --comp <合成> --out out/<项目>/<名字>-2k.mp4 --opaque        # 不透明，H.265
    python deliver.py --comp <合成> --out out/<项目>/<名字>-4k-hevc.mov --scale 1.5  # 4K
    python deliver.py --comp <合成> --out out/<项目>/<名字>-2k.mov --format prores   # 用户点名要 ProRes 4444
    python deliver.py --comp demo-main --out out/demo/draft.mp4 --opaque --scale 0.5 --crf 24 --props src/demo/props/draft.json  # 3D 小样
透明：先渲 ProRes 4444 中间文件，预乘 Alpha 后用 macOS 的 hevc_videotoolbox 编码。
不透明：Remotion 直接出 H.265，再改成 hvc1 标签（默认的 hev1 在 QuickTime / 预览里打不开）。
"""
import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"failed: {' '.join(map(str, cmd))}\n{(r.stderr or '')[-2000:]}")
    return r.stdout


def mac_check(swift, out, check, at, want_alpha):
    """用系统解码器解一帧叠灰底；透明成片还要确认带 Alpha 标记。"""
    r = subprocess.run([swift, str(HERE / "check_alpha.swift"), str(out), str(check), at], capture_output=True, text=True)
    print("\n".join(l for l in r.stdout.splitlines() if l.strip()))
    if not check.exists():
        return "系统解码失败（QuickTime / 预览可能打不开）"
    if want_alpha and r.returncode != 0:
        return "透明通道校验失败"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--comp", required=True, help="合成 ID")
    ap.add_argument("--out", required=True, help="成片路径；透明用 .mov，不透明用 .mp4")
    ap.add_argument("--opaque", action="store_true", help="不需要透明通道（自带背景的画面）")
    ap.add_argument("--format", choices=["hevc", "prores"], default="hevc")
    ap.add_argument("--scale", help="渲染缩放，如 1.5 把 2560×1440 合成出成 4K；宽高须为整数")
    ap.add_argument("--props", help="渲染参数 json 文件（3D 项目的小样、无字幕、分层）")
    ap.add_argument("--crf", default="18", help="不透明 H.265 的画质，越小越好越大")
    ap.add_argument("--check-at", default="3", help="校验抽帧的秒数")
    a = ap.parse_args()

    npx, ffmpeg, ffprobe = shutil.which("npx"), shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not (npx and ffmpeg and ffprobe):
        sys.exit("需要 npx、ffmpeg、ffprobe 在 PATH 里")
    if not Path("node_modules/remotion").exists():
        sys.exit("当前目录不是装好依赖的 Remotion 工程")
    if a.format == "hevc" and not a.opaque and platform.system() != "Darwin":
        sys.exit("H.265 带透明需要 macOS 的 hevc_videotoolbox；请改用 --format prores")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    scale = ([f"--scale={a.scale}"] if a.scale else []) + ([f"--props={a.props}"] if a.props else [])
    tmp = out.with_name(out.stem + "-tmp" + (".mp4" if a.opaque else ".mov"))

    if a.format == "prores":
        print(f"render ProRes 4444 -> {out}")
        run([npx, "remotion", "render", a.comp, str(out), "--codec=prores", "--prores-profile=4444",
             "--pixel-format=yuva444p10le", "--image-format=png", "--color-space=bt709", *scale])
    elif a.opaque:
        print(f"render H.265 -> {tmp}")
        run([npx, "remotion", "render", a.comp, str(tmp), "--codec=h265", f"--crf={a.crf}", "--color-space=bt709", *scale])
        run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp), "-c", "copy", "-tag:v", "hvc1", "-movflags", "+faststart", str(out)])
    else:
        print(f"render ProRes 4444 -> {tmp}")
        run([npx, "remotion", "render", a.comp, str(tmp), "--codec=prores", "--prores-profile=4444",
             "--pixel-format=yuva444p10le", "--image-format=png", "--color-space=bt709", *scale])
        print(f"premultiply + HEVC alpha -> {out}")
        run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp),
             "-vf", "format=rgba,premultiply=inplace=1,format=bgra",
             "-c:v", "hevc_videotoolbox", "-alpha_quality", "0.9", "-q:v", "70", "-tag:v", "hvc1", str(out)])

    if a.format == "hevc":
        swift = shutil.which("swift") if platform.system() == "Darwin" else None
        if swift:
            check = out.parent / "stills" / a.comp.lower() / "deliver-check.png"
            check.parent.mkdir(parents=True, exist_ok=True)
            err = mac_check(swift, out, check, a.check_at, want_alpha=not a.opaque)
            if err:
                sys.exit(f"{err}，保留中间文件 {tmp} 以便排查")
        else:
            print("没有 macOS 的 swift，跳过系统解码校验（交付时要说明未验证）")
        tmp.unlink()

    info = json.loads(run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                           "stream=codec_name,codec_tag_string,width,height,r_frame_rate,nb_frames:format=duration,size",
                           "-of", "json", str(out)]))
    s, f = info["streams"][0], info["format"]
    print(f"done: {out}  {s['codec_name']}/{s.get('codec_tag_string', '?')} {s['width']}x{s['height']} {s['r_frame_rate']}fps "
          f"{s.get('nb_frames', '?')} frames {float(f['duration']):.2f}s {int(f['size']) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
