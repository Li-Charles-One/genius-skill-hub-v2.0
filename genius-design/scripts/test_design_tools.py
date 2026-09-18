#!/usr/bin/env python3
"""Offline regressions for genius-design scripts. Temporary files only."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "evals" / "fixtures"
PY = sys.executable
VALID = FIXTURES / "valid-design.md"
INVALID = FIXTURES / "invalid-unfilled.md"
CAPTURE = FIXTURES / "capture.json"


def run(script: Path, args: list[str], *, cwd: Path, extra_py: list[str] | None = None):
    cmd = [PY, *list(extra_py or []), "-B", str(script), *args]
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run offline genius-design script regressions"
    )
    parser.add_argument(
        "workspace",
        nargs="?",
        help="Optional directory for temporary test files (created if missing)",
    )
    args = parser.parse_args(argv)

    if args.workspace:
        workspace = Path(args.workspace)
        workspace.mkdir(parents=True, exist_ok=True)
        cleanup_workspace = False
    else:
        workspace = Path(tempfile.mkdtemp(prefix="genius-design-test-"))
        cleanup_workspace = True

    foreign = Path(tempfile.mkdtemp(prefix="genius-design-cwd-"))
    fails: list[str] = []

    def ok(name: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"ok    {name}")
        else:
            fails.append(f"{name}: {detail}".rstrip())
            print(f"FAIL  {name}  {detail}")

    try:
        sys.path.insert(0, str(SCRIPTS))
        from design_io import unique_backup, unique_backup_path

        lint = SCRIPTS / "lint_design_md.py"
        io_script = SCRIPTS / "design_io.py"
        extract = SCRIPTS / "extract_design_signals.py"

        proc = run(lint, [str(VALID)], cwd=foreign)
        ok("lint valid fixture", proc.returncode == 0, proc.stdout + proc.stderr)

        proc = run(lint, [str(VALID), "--json"], cwd=foreign)
        payload = {}
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            payload = {"_error": str(exc)}
        ok(
            "lint valid json",
            proc.returncode == 0 and payload.get("ok") is True and payload.get("fails") == [],
            proc.stdout,
        )

        proc = run(lint, [str(INVALID)], cwd=foreign)
        ok("lint unfilled template", proc.returncode == 1, proc.stdout)

        fake = workspace / "fake.md"
        fake.write_text("anti-patterns checklist DESIGN_VARIANCE page rhythm\n", encoding="utf-8")
        proc = run(lint, [str(fake)], cwd=foreign)
        ok("lint keyword-only", proc.returncode == 1 and "FAIL" in proc.stdout, proc.stdout)

        dial = workspace / "dial-999.md"
        text = VALID.read_text(encoding="utf-8").replace(
            "DESIGN_VARIANCE: 6", "DESIGN_VARIANCE: 999"
        )
        dial.write_text(text, encoding="utf-8")
        proc = run(lint, [str(dial)], cwd=foreign)
        ok("lint dial 999", proc.returncode == 1, proc.stdout)

        boolean_dial = workspace / "dial-true.md"
        boolean_dial.write_text(
            VALID.read_text(encoding="utf-8").replace(
                "DESIGN_VARIANCE: 6", "DESIGN_VARIANCE: true"
            ),
            encoding="utf-8",
        )
        proc = run(lint, [str(boolean_dial)], cwd=foreign)
        ok("lint boolean dial", proc.returncode == 1, proc.stdout)

        dup = workspace / "dup.md"
        dup.write_text(
            VALID.read_text(encoding="utf-8").replace(
                "name: Hearth Folio Seasonal Landing",
                "name: Hearth Folio Seasonal Landing\nname: duplicate",
                1,
            ),
            encoding="utf-8",
        )
        proc = run(lint, [str(dup)], cwd=foreign)
        ok("lint duplicate key", proc.returncode == 1 and "duplicate" in proc.stdout.lower(), proc.stdout)

        cream = workspace / "cream-dash.md"
        cream.write_text(
            VALID.read_text(encoding="utf-8").replace(
                "The positive direction is an editorial title page",
                "The positive direction is an editorial title page — cream #f5f1ea, Inter is allowed when named",
                1,
            ),
            encoding="utf-8",
        )
        proc = run(lint, [str(cream)], cwd=foreign)
        ok(
            "lint cream dash Inter allowed",
            proc.returncode == 0,
            proc.stdout + proc.stderr,
        )

        proc = run(lint, [str(workspace / "missing.md")], cwd=foreign)
        ok("lint missing file", proc.returncode == 1, proc.stdout)

        proc = run(lint, [str(VALID)], cwd=foreign, extra_py=["-S"])
        ok(
            "lint missing PyYAML",
            proc.returncode == 2 and "pip install PyYAML" in (proc.stderr + proc.stdout),
            proc.stderr + proc.stdout,
        )

        dest = workspace / "DESIGN.md"
        proc = run(io_script, [str(VALID), str(VALID)], cwd=foreign)
        ok("commit same path", proc.returncode != 0, proc.stderr)

        dest.write_text("ORIGINAL", encoding="utf-8")
        proc = run(io_script, [str(INVALID), str(dest)], cwd=foreign)
        ok(
            "commit lint failure preserves dest",
            proc.returncode != 0
            and dest.read_text(encoding="utf-8") == "ORIGINAL"
            and not dest.with_name("DESIGN.md.bak").exists(),
            proc.stdout + proc.stderr,
        )

        empty = workspace / "empty.md"
        empty.write_bytes(b"")
        first = unique_backup(empty)
        first_ok = first is not None and first.name == "empty.md.bak" and first.stat().st_size == 0
        empty.write_text("v2", encoding="utf-8")
        empty.with_name("empty.md.bak").write_bytes(b"keep-bak")
        empty.with_name("empty.md.bak.1").write_bytes(b"keep-bak-1")
        second = unique_backup(empty)
        ok(
            "unique numbered backups including empty",
            first_ok
            and second is not None
            and second.name == "empty.md.bak.2"
            and second.read_text(encoding="utf-8") == "v2"
            and empty.with_name("empty.md.bak").read_bytes() == b"keep-bak",
            f"first={first} second={second}",
        )
        ok(
            "next backup path skips existing",
            unique_backup_path(empty).name == "empty.md.bak.3",
            unique_backup_path(empty).name,
        )

        delivered = workspace / "out" / "DESIGN.md"
        delivered.parent.mkdir(parents=True, exist_ok=True)
        delivered.write_text("previous", encoding="utf-8")
        proc = run(io_script, [str(VALID), str(delivered)], cwd=foreign)
        ok(
            "commit success",
            proc.returncode == 0
            and delivered.read_text(encoding="utf-8") == VALID.read_text(encoding="utf-8")
            and delivered.with_name("DESIGN.md.bak").read_text(encoding="utf-8") == "previous",
            proc.stdout + proc.stderr,
        )

        proc = run(extract, [str(CAPTURE)], cwd=foreign)
        cap = {}
        try:
            cap = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            cap = {"_error": str(exc)}
        computed = [
            row
            for row in cap.get("signals", [])
            if row.get("source") == "computed-style"
            and row.get("selector") == "main h1"
            and row.get("state") == "default"
        ]
        ok(
            "extract computed capture",
            proc.returncode == 0 and computed and isinstance(computed[0].get("viewport"), dict),
            proc.stdout[:500],
        )

        html = workspace / "page.html"
        html.write_text(
            """<!doctype html><html><head>
