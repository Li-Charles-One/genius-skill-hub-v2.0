# Runtime and Portable Commands

Shared instructions describe capabilities, not universal tool names. Use the tools actually exposed by the host:

| Neutral action | Use |
| --- | --- |
| Read/search files | Native file read/search tools |
| Edit staged document | Native edit/write tools |
| Run Python | Native shell/command tool (PowerShell on Windows) |
| Load a needed skill | The host's native skill mechanism |
| Fetch HTTP URL | The host's native fetch/web tool |
| Capture a page | Discover available browser tools and their schemas |

`agents/openai.yaml` is Codex/UI metadata; other hosts use native SKILL.md discovery. Do not invent tool names the host does not expose.

## Dependencies

- Python 3.9+.
- Fetch and extraction use the standard library.
- Lint and validated commit require **PyYAML**. If absent, the command exits unsuccessfully with an actionable message before touching the destination. Do not install it automatically.
- If the user chooses to install it: Windows `python -m pip install PyYAML`; macOS/Linux `python3 -m pip install PyYAML`, using the same interpreter as the commands.

## Resolve Paths

`<skill-root>` is the directory containing the loaded SKILL.md. Scripts resolve there. Output paths resolve in the target project. Do not save a user's DESIGN.md inside the installed package.

Choose a fresh staging directory under the project or an approved temporary workspace.

Use `python` on Windows and `python3` on macOS/Linux. Always pass `-B`.

```powershell
$skill = '<resolved-skill-root>'
$stage = '<fresh-staging-directory>'
$destination = '<project-directory>/DESIGN.md'
# Mode A (optional): fetch VoltAgent raw into $stage/catalog-evidence.md — never as the candidate
# Mode B (optional): extract signals from local capture
python -B "$skill/scripts/extract_design_signals.py" "$stage/page.html" "$stage/capture.json"
# Agent writes $stage/candidate.md with the native edit tool.
python -B "$skill/scripts/lint_design_md.py" "$stage/candidate.md"
python -B "$skill/scripts/design_io.py" "$stage/candidate.md" "$destination"
```

```bash
skill='<resolved-skill-root>'
stage='<fresh-staging-directory>'
destination='<project-directory>/DESIGN.md'
# Mode A (optional): fetch VoltAgent raw into "$stage/catalog-evidence.md" — never as the candidate
# Mode B (optional): extract signals from local capture
python3 -B "$skill/scripts/extract_design_signals.py" "$stage/page.html" "$stage/capture.json"
# Agent writes $stage/candidate.md with the native edit tool.
python3 -B "$skill/scripts/lint_design_md.py" "$stage/candidate.md"
python3 -B "$skill/scripts/design_io.py" "$stage/candidate.md" "$destination"
```

Path B capture format and HTML/CSS-only fallback: `references/evidence.md`.

Extraction is optional per workflow. Do not bypass failed validation by copying a candidate over the destination.

`design_io.py` writes `.bak`, `.bak.1`, … beside the destination after a successful commit. Tell the user they exist; they may want those backups gitignored. Do not create a gitignore as part of this workflow. Lint failure does not write backups. If the destination path exists and is not a file, the command exits with an error and writes nothing.

## Evaluation Commands

```powershell
python -B "<skill-root>/scripts/test_design_tools.py"
python -B "<skill-root>/scripts/lint_design_md.py" "<skill-root>/evals/fixtures/valid-design.md" --json
```

```bash
python3 -B "<skill-root>/scripts/test_design_tools.py"
python3 -B "<skill-root>/scripts/lint_design_md.py" "<skill-root>/evals/fixtures/valid-design.md" --json
```

Tests are offline and create temporary files only. Optional test-workspace: `test_design_tools.py --help`.

## Verification Status

The scripts are exercised on Windows/Python 3.12 and macOS/Python 3.9 (test suite, extractor, lint, safe commit). Linux variants follow the same POSIX commands but are unverified. Reference snapshots use the host HTTP tool when requested.
