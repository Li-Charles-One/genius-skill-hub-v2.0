---
name: genius-design
description: "Generate production-grade DESIGN.md brand design systems with deep anti-slop rules. Three workflows: (A) pick from 73 brand templates, (B) reverse-engineer a live website, or (C) let the agent infer a design direction from your product type. Trigger keywords: 逆向, 品牌, UI设计, 设计规范, DESIGN.md, reverse engineer, brand, design system, 风格. Do not use for marketing copy or image/video generation."
license: Apache-2.0
metadata:
  version: "2.0.0"
  hermes:
    tags: [design-system, brand, DESIGN.md, anti-slop, frontend, UI, landing-page, template, reverse-engineer]
    related_skills: [taste-skill, impeccable]
---

# Genius Design

Produce a rich, anti-slop `DESIGN.md` an agent can follow. Every file needs: brief inference, three-dial values, semantic tokens, category anti-patterns, refusal rules, and the 12-item pre-ship checklist.

## Brief Inference (all workflows)

Read the room first: page kind, vibe words, reference URLs, audience, existing brand assets, quiet constraints (a11y, public-sector, regulated).

State one line before acting:

> Reading this as: [page kind] for [audience], with a [vibe] language, leaning toward [system or family].

Ask at most one clarifying question, and only if the read genuinely forks. If the user already gave a URL, skip the path question and go to Workflow B.

Otherwise ask A / B / C:

- **A. Brand template** — pick from 73 brands
- **B. Reverse-engineer** — URL in, DESIGN.md out
- **C. AI recommendation** — product type in, direction out

## Dials

Every DESIGN.md sets `DESIGN_VARIANCE`, `MOTION_INTENSITY`, `VISUAL_DENSITY` (1-10). Baseline for a landing page: **7 / 6 / 4**. Inference table and how dials gate layout/motion/density: `reference/dials-and-stack.md`.

Honesty map (official package vs aesthetic-only) and code-stack defaults live in the same file.

## Workflows

Details: `reference/workflows.md`. After the base file exists, run `reference/enrichment.md`.

- **A:** recommend 2-3 catalog brands from the Design Read, fetch with `python scripts/fetch_design_md.py <brand> ./DESIGN.md`, then enrich.
- **B:** fetch the page (Firecrawl if available), extract tokens with semantic roles, write from `reference/design-template.md`, then enrich.
- **C:** reason register / vibe / dials / system / closest brands, then fetch-and-adapt or generate from the template, then enrich.

If `./DESIGN.md` exists, tell the user before overwrite and back up to `./DESIGN.md.bak`.

Brand list, font substitutions, selection guide: `reference/catalog.md`. Refusals: `reference/refusals.md`. Category anti-patterns: `reference/anti-patterns.md`. Checklist: `reference/preflight-checklist.md`.

## Delivery

Tell the user: key decisions (color, type, vibe, dials), save path `./DESIGN.md`, what was inferred, what they may override.

## Gotchas

- One official design system per project. Do not mix Fluent with Carbon.
- Do not invent DESIGN.md tokens that recreate a system you should have installed.
- This skill writes DESIGN.md. It does not write marketing copy or generate images.

## Resource Map

- `reference/design-template.md`
- `reference/anti-patterns.md`
- `reference/preflight-checklist.md`
- `reference/dials-and-stack.md`
- `reference/refusals.md`
- `reference/enrichment.md`
- `reference/workflows.md`
- `reference/catalog.md`
- `scripts/fetch_design_md.py`
- Fork: https://github.com/Li-Charles-One/awesome-design-md
- Upstream: https://github.com/VoltAgent/awesome-design-md
