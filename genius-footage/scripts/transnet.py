#!/usr/bin/env python3
"""
TransNetV2 shot-transition probabilities for every decoded frame (ONNX on onnxruntime, CPU).

measure.py writes the frames, 48×27 RGB in decode order, from the same decode it measures; this module only
windows them and runs the model: 100 frames per window, 50 frames apart, the middle 50 kept, the first and
last frame repeated at the ends (as upstream inference does). Per frame it returns two probabilities:
single = the last frame of an outgoing shot (a cut), many = a frame inside a transition (dissolve, fade).

Model: TransNetV2 (Souček & Lokoč 2020, MIT), ONNX export published on Hugging Face. setup.py puts the model
and a venv with numpy and onnxruntime in HOME, a per-machine folder outside the skill: the skill folder may be
synced between machines, and a venv only works on the machine that built it.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

HOME = Path(os.environ.get("GENIUS_FOOTAGE_HOME") or (
    Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "genius-footage" if os.name == "nt"
    else Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "genius-footage"))
MODEL = HOME / "models" / "transnetv2.onnx"
MODEL_SHA256 = "c4d54a682bace32f25136ef83ca2c9d403e8f8193775efeb995172a0d95a8e0c"
MODEL_URLS = ("https://huggingface.co/elya5/transnetv2/resolve/main/transnetv2.onnx",
              "https://huggingface.co/edgetools/transnetv2/resolve/main/transnetv2.onnx")
VENV = HOME / "venv"
W, H = 48, 27
FRAME_BYTES = W * H * 3
WINDOW, STEP, CONTEXT = 100, 50, 25

_lock = threading.Lock()
_session = None


class TransNetError(RuntimeError):
    pass


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def missing() -> str | None:
    """Why TransNetV2 cannot run here, or None when it can."""
    try:
        import numpy  # noqa: F401
        import onnxruntime  # noqa: F401
    except ImportError as e:
        return f"{e.name} is not installed (run scripts/setup.py)"
    if not MODEL.is_file():
        return f"model not found at {MODEL} (run scripts/setup.py)"
    return None


def reexec() -> None:
    """Run the calling script with the venv's Python when this Python lacks numpy / onnxruntime.
    Without the venv the script carries on, and measure.py reports the missing dependency."""
    if os.environ.get("GENIUS_FOOTAGE_VENV"):
        return
    try:
        import numpy  # noqa: F401
        import onnxruntime  # noqa: F401
        return
    except ImportError:
        pass
    py = venv_python()
    if py.is_file():
        env = dict(os.environ, GENIUS_FOOTAGE_VENV="1")
        sys.exit(subprocess.call([str(py), *sys.argv], env=env))


def _sess():
    global _session
    with _lock:
        if _session is None:
            reason = missing()
            if reason:
                raise TransNetError(reason)
            import onnxruntime as ort
            opts = ort.SessionOptions()
            opts.log_severity_level = 3
            _session = ort.InferenceSession(str(MODEL), opts, providers=["CPUExecutionProvider"])
        return _session


def predict_file(path: str | Path) -> tuple[list[float], list[float]]:
    """(single, many) per frame for a raw 48×27 rgb24 file. The file is memory-mapped, so a long clip is
    not held in memory at once."""
    import numpy as np
    size = Path(path).stat().st_size
    n = size // FRAME_BYTES
    if not n:
        return [], []
    frames = np.memmap(path, dtype=np.uint8, mode="r", shape=(n, H, W, 3))
    sess = _sess()
    name = sess.get_inputs()[0].name
    padded = n + 2 * CONTEXT + (STEP - (n % STEP or STEP))  # upstream: 25 + n + (25 + 50 - (n % 50 or 50))
    single, many = [], []
    for ptr in range(0, padded - WINDOW + 1, STEP):
        idx = np.clip(np.arange(ptr - CONTEXT, ptr - CONTEXT + WINDOW), 0, n - 1)
        a, b = sess.run(None, {name: frames[idx].astype(np.float32)[None]})
        single.append(a[0, CONTEXT:CONTEXT + STEP, 0])
        many.append(b[0, CONTEXT:CONTEXT + STEP, 0])
    del frames
    return ([round(float(x), 4) for x in np.concatenate(single)[:n]],
            [round(float(x), 4) for x in np.concatenate(many)[:n]])
