---
name: genius-code-audit
description: Evidence-backed code audit skill for diff reviews and full repository reviews. Use for code audit, security-focused review, pre-release review, architecture assessment, "Linus review", PR risk review, or Chinese requests such as dai ma shen ji and quan mian shen cha. Supports Codex and Reasonix through separate agent metadata.
---

# Genius Code Audit

Use this skill for serious code review where correctness, data integrity, security, concurrency, and architecture matter. Do not use it for casual style nits or broad refactoring advice.

## Runtime Model

This package is shared by Codex and Reasonix:

- Codex uses this `SKILL.md` plus `agents/openai.yaml`.
- Reasonix uses the same audit instructions plus `agents/reasonix.yaml`.
- Shared workflow details live in `references/audit-workflow.md`.
- Report structure lives in `references/report-format.md`.
- The report template lives in `assets/audit-report-template.html`.

Keep runtime-specific metadata out of this file. If a runtime needs fields such as `run_as`, `model`, or `allowed_tools`, put them under `agents/`.

## Mode Selection

If the user asks for a PR review, diff review, branch review, or asks what changed, use **diff mode**. If no base is given, compare against `origin/main..HEAD` when available.

If the user asks for full audit, deep review, codebase health check, security-focused review, architecture assessment, code audit, or does not specify a diff scope, use **full mode**.

If the repository, base range, or mode is ambiguous and the wrong choice would change the audit scope materially, ask one concise question before proceeding.

## Workflow

1. Read `references/audit-workflow.md`.
2. Determine mode and scope.
3. Run the required evidence-gathering commands for that mode.
4. Inspect files, callers, data flows, and risky patterns before writing findings.
5. Use `assets/audit-report-template.html` and `references/report-format.md` to create a self-contained HTML report in the workspace root, outside the audited git repo when possible.
6. Run `scripts/validate-audit-report.cjs <report.html>`.
7. Report the issue counts, report path, and any scope caveats.

## Required Standards

- Findings must cite verified file paths and specific code evidence.
- Every bug finding must explain what breaks, not just what looks ugly.
- Prefer fewer high-confidence findings over many speculative ones.
- Always distinguish missing implementation from implemented-but-wrong behavior.
- Security quick scans are mandatory in both modes.
- If no issues are found, say so directly and include remaining scope limitations.

## Output

Return a short summary in chat and save the full HTML report. The chat response should include:

- audit mode and scope;
- fatal, severe, fix, suggestion, and architecture counts;
- report path;
- validation result from `scripts/validate-audit-report.cjs`;
- any residual risk or skipped scope.
