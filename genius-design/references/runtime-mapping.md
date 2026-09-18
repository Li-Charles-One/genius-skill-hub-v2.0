# Runtime and Portable Commands

Shared instructions describe capabilities, not universal tool names. Use the tools actually exposed by the host:

| Neutral action | This OpenCode environment | Other runtimes |
| --- | --- | --- |
| Read/search files | `Read`, `Glob`, `Grep` | Native file tools |
| Edit staged document | `Edit`, `Write` | Native edit/write tools |
| Run Python | `Bash` (PowerShell on Windows) | Native command tool |
| Load a needed skill | `Skill` | Verified native skill mechanism |
| Capture a page | Discover available browser tools and their schemas | Verified browser/screenshot tooling |

`agents/openai.yaml` is Codex/UI metadata. OpenCode uses native SKILL.md discovery. Do not invent `functions.read` / `functions.patch` names.

## Dependencies

- Python 3.10+.
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
python -B "$skill/scripts/fetch_design_md.py" linear "$stage/base.md"
python -B "$skill/scripts/extract_design_signals.py" "$stage/page.html" "$stage/capture.json"
# Agent writes $stage/candidate.md with the native edit tool.
python -B "$skill/scripts/lint_design_md.py" "$stage/candidate.md"
python -B "$skill/scripts/design_io.py" "$stage/candidate.md" "$destination"
```

Fetch requires the output path. A destination named `DESIGN.md` is rejected; use `"$stage/base.md"`. Fetch and extraction are optional per workflow. Do not bypass failed validation by copying a candidate over the destination.

`design_io.py` writes `.bak`, `.bak.1`, … beside the destination. Tell the user they exist; they may want those backups gitignored. Do not create a gitignore as part of this workflow.

## Evaluation Commands

```powershell
python -B "<skill-root>/scripts/test_design_tools.py"
python -B "<skill-root>/scripts/lint_design_md.py" "<skill-root>/evals/fixtures/valid-design.md" --json
```

Tests are offline and create temporary files only. Optional test-workspace: `test_design_tools.py --help`.

## Verification Status

Version 3.3.0 is exercised on Windows/Python 3.12. macOS/Linux paths are designed to be portable but remain unverified there. Catalog transport uses per-request timeouts; remote availability is independent of local regression results.
