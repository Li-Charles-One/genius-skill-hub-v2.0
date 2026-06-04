# Audit Workflow

## Principle

Audit code as evidence, not vibes. Every issue should be tied to a concrete file path, a specific behavior, and a realistic failure mode.

Use direct language, but do not let style replace proof. The report can be blunt; the findings still need to be correct.

## Mode A: Diff Audit

Use diff mode for PRs, branch reviews, commit ranges, or "what did this change break?" prompts.

Recommended commands:

```powershell
git status --short --branch
git diff --stat origin/main..HEAD
git diff origin/main..HEAD
git log --oneline origin/main..HEAD
```

If the user supplies a base range, use that range instead of `origin/main..HEAD`.

Required inspection:

- Read every changed file with more than 20 changed lines.
- For smaller changes, read at least the containing function, class, or module.
- Trace callers of changed exported functions or public APIs.
- Check whether changed data formats, file paths, API shapes, or persistence behavior are consumed outside the diff.
- State the diff-mode limitation in the report: unchanged code outside the traced call paths may not have been fully audited.

## Mode B: Full Audit

Use full mode for deep review, pre-release audit, security review, architecture assessment, codebase health check, or broad code audit requests.

Recommended exploration:

```powershell
git status --short --branch
rg --files
rg -n "TODO|FIXME|HACK|throw new Error|catch|eval\\(|innerHTML|dangerouslySetInnerHTML|password|TOKEN|SECRET|API_KEY|apiKey"
```

Required inspection:

- Map the top-level project structure before reading details.
- Identify the storage/data layer and read it fully.
- Trace one complete user-visible flow end to end: input, state transition, persistence, readback, and error path.
- Read asynchronous boundaries such as timers, event listeners, queues, background tasks, subscriptions, promises, and effects.
- Check all catch blocks for swallowed errors or inconsistent state after failure.
- Look for fake implementation: functions that look wired but return constants, empty arrays, mocks, or unvalidated assumptions.

## Mandatory Quick Scans

Run quick scans in every audit. Adapt the file globs to the project language.

Security and secrets:

```powershell
rg -n "API_KEY|SECRET|TOKEN|password|apiKey|private_key|BEGIN .*PRIVATE" .
```

Dangerous execution/rendering:

```powershell
rg -n "eval\\(|Function\\(|innerHTML|dangerouslySetInnerHTML|exec\\(|spawn\\(|system\\(" .
```

Path and file handling:

```powershell
rg -n "path\\.join|path\\.resolve|\\.\\./|writeFile|readFile|Remove-Item|rm -rf" .
```

Silent failure:

```powershell
rg -n "catch\\s*\\{|catch \\([^)]*\\) \\{\\s*\\}|return null|return \\[\\]|console\\.error" .
```

If a scan is clean, note it. If it hits, inspect the relevant code before filing an issue.

## Priority Order

1. Data integrity: corruption, loss, partial writes, stale reads, silent overwrite.
2. Security: injection, path traversal, secret exposure, auth bypass, XSS/CSRF.
3. Concurrency: races, lock gaps, overlapping async, TOCTOU, multi-writer conflicts.
4. Resource management: leaked listeners, handles, URLs, sockets, intervals, quota.
5. Error handling: swallowed failures, inconsistent state after catch, missing rollback.
6. Performance pathology: avoidable hot-path O(n^2), repeated serialization, render cascades.
7. Architecture and clarity: dependency inversion, duplicated types, god objects, dead tests, fake abstractions.

## Severity

Use these classes exactly because the HTML template and validator depend on them:

| Class | Meaning |
|:--|:--|
| `fatal` | Data loss/corruption, exploitable security hole, fake functionality that deceives users. |
| `severe` | Deterministic race, guaranteed leak, broken workflow, or failure on a major supported environment. |
| `fix` | Real bug or silent failure with plausible user impact. |
| `suggest` | Minor but real issue such as fragile comparison, avoidable work, or missing recovery signal. |
| `arch` | Architecture debt that makes future defects likely but is not itself an immediate bug. |

## Runtime Notes

Codex:

- Prefer `rg`, `git`, and direct file reads.
- Use PowerShell-compatible commands in Windows workspaces.
- Save the report outside the audited repo when possible.

Reasonix:

- Use `directory_tree`, `read_file`, `search_content`, `glob`, `get_symbols`, and `run_command`.
- Use `write_file` for the final HTML report.
- Use the tool list from `agents/reasonix.yaml`.

## Anti-Patterns

- Do not report speculative issues without a failure path.
- Do not flood the report with style preferences.
- Do not confuse "not implemented yet" with "implemented incorrectly".
- Do not invent line numbers. If exact lines are unavailable, cite the file and symbol.
- Do not hide uncertainty. Mark scope caveats explicitly.
