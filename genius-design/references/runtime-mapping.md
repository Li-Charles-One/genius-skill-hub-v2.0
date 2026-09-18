# Runtime and Portable Commands

## Runtime Mapping

Shared instructions describe capabilities, not universal tool names. Use the tools actually exposed by the host:

| Neutral action | This OpenCode environment | Other runtimes |
| --- | --- | --- |
| Read/search files | `functions.read`, `functions.glob`, `functions.grep` | Native file tools |
| Edit staged document | `functions.patch` | Native edit/write tools |
| Run Python | `functions.shell` (PowerShell on Windows) | Native command tool |
| Load a needed skill | `functions.skill` | Verified native skill mechanism |
| Capture a page | Discover available browser tools and their schemas | Verified browser/screenshot tooling |

`agents/openai.yaml` is Codex/UI metadata. OpenCode uses native SKILL.md discovery; no custom adapter YAML is needed to load this skill. Tool names vary across host versions. Do not copy these names into other runtimes or assume an optional browser is installed.

## Dependencies

- Python 3.10+.
- Fetch and extraction use the standard library.
- Lint and validated commit require **PyYAML**. If absent, the command exits unsuccessfully with an actionable message before touching the destination. Do not install it automatically.
- If the user chooses to install it: Windows `python -m pip install PyYAML`; macOS/Linux `python3 -m pip install PyYAML`, using the same interpreter/environment as the commands.

## Resolve Paths

`<skill-root>` is the directory containing the loaded SKILL.md. Script paths resolve there, not in the project. Output paths resolve in the target project. Do not change working directory to the skill root and accidentally save a user's DESIGN.md inside the installed package.

Choose a fresh staging directory under the project or an approved temporary workspace. The names below are examples; avoid reusing a directory with an existing candidate.

### Windows / PowerShell

```powershell
$skill = '<resolved-skill-root>'
$stage = '<fresh-staging-directory>'
$destination = '<project-directory>/DESIGN.md'
python -B "$skill/scripts/fetch_design_md.py" linear "$stage/base.md"
python -B "$skill/scripts/extract_design_signals.py" "$stage/page.html" "$stage/capture.json"
# Agent writes and enriches $stage/candidate.md using the native edit tool.
python -B "$skill/scripts/lint_design_md.py" "$stage/candidate.md"
# Run only after reviewing validation and the human checklist.
python -B "$skill/scripts/design_io.py" "$stage/candidate.md" "$destination"
```

### macOS/Linux / POSIX Shell

```sh
skill='<resolved-skill-root>'
stage='<fresh-staging-directory>'
destination='<project-directory>/DESIGN.md'
python3 -B "$skill/scripts/fetch_design_md.py" linear "$stage/base.md"
python3 -B "$skill/scripts/extract_design_signals.py" "$stage/page.html" "$stage/capture.json"
# Agent writes and enriches the candidate with its native edit tool.
python3 -B "$skill/scripts/lint_design_md.py" "$stage/candidate.md"
# Run only after reviewing validation and the human checklist.
python3 -B "$skill/scripts/design_io.py" "$stage/candidate.md" "$destination"
```

Fetch and extraction are optional per workflow, not commands to run against nonexistent files. Do not bypass failed validation by directly copying a candidate over the destination.

## Evaluation Commands

From any directory, resolve the same skill root:

```powershell
python -B "<skill-root>/scripts/test_design_tools.py"
python -B "<skill-root>/scripts/lint_design_md.py" "<skill-root>/evals/fixtures/valid-design.md" --json
```

Use `python3 -B` on macOS/Linux. Tests are offline and create temporary files only. An optional test-workspace argument is documented by `test_design_tools.py --help`.

## Verification Status

Version 3.0.0 is exercised on Windows/Python 3.12. macOS/Linux paths and standard-library operations are designed to be portable but runtime execution there remains unverified. Catalog transport uses per-request timeouts; remote service availability is independent of local regression results.
