# Genius Skill Hub

Personal monorepo for Codex-compatible skills.

This repository is the source hub for reusable skills, local skill mirrors, and lightweight validation before syncing skills into agent runtimes.

## Skills

| Skill | Path | Purpose |
|:--|:--|:--|
| brainstorming | `brainstorming/` | Explore intent and design before complex multi-file work; optional browser-based Visual Companion. |
| brand-copywriter | `brand-copywriter/` | Advertising, landing page, email, social, and brand copywriting frameworks. |
| cli-creator | `cli-creator/` | Build durable command-line tools from APIs, specs, SDKs, or local scripts. |
| genius-code-audit | `genius-code-audit/` | Run diff or full code audits with Codex and Reasonix adapters. |
| genius-design | `genius-design/` | Brand design systems for AI: pick from prebuilt DESIGN.md templates, or reverse-engineer a site into one. |
| genius-image | `genius-image/` | Use the Genius Image / GRSai image generation provider when explicitly requested. |
| genius-skill-creator | `genius-skill-creator/` | Create, repair, validate, evaluate, and optimize skills. |
| genius-vision | `genius-vision/` | Universal image and video analysis (OCR, UI review, chart data, video summary) via the doubao vision API. |
| github-cli | `github-cli/` | Use GitHub CLI for repo, auth, PR, issue, Actions, and API work. |
| mcp-builder | `mcp-builder/` | Build MCP servers for external APIs or services. |
| we-planing | `we-planing/` | WePlaning v2.2 project memory with lifecycle scripts and cross-Agent sync helpers. |
| writing-plans | `writing-plans/` | Write implementation plans before multi-step coding work. |

## Skill Pipeline

For complex multi-step work, three skills compose into a pipeline:

```
brainstorming  →  writing-plans  →  implementation  →  we-planing
   (WHAT/WHY)      (HOW)              (do the work)     (record state)
```

- `brainstorming` triggers only when the complexity gate fires (3+ files AND ambiguous approach), or when the user explicitly asks to plan. It outputs a design spec.
- `writing-plans` always follows brainstorming for architectural work and turns the spec into an implementation plan.
- `we-planing` records session state in `.agent-memory/` whenever durable changes happen during implementation.
- The other skills (`brand-copywriter`, `cli-creator`, `genius-code-audit`, `genius-design`, `genius-image`, `genius-skill-creator`, `genius-vision`, `github-cli`, `mcp-builder`) are leaf skills — they do their own job and don't sit in this pipeline.

## Validation

The `validate` GitHub Actions workflow checks skill metadata and runs WePlaning script smoke tests.
It also parses agent YAML metadata and smoke-tests the Genius Code Audit report validator.

Run the same lightweight checks locally before pushing meaningful skill changes:

```powershell
git status --short
node we-planing/scripts/check-memory.cjs <project-root>
node we-planing/scripts/audit-memory.cjs <project-root>
```
