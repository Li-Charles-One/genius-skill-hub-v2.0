"""
Storyboards: exact frames, labelled with their id (S012a, X03b, X04-7…), tiled into sheets.

Labels are drawn into the pixels with a built-in 5x7 font, so no ffmpeg drawtext / fonts / PIL
are needed. Frames are grabbed by pts, so each cell is exactly the frame the shot list names.
"""

from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CELL = (384, 216)             # cell width, height
COLS, MAX_CELLS = 5, 40       # ~20 shots per sheet at 2 cells each
PAD, SCALE = 6, 3             # white gap between cells; label pixel size
BG, FG, BOX = (255, 255, 255), (255, 220, 0), (0, 0, 0)
RUN_GAP = 12                  # frames this close are decoded by one ffmpeg: a seek costs about 20 decoded frames

FONT = {  # 5x7, '#' = ink
    "0": [" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    "3": ["#####", "   # ", "  #  ", "   # ", "    #", "#   #", " ### "],
    "4": ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
    "5": ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    "6": ["  ## ", " #   ", "#    ", "#### ", "#   #", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    "8": [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
    "9": [" ### ", "#   #", "#   #", " ####", "    #", "   # ", " ##  "],
    "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    "H": ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    "X": ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    "a": ["     ", "     ", " ### ", "    #", " ####", "#   #", " ####"],
    "b": ["#    ", "#    ", "# ## ", "##  #", "#   #", "#   #", "#### "],
    "m": ["     ", "     ", "## # ", "# # #", "# # #", "#   #", "#   #"],
    "-": ["     ", "     ", "     ", "#####", "     ", "     ", "     "],
}


def grab(path: str, seek_times: list[float], fps: float, keys: list[tuple], cell: tuple[int, int] = CELL,
         workers: int = 4) -> dict[tuple, bytes]:
    """{(frame, crop): cell rgb24 bytes, letterboxed} for (frame, crop or None) keys.
    seek_times = measure.frame_times(path, for_seek=True); crop = (x, y, w, h) in source pixels, cut out
    before scaling. Frames within RUN_GAP of each other come from one ffmpeg: it seeks half a frame before
    the first, so the first frame decoded is exactly that one, and the ones after it follow in order."""
    w, h = cell
    size = w * h * 3
    fit = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
    runs = []  # (crop, [frames])
    for crop in dict.fromkeys(c for _, c in keys):
        for f in sorted({f for f, c in keys if c == crop}):
            if runs and runs[-1][0] == crop and f - runs[-1][1][-1] <= RUN_GAP:
                runs[-1][1].append(f)
            else:
                runs.append((crop, [f]))

    def one(run: tuple) -> dict:
        crop, frames = run
        vf = (f"crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]}," if crop else "") + fit
        proc = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, seek_times[frames[0]] - 0.5 / fps):.6f}",
                                 "-i", path, "-map", "0:v:0", "-frames:v", str(frames[-1] - frames[0] + 1),
                                 "-fps_mode", "passthrough", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        out, want = {}, set(frames)
        for f in range(frames[0], frames[-1] + 1):
            data = proc.stdout.read(size)
            if f in want:
                out[(f, crop)] = data if len(data) == size else bytes(size)
        proc.stdout.close()
        proc.wait()
        return out

    with ThreadPoolExecutor(workers) as ex:
        return {k: v for d in ex.map(one, runs) for k, v in d.items()}


def label(cell: bytearray, text: str, width: int) -> None:
    """Draw text into the top-left corner of a cell `width` pixels wide."""
    w, h = (len(text) * 6 + 1) * SCALE, 9 * SCALE
    for y in range(h):
        row = y * width * 3
        cell[row:row + w * 3] = bytes(BOX) * w
    for i, ch in enumerate(text):
        for gy, line in enumerate(FONT[ch]):
            for gx, px in enumerate(line):
                if px != "#":
                    continue
                x0, y0 = (1 + i * 6 + gx) * SCALE, (1 + gy) * SCALE
                for y in range(y0, y0 + SCALE):
                    o = (y * width + x0) * 3
                    cell[o:o + SCALE * 3] = bytes(FG) * SCALE


def sheets(path: str, seek_times: list[float], fps: float, groups: list[tuple[str, list[tuple[str, int]]]],
           out_dir: Path, prefix: str, crops: dict | None = None, cell: tuple[int, int] = CELL,
           cols: int = COLS, per_sheet: int = MAX_CELLS) -> list[tuple[Path, list[str]]]:
    """groups: [(group id, [(cell label, frame), ...])]. A group is never split across sheets.
    crops: {group id: (x, y, w, h)} to show only that part of the frame in the group's cells.
    Returns [(sheet path, [group ids on it])]."""
    crops = crops or {}
    cw, ch = cell
    out_dir.mkdir(parents=True, exist_ok=True)
    pages, cur = [], []
    for g in groups:
        if cur and sum(len(c) for _, c in cur) + len(g[1]) > per_sheet:
            pages.append(cur)
            cur = []
        cur.append(g)
    if cur:
        pages.append(cur)
    pix = grab(path, seek_times, fps, [(f, crops.get(g)) for g, cells in groups for _, f in cells], cell)
    result = []
    for n, page in enumerate(pages, 1):
        cells = [(text, (f, crops.get(g))) for g, c in page for text, f in c]
        rows = (len(cells) + cols - 1) // cols
        sw, sh = cols * cw + (cols + 1) * PAD, rows * ch + (rows + 1) * PAD
        sheet = bytearray(bytes(BG) * (sw * sh))
        for k, (text, key) in enumerate(cells):
            one = bytearray(pix[key])
            label(one, text, cw)
            x0, y0 = PAD + (k % cols) * (cw + PAD), PAD + (k // cols) * (ch + PAD)
            for y in range(ch):
                o = ((y0 + y) * sw + x0) * 3
                sheet[o:o + cw * 3] = one[y * cw * 3:(y + 1) * cw * 3]
        out = out_dir / f"{prefix}_{n:02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{sw}x{sh}",
                        "-i", "-", "-q:v", "3", str(out)], input=bytes(sheet), check=True)
        result.append((out, [gid for gid, _ in page]))
    return result
