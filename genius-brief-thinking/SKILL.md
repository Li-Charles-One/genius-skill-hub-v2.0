---
name: genius-brief-thinking
description: "在开发复杂功能前探索用户真实意图、头脑风暴并输出设计简报（Brief/Spec），为实现计划做准备。不要用于范围清晰的微小改动、重命名或已有明确解法的 Bug 修复。"
license: MIT
metadata:
  version: "2.1.1"
  hermes:
    tags: [planning, design, spec, brief, brainstorming, architecture, requirements]
    related_skills: [genius-impl-plans]
---

# Genius Brief Thinking

This skill produces a **brief**: what to build and why. `genius-impl-plans` defines how, and is the only next skill.

Run when the user asks to brainstorm or make a brief. A request for an implementation plan goes to `genius-impl-plans`; so does a complete spec with settled goals, constraints, and acceptance criteria. Speak in briefs, not brainstorming ritual.

## Complexity Gate

Require a brief when **both** are true:

- The work touches 3+ files or adds a new feature/component
- The approach is ambiguous (multiple valid approaches, costly if wrong)

Skip when intent is clear even across many files (rename X to Y), scope is 1-2 files (bug fix, config, simple addition), or there is one obvious approach. A single-file fix does not need a design phase.

## Speed Tiers

### Lite (default)

Use when the question is "which of 2-3 approaches?" not "what are we building?"

1. State 2-3 approaches — one sentence each plus trade-off
2. Recommend one — one-line reason
3. Get the user's pick; write a short brief only if they want it on disk

No spec review loop. No visual companion. One message if possible.

### Full

Use only when the user asks for an in-depth brief, or the work is architectural (new service, data model, or integration).

1. Explore project context — files, docs, recent commits, existing patterns
2. If the request is several independent subsystems, decompose; each gets its own brief → plan → implementation cycle
3. If upcoming questions are visual, offer the companion (see below)
4. Ask clarifying questions — one per message, multiple choice when possible, focused on purpose, constraints, success criteria
5. Propose 2-3 approaches with trade-offs, leading with your recommendation. If one approach is clearly right, explain why and proceed
6. Present the design in sections scaled to complexity (architecture, components, data flow, error handling, testing); get approval as you go. Small units with one purpose, existing codebase patterns, no refactors beyond the goal. YAGNI
7. Write `specs/YYYY-MM-DD-<topic>-design.md` (or the user's path)
8. Review it with `spec-document-reviewer-prompt.md` (max 5 loops), then ask the user to read the file; edit and re-review on requested changes

## Brief Format

Every saved brief uses these minimum sections, with requirements numbered `R1`, `R2`, …:

```markdown
## Problem
## Goal
## Non-goals
## Requirements
- R1: ...
## Decision
## Success Criteria
## Open Questions
```

## Stop Rule

Both tiers end at the brief. Picking an approach is not permission to code, and do not `git commit` unless asked. After the user approves (handoff state `BRIEF_APPROVED`), offer `genius-impl-plans` — never jump to implementation.

## Visual Companion

Optional, Full tier only. Use when seeing beats reading (mockups, layouts, diagrams); a UI topic is not automatically visual. Details: `visual-companion.md`. If `scripts/` is missing, stay in the terminal.

Companion files: `scripts/server.cjs`, `scripts/frame-template.html`, `scripts/helper.js`, `scripts/start-server.sh`, `scripts/stop-server.sh`. Trigger checks: `evals/evals.json`.
