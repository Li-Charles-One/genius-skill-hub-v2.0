# Cross-Platform Command Standard

Use this standard when a skill contains scripts, install commands, shell snippets, validation commands, or runbook steps. The default target is Windows, macOS, and Linux.

## Decision Order

1. Prefer a Python or Node script for repeated logic.
2. Use repo-relative paths inside scripts.
3. Use shell commands only for simple orchestration or one-off examples.
4. Provide separate Windows PowerShell and macOS/Linux Bash variants when syntax differs.
5. State which operating systems were actually tested. Mark the rest as unverified.

## Script Rules

- Use Python or Node path libraries instead of hardcoded separators.
- Keep script inputs explicit: `script <skill-dir>` is better than depending on the current directory.
- Avoid local absolute paths in reusable package files. If a local path is unavoidable in a report, mark it `local-only`.
- Do not require Bash on Windows unless the skill explicitly targets Git Bash, WSL, or MSYS2.
- Do not require PowerShell on macOS/Linux unless the skill explicitly targets PowerShell Core.
- Keep generated files deterministic and avoid hidden network calls unless the skill purpose requires them.

## Command Rules

When commands differ by OS, show both forms:

```powershell
python .\scripts\quick_validate.py .\my-skill
```

```bash
python3 ./scripts/quick_validate.py ./my-skill
```

Use PowerShell for Windows examples:

- quote paths that may contain spaces with single quotes;
- avoid Bash heredocs;
- do not rely on `&&` as the only separator;
- prefer separate commands or a PowerShell script block for multi-step examples.

Use Bash for macOS/Linux examples:

- quote paths that may contain spaces with single quotes;
- use `python3` when the environment may not map `python` to Python 3;
- avoid GNU-only flags unless Linux is the only target.

## Path Rules

- In package docs, prefer repo-relative paths such as `genius-skill-creator/scripts/quick_validate.py`.
- In scripts, use `pathlib.Path` for Python or `node:path` for Node.
- In YAML adapters, keep paths relative to the skill folder.
- In final reports, include absolute paths only when reporting the actual local machine state.

## Validation Reporting

Report validation with OS scope:

```text
Validation:
- Windows: passed `python scripts/quick_validate.py genius-skill-creator`
- macOS: unverified
- Linux: unverified
```

If a command is portable by construction but not executed on an OS, say `expected portable; unverified on <OS>` instead of claiming it passed.

## Common Fixes

| Risk | Better pattern |
|:--|:--|
| Bash heredoc in Windows instructions | PowerShell here-string or checked-in script |
| Hardcoded `C:\...` inside reusable docs | repo-relative path plus local-only note in final report |
| `rm -rf` in cross-platform docs | script-backed cleanup or OS-specific variants |
| shell parsing JSON/YAML with text filters | Python/Node parser |
| one command only shown for all OSes | split PowerShell and Bash when syntax differs |
