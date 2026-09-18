# genius-design evaluations

Two layers. Do not treat one as the other.

## 1. Deterministic script tests

From any working directory:

```powershell
python -B "<skill-root>/scripts/test_design_tools.py"
python -B "<skill-root>/scripts/lint_design_md.py" "<skill-root>/evals/fixtures/valid-design.md" --json
```

`test_design_tools.py` may take an optional test-workspace directory (`--help`). It creates temporary files only. It also executes `evals/evals.json` file-corpus assertions so a green suite means those strings still match the repo. Covered:

- Output Contract lint: valid fixture passes; keyword-only, illegal dials, duplicate keys, missing fields, and unfilled TODOs fail.
- Cream, serif, Inter, em dashes, two accents, and a centered masthead are not mechanical FAILs.
- `design_io.py` refuses same-path commit, leaves destination and backups untouched on lint failure, numbers `.bak` / `.bak.1` / `.bak.2`, and backs up empty files.
- Fetch refuses a destination named `DESIGN.md` and requires a staged path such as `<staging>/base.md`.
- Core-only lint: required H2 are Design Read, Colors, Typography, Spacing and Shape, Layout, Components. Motion / Imagery / checklist may be omitted when they do not apply. Fixture: `evals/fixtures/minimal-core.md`.
- Extractor distinguishes computed-style captures from CSS/HTML candidates, ignores script and unrelated JSON metadata colors, and records external styles / unresolved `var(...)` / missing states as limitations.

These tests do **not** prove an agent generated a good DESIGN.md.

## 2. Trigger routing and file-corpus checks

`evals/evals.json` is **not** a live generation transcript. Each case concatenates the listed files and asserts strings against that corpus. `trigger_expected` records whether genius-design should load; both should-trigger and should-not-trigger cases are required.

`expected_output` is agent guidance and must match the scripts:

1. Auto fetch order is Refero → Design.md Store → VoltAgent. Pin with `--source` when a single catalog is required.
2. Fetch writes `<staging>/base.md`. Never `DESIGN.md`. Never curl-by-hand. A catalog snapshot is not a delivered spec.
3. Negative triggers (marketing copy, image/video generation, screenshot recognition, one-off button tweaks, writing the page, implementation plans) must not load this skill. Do not assert `not_contains: DESIGN.md` on SKILL.md; that file names DESIGN.md constantly.

Behavior to verify by reading SKILL.md / references, not by string-matching a chat:

1. Heritage brand with cream, serif, two accents, and a centered masthead: preserve those facts.
2. Medical operations UI: work areas, tables, status — no forced marketing hero, image quota, or dark mode.
3. Reverse-engineering: label Observed / Inferred / Recommended; unknown hover/mobile/motion stay unknown.
4. “Change this button to blue” is a negative trigger; do not load this skill for a full DESIGN.md.
5. Deliver through `scripts/design_io.py` after lint; fetch writes a staged catalog snapshot, not a delivered spec.

## Live generation (out of band)

With-skill versus baseline agent generation needs a separate budget and is not part of `test_design_tools.py` or the default `evals.json` runner. Passing lint is structural, not visual or accessibility certification.
