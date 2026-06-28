---
name: lark
description: Unified Lark/Feishu agent skill for operating the official lark-cli. Use when the user asks to check Lark/Feishu CLI status, configure or verify auth, read or write Feishu Docs/Wiki/Drive/Base/Sheets/Slides/Markdown, send or search IM messages, manage calendars/tasks/mail/approvals/meetings/OKR/attendance, or route any Lark OpenAPI task. Do not use for non-Lark services or local-only document editing unless the user wants to publish/import it into Lark/Feishu.
---

# Lark / Feishu Unified CLI Skill

This skill is the single entry point for Lark/Feishu work through the official `lark-cli`. It does not duplicate every upstream `lark-*` skill. Instead, it checks the local CLI, routes the request to the right command domain, and reads the official embedded skill content only when that domain is needed.

## Load These References

- `references/health-check.md` for CLI discovery, `doctor`, auth, profile, and scope checks.
- `references/routing.md` for mapping user intent to `lark-cli` domains and official embedded skills.
- `references/safety.md` for confirmation rules before outward-facing or hard-to-reverse actions.
- `references/command-patterns.md` for common command shapes, JSON handling, schemas, and fallback patterns.
- `evals/evals.json` contains representative trigger and routing prompts.

## Core Workflow

1. Identify whether the task is a Lark/Feishu task. If it is not, do not use this skill.
2. For every new session or uncertain environment, run the checks in `references/health-check.md` before operational commands.
3. Classify the task using `references/routing.md`.
4. Read the matching official embedded skill before non-trivial domain work:
   - `lark-cli skills read lark-doc`
   - `lark-cli skills read lark-drive`
   - `lark-cli skills read lark-base`
   - or the domain-specific skill named in `references/routing.md`.
5. Use `lark-cli <domain> --help`, `lark-cli <domain> <command> --help`, or `lark-cli schema <service.resource.method>` when command details are unclear.
6. Before actions that send, publish, delete, overwrite, approve, reject, move, expose, or batch-modify data, apply `references/safety.md` and get user confirmation unless the user has already given explicit approval for that exact action.
7. Prefer structured output when useful: `--format json`, `--format table`, `--page-all`, and `--dry-run` where supported.
8. If the CLI output contains `_notice`, permission errors, scope errors, or auth problems, route to `lark-shared` guidance and report the exact next step.
9. Summarize results plainly. Include created URLs, object IDs/tokens, counts changed, skipped items, and any failed commands.

## Operating Principles

- Use the official `lark-cli` as the source of truth. Do not call Lark/Feishu APIs directly unless using `lark-cli api` after checking the relevant schema or OpenAPI guidance.
- Keep reads low-risk and fast. Ask for confirmation before write operations with external impact.
- Do not install, update, or reconfigure `lark-cli` unless the user explicitly asks.
- Do not expose secrets, app credentials, OAuth tokens, or raw sensitive payloads in the final answer.
- When unsure which domain owns a request, inspect the URL path/token pattern and use `lark-cli skills read lark-openapi-explorer` only after checking the obvious domain skills.

## Final Response Contract

For completed Lark work, report:

- What was checked or changed.
- The relevant Lark/Feishu URL, token, file name, chat name, calendar event, record count, or task count.
- Any confirmation that was required and obtained.
- Any failed or skipped step, with the actionable error message.