<link rel="stylesheet" href="https://example.com/app.css">
<style>.btn { color: #112233; background: var(--missing); }</style>
</head><body><script>const x = "#ff00aa";</script></body></html>
""",
            encoding="utf-8",
        )
        proc = run(extract, [str(html)], cwd=foreign)
        html_payload = {}
        try:
            html_payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            html_payload = {"_error": str(exc)}
        counts = html_payload.get("color_counts", {})
        limits = " ".join(html_payload.get("limitations", []))
        externals = [item.get("url") for item in html_payload.get("external_stylesheets", [])]
        ok(
            "extract html vs script",
            proc.returncode == 0
            and "#112233" in counts
            and "#ff00aa" not in counts
            and any("app.css" in (url or "") for url in externals)
            and "var(--missing)" in limits,
            proc.stdout[:800],
        )

        meta = workspace / "export.json"
        meta.write_text(
            json.dumps({"id": "pack", "meta": {"brandColor": "#abcdef"}, "notes": "color #abcdef"}),
            encoding="utf-8",
        )
        proc = run(extract, [str(meta)], cwd=foreign)
        meta_payload = {}
        try:
            meta_payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            meta_payload = {"_error": str(exc)}
        ok(
            "extract ignores metadata hex",
            proc.returncode == 0 and "#abcdef" not in meta_payload.get("color_counts", {}),
            proc.stdout[:500],
        )

        proc = run(extract, [str(workspace / "nope.css")], cwd=foreign)
        ok("extract missing file", proc.returncode == 1, proc.stderr)
    except Exception as exc:  # noqa: BLE001 — report and fail the suite
        fails.append(f"suite exception: {exc}")
        print(f"FAIL  suite exception  {exc}")
    finally:
        if str(SCRIPTS) in sys.path:
            try:
                sys.path.remove(str(SCRIPTS))
            except ValueError:
                pass
        shutil.rmtree(foreign, ignore_errors=True)
        if cleanup_workspace:
            shutil.rmtree(workspace, ignore_errors=True)

    if fails:
        print(f"{len(fails)} failure(s).")
        return 1
    print("All genius-design script tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
