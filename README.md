# Genius Skill Hub

Personal monorepo for Codex-compatible skills.

This repository is the source hub for reusable skills, local skill mirrors, and lightweight validation before syncing skills into agent runtimes.

## Skills

| Skill | Path | Purpose |
|:--|:--|:--|
| brand-copywriter | `brand-copywriter/` | Advertising, landing page, email, social, and brand copywriting frameworks. |
| cli-creator | `cli-creator/` | Build durable command-line tools from APIs, specs, SDKs, or local scripts. |
| design-md | `design-md/` | Add brand design-system rules for AI coding agents. |
| frontend-design | `frontend-design/` | Build distinctive production-grade frontend interfaces. |
| genius-image | `genius-image/` | Use the Genius Image / GRSai image generation provider when explicitly requested. |
| genius-skill-creator | `genius-skill-creator/` | Create, repair, validate, evaluate, and optimize skills. |
| github-cli | `github-cli/` | Use GitHub CLI for repo, auth, PR, issue, Actions, and API work. |
| mcp-builder | `mcp-builder/` | Build MCP servers for external APIs or services. |
| we-planing | `we-planing/` | WePlaning v2.2 project memory with lifecycle scripts and cross-Agent sync helpers. |
| writing-plans | `writing-plans/` | Write implementation plans before multi-step coding work. |

## Validation

The `validate` GitHub Actions workflow checks skill metadata and runs WePlaning script smoke tests.

Run the same lightweight checks locally before pushing meaningful skill changes:

```powershell
git status --short
node we-planing/scripts/check-memory.cjs <project-root>
node we-planing/scripts/audit-memory.cjs <project-root>
```
