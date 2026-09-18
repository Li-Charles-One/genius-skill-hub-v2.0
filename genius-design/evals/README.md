# genius-design evaluations

Two layers. Do not treat one as the other.

## Deterministic script tests

From any working directory:

```powershell
python -B "<skill-root>/scripts/test_design_tools.py"
python -B "<skill-root>/scripts/lint_design_md.py" "<skill-root>/evals/fixtures/valid-design.md" --json
```

`test_design_tools.py` may take an optional test-workspace directory (`--help`). It creates temporary files only. Covered:

- Output Contract v1 lint: valid fixture passes; keyword-only, illegal dials, duplicate keys, missing fields, and unfilled TODOs fail.
- Cream, serif, Inter, em dashes, two accents, and a centered masthead are not mechanical FAILs.
- `design_io.py` refuses same-path commit, leaves destination and backups untouched on lint failure, numbers `.bak` / `.bak.1` / `.bak.2`, and backs up empty files.
- Extractor distinguishes computed-style captures from CSS/HTML candidates, ignores script and unrelated JSON metadata colors, and records external styles / unresolved `var(...)` / missing states as limitations.

These tests do **not** prove an agent generated a good DESIGN.md.

## Trigger and routing evals

`evals/evals.json` lists should-trigger and near-miss prompts. Assertions check bundled files and script contracts, not a live generation transcript.

Behavior the skill is supposed to follow (verify by reading SKILL.md / references, not by string-matching a chat):

1. Heritage brand with cream, serif, two accents, and a centered masthead: preserve those facts.
2. Medical operations UI: work areas, tables, status — no forced marketing hero, image quota, or dark mode.
3. Reverse-engineering: label Observed / Inferred / Recommended; unknown hover/mobile/motion stay unknown.
4. “Change this button to blue” is a negative trigger; do not load this skill for a full DESIGN.md.
5. Deliver through `scripts/design_io.py` after lint; fetch writes a staged catalog snapshot, not a delivered spec.

## Not run by default

Old-versus-new agent generation comparison needs a separate budget and is not part of `test_design_tools.py`. Passing lint is structural, not visual or accessibility certification.
