# genius-design evaluations

Two layers. Do not treat one as the other.

## Script tests

```powershell
python -B "<skill-root>/scripts/test_design_tools.py"
```

```bash
python3 -B "<skill-root>/scripts/test_design_tools.py"
```

Offline. Also runs `evals/evals.json` corpus assertions. A green suite does **not** prove a generated DESIGN.md is good.

Covered: contract lint (including cream/serif/Inter allowed, duplicate H2 fail), `design_io.py` backups and non-file destination, staging safety, core-only H2s, extractor vs script/metadata, computed-style `color_counts`.

## Trigger corpus

`evals.json` concatenates listed files and asserts strings. Keep both should-trigger and should-not-trigger near misses. Do not assert `not_contains: DESIGN.md` on SKILL.md.

Live with-skill vs baseline generation is out of band. Passing lint is structural, not visual or accessibility certification.
