"""
Storyboards: exact frames, labelled with their id (S012a, X03b…), tiled into sheets.

Labels are drawn into the pixels with a built-in 5x7 font, so no ffmpeg drawtext / fonts / PIL
are needed. Frames are grabbed by pts, so each cell is exactly the frame the shot list names.
"""

from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CELL_W, CELL_H = 384, 216
COLS, MAX_CELLS = 5, 40       # ~20 shots per sheet at 2 cells each
PAD, SCALE = 6, 3             # white gap between cells; label pixel size
BG, FG, BOX = (255, 255, 255), (255, 220, 0), (0, 0, 0)

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
    "X": ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    "a": ["     ", "     ", " ### ", "    #", " ####", "#   #", " ####"],
    "b": ["#    ", "#    ", "# ## ", "##  #", "#   #", "#   #", "#### "],
    "m": ["     ", "     ", "## # ", "# # #", "# # #", "#   #", "#   #"],
}


def grab(path: str, seek_times: list[float], fps: float, frames: list[int], workers: int = 4) -> dict[int, bytes]:
    """{frame: CELL_W x CELL_H rgb24 bytes}, letterboxed. seek_times = measure.frame_times(path, for_seek=True).
    Seeks half a frame early so the first frame decoded at or after the seek point is exactly the requested one."""
    vf = (f"scale={CELL_W}:{CELL_H}:force_original_aspect_ratio=decrease,"
          f"pad={CELL_W}:{CELL_H}:(ow-iw)/2:(oh-ih)/2")

    def one(f: int) -> tuple[int, bytes]:
        t = max(0.0, seek_times[f] - 0.5 / fps)
        out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.6f}", "-i", path, "-map", "0:v:0",
                              "-frames:v", "1", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True).stdout
        return f, out if len(out) == CELL_W * CELL_H * 3 else bytes(CELL_W * CELL_H * 3)

    with ThreadPoolExecutor(workers) as ex:
        return dict(ex.map(one, sorted(set(frames))))


def _label(cell: bytearray, text: str) -> None:
    w, h = (len(text) * 6 + 1) * SCALE, 9 * SCALE
    for y in range(h):
        row = y * CELL_W * 3
        cell[row:row + w * 3] = bytes(BOX) * w
    for i, ch in enumerate(text):
        for gy, line in enumerate(FONT[ch]):
            for gx, px in enumerate(line):
                if px != "#":
                    continue
                x0, y0 = (1 + i * 6 + gx) * SCALE, (1 + gy) * SCALE
                for y in range(y0, y0 + SCALE):
                    o = (y * CELL_W + x0) * 3
                    cell[o:o + SCALE * 3] = bytes(FG) * SCALE


def sheets(path: str, seek_times: list[float], fps: float, groups: list[tuple[str, list[tuple[str, int]]]],
           out_dir: Path, prefix: str) -> list[tuple[Path, list[str]]]:
    """groups: [(group id, [(cell label, frame), ...])]. A group is never split across sheets.
    Returns [(sheet path, [group ids on it])]."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pages, cur = [], []
    for g in groups:
        if cur and sum(len(c) for _, c in cur) + len(g[1]) > MAX_CELLS:
            pages.append(cur)
            cur = []
        cur.append(g)
    if cur:
        pages.append(cur)
    pix = grab(path, seek_times, fps, [f for _, cells in groups for _, f in cells])
    result = []
    for n, page in enumerate(pages, 1):
        cells = [(label, f) for _, c in page for label, f in c]
        rows = (len(cells) + COLS - 1) // COLS
        sw, sh = COLS * CELL_W + (COLS + 1) * PAD, rows * CELL_H + (rows + 1) * PAD
        sheet = bytearray(bytes(BG) * (sw * sh))
        for k, (label, f) in enumerate(cells):
            cell = bytearray(pix[f])
            _label(cell, label)
            x0, y0 = PAD + (k % COLS) * (CELL_W + PAD), PAD + (k // COLS) * (CELL_H + PAD)
            for y in range(CELL_H):
                o = ((y0 + y) * sw + x0) * 3
                cell_row = y * CELL_W * 3
                sheet[o:o + CELL_W * 3] = cell[cell_row:cell_row + CELL_W * 3]
        out = out_dir / f"{prefix}_{n:02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{sw}x{sh}",
                        "-i", "-", "-q:v", "3", str(out)], input=bytes(sheet), check=True)
        result.append((out, [gid for gid, _ in page]))
    return result
