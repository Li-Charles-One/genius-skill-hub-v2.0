#!/usr/bin/env python3
"""Validate a DESIGN.md candidate and atomically promote it to the destination."""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path


def _same_file(left: Path, right: Path) -> bool:
    a = left.expanduser().resolve()
    b = right.expanduser().resolve()
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def unique_backup_path(path: Path) -> Path:
    backup = path.with_name(path.name + ".bak")
    n = 1
    while backup.exists():
        backup = path.with_name(f"{path.name}.bak.{n}")
        n += 1
    return backup


def unique_backup(path: Path) -> Path | None:
    """Copy path to a unique sibling backup. None if path does not exist."""
    if not path.exists() or not path.is_file():
        return None
    data = path.read_bytes()
    backup = unique_backup_path(path)
    backup.write_bytes(data)
    return backup


def atomic_write_bytes(dest: Path, data: bytes) -> None:
    """Write data onto dest via a same-directory temp file and os.replace."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f"{dest.name}.{uuid.uuid4().hex}.tmp")
    written = False
    try:
        with open(tmp, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        written = True
        os.replace(tmp, dest)
    except BaseException:
        if not written:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def atomic_replace(src: Path, dest: Path) -> None:
    atomic_write_bytes(dest, src.read_bytes())


def _lint_candidate(candidate: Path) -> int:
    lint = Path(__file__).resolve().parent / "lint_design_md.py"
    proc = subprocess.run(
        [sys.executable, str(lint), str(candidate)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdout:
        sys.stdout.write(proc.stdout)
        if not proc.stdout.endswith("\n"):
            sys.stdout.write("\n")
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        if not proc.stderr.endswith("\n"):
            sys.stderr.write("\n")
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print("Usage: design_io.py <candidate> <destination>")
        return 0
    if len(args) != 2:
        print("Usage: design_io.py <candidate> <destination>", file=sys.stderr)
        return 2

    candidate = Path(args[0])
    destination = Path(args[1])
    if _same_file(candidate, destination):
        print(
            "Candidate and destination must be different files.",
            file=sys.stderr,
        )
        return 1
    if not candidate.is_file():
        print(f"Candidate not found: {candidate}", file=sys.stderr)
        return 1

    lint_code = _lint_candidate(candidate)
    if lint_code != 0:
        return lint_code if lint_code > 0 else 1

    backup = unique_backup(destination)
    atomic_replace(candidate, destination)
    print(destination.resolve())
    if backup is not None:
        print(backup.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
