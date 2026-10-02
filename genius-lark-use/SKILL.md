---
name: genius-lark-use
description: "飞书/Lark 统一智能体技能（基于 lark-cli）：处理凭证认证、云文档与多维表格读写、IM 消息收发、日程任务与 OpenAPI 调用。不要用于非飞书第三方服务或纯本地文档编辑。"
metadata:
  version: "1.2.0"
---

# Lark / Feishu Unified CLI Skill

This skill is the single entry point for Lark/Feishu work through the official `lark-cli`. It does not duplicate the upstream `lark-*` skills. It checks the local CLI, routes the request to the right command domain, and reads the official embedded skill (version-matched to the installed binary) only when that domain is needed.

## Load These References

- `references/health-check.md` — diagnosis after a failure: CLI discovery, `doctor`, auth, profile, scope checks, and commands that need approval.
- `references/routing.md` — user intent and URL patterns to `lark-cli` domains and official embedded skills.
- `references/safety.md` — what to confirm before outward-facing or hard-to-reverse actions.
- `references/command-patterns.md` — command shapes, JSON handling, schemas, raw API fallback, error handling.

`evals/evals.json` holds trigger and routing checks; it is not runtime material.

## Core Workflow

1. Confirm it is a Lark/Feishu task. If not, do not use this skill.
2. Do not pre-check the environment. Run the command the task needs; go to `references/health-check.md` only when it fails (command not found, auth, profile, scope) or when the user asks about CLI status.
3. Classify the task with `references/routing.md`, then read the matching official skill before non-trivial work: `lark-cli skills read <skill-name>`.
4. When command details are unclear: `lark-cli <domain> [<command>] --help` or `lark-cli schema <service.resource.method>`.
5. Before any write, apply `references/safety.md`.
6. Prefer structured output (`--format json`) and `--dry-run` where supported.
7. On `_notice`, permission, scope, or auth errors, read `lark-shared` and report the exact next step.

## Operating Principles

- `lark-cli` is the source of truth. Use `lark-cli api` only after checking schema or help; never raw HTTP.
- Do not install, update, log in, or reconfigure `lark-cli` unless the user explicitly asks.
- Do not expose secrets, app credentials, OAuth tokens, or raw sensitive payloads.

## Final Response Contract

Report what was checked or changed; the relevant URL, token, file, chat, event, or record/task count; any confirmation obtained; and any failed or skipped step with its actionable error.
