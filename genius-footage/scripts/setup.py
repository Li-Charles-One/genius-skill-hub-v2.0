#!/usr/bin/env python3
"""
One-time setup for genius-footage's shot detection, once per machine: a venv with numpy and onnxruntime, and the
TransNetV2 ONNX model (downloaded from Hugging Face, SHA-256 checked), both in transnet.HOME outside the skill
(~/.local/share/genius-footage, %LOCALAPPDATA%\\genius-footage on Windows, or GENIUS_FOOTAGE_HOME).

    python3 setup.py            # create or repair; safe to rerun
    python3 setup.py --check    # report only

Uses uv when it is on PATH (it brings its own Python 3.12), otherwise this Python's venv and pip; onnxruntime
needs Python 3.10 or newer then. The other scripts switch to the venv by themselves.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import transnet

PACKAGES = ["numpy", "onnxruntime"]


def model_ok() -> bool:
    if not transnet.MODEL.is_file():
        return False
    h = hashlib.sha256()
    with transnet.MODEL.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest() == transnet.MODEL_SHA256


def venv_ok() -> bool:
    py = transnet.venv_python()
    return py.is_file() and subprocess.run([str(py), "-c", "import numpy, onnxruntime"],
                                           capture_output=True).returncode == 0


def make_venv() -> None:
    uv, py = shutil.which("uv"), transnet.venv_python()
    transnet.HOME.mkdir(parents=True, exist_ok=True)
    if uv:
        subprocess.run([uv, "venv", "--python", "3.12", "--allow-existing", str(transnet.VENV)], check=True)
        subprocess.run([uv, "pip", "install", "--python", str(py), *PACKAGES], check=True)
    else:
        if sys.version_info < (3, 10):
            sys.exit("Error [DEPENDENCY_MISSING]: onnxruntime needs Python 3.10 or newer; run setup.py with one, "
                     "or install uv and rerun")
        subprocess.run([sys.executable, "-m", "venv", str(transnet.VENV)], check=True)
        subprocess.run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "-q", *PACKAGES], check=True)


def fetch_model() -> None:
    transnet.MODEL.parent.mkdir(parents=True, exist_ok=True)
    part = transnet.MODEL.with_suffix(".part")
    for url in transnet.MODEL_URLS:
        try:
            print(f"downloading {url}", file=sys.stderr)
            with urllib.request.urlopen(url, timeout=60) as resp, part.open("wb") as out:
                shutil.copyfileobj(resp, out)
        except OSError as e:
            print(f"  failed: {e}", file=sys.stderr)
            continue
        part.replace(transnet.MODEL)
        if model_ok():
            return
        print("  SHA-256 mismatch, trying the next mirror", file=sys.stderr)
    transnet.MODEL.unlink(missing_ok=True)
    part.unlink(missing_ok=True)
    sys.exit("Error [DEPENDENCY_MISSING]: could not download the TransNetV2 model; check the network and rerun")


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up TransNetV2 for genius-footage (.venv and model)")
    parser.add_argument("--check", action="store_true", help="Report only")
    args = parser.parse_args()
    venv, model = venv_ok(), model_ok()
    if not args.check:
        if not venv:
            make_venv()
            venv = venv_ok()
        if not model:
            fetch_model()
            model = model_ok()
    print(f"venv:   {transnet.venv_python() if venv else 'MISSING'}\n"
          f"model:  {transnet.MODEL if model else 'MISSING'}")
    print("ok" if venv and model else "NOT READY (run scripts/setup.py)")
    return 0 if venv and model else 2


if __name__ == "__main__":
    sys.exit(main())
