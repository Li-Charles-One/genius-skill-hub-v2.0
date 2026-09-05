---
name: genius-brief-thinking
description: Explore intent and produce a design brief before implementing complex features. Use for genius-brief-thinking, brainstorm, plan, or ambiguous multi-approach tasks. Outputs a brief/spec, then hands off to genius-impl-plans. Do not use for clear-scope work such as renames, bugfixes, or one obvious approach.
license: MIT
metadata:
  version: "2.0.0"
  hermes:
    tags: [planning, design, spec, brief, brainstorming, architecture, requirements]
    related_skills: [genius-impl-plans]
---

# Genius Brief Thinking

This skill produces a **brief**: what to build and why. `genius-impl-plans` defines how. They are sequential. See the repository-level [`WORKFLOW.md`](../WORKFLOW.md) for the shared handoff states. If the user already knows what they want, skip this skill and go to `genius-impl-plans`. Do not write implementation details here.

`brainstorm` and `plan` are trigger words only. Speak in briefs, not brainstorming ritual.

Help turn ideas into a brief through collaborative dialogue. Survey the project, ask questions one at a time, then present the design and get approval.

## Complexity Gate

Require a brief when **both** are true:

- The work touches 3+ files or adds a new feature/component
- The approach is ambiguous (multiple valid approaches, costly if wrong)

Skip when:

- Intent is clear even across many files (rename X to Y)
- Scope is 1-2 files (bug fix, config, simple addition)
- There is one obvious approach

Always run when the user asks to brainstorm, plan, or make a brief.

Survey existing patterns before proposing designs.

## Anti-Pattern

A single-file bug fix, a config change, or a straightforward utility does not need a 9-step design phase.

## Speed Tiers

### Lite (default)

Use when the question is "which of 2-3 approaches?" not "what are we building?"

1. State 2-3 approaches — one sentence each plus trade-off
2. Recommend one — one-line reason
3. Get the user's pick
4. Stop. Write a short brief if they want it on disk. If they want an implementation plan, invoke `genius-impl-plans`. Do not start coding.

No spec review loop. No visual companion. One message if possible.

### Full

Use only when the user says to plan it out, or the work is architectural (new service, data model, or integration).

1. Explore project context — files, docs, recent commits
2. If upcoming questions are visual, offer the companion in `visual-companion.md`
3. Ask clarifying questions — one at a time
4. Propose 2-3 approaches with trade-offs and a recommendation
5. Present the design in sections; get approval as you go
6. Write `specs/YYYY-MM-DD-<topic>-design.md` (or the user's preferred path). Do not commit unless asked
7. Review the spec with `spec-document-reviewer-prompt.md` (max 5 loops), then ask the user to read the file
8. After they approve, invoke `genius-impl-plans` only

**Default to Lite.**

The terminal state is `genius-impl-plans`. Do not start implementation from this skill.

## Process

**Understanding the idea:**

- Check current project state first
- If the request is several independent subsystems, decompose first. Each sub-project gets its own brief → plan → implementation cycle
- Ask one question per message. Prefer multiple choice. Focus on purpose, constraints, success criteria

**Exploring approaches:**

- Propose 2-3 approaches with trade-offs
- Lead with your recommendation and why

**Presenting the design:**

- Scale each section to its complexity
- Cover architecture, components, data flow, error handling, testing
- Design small units with one purpose and clear interfaces
- Follow existing codebase patterns. Only include refactors that serve this goal

## Brief Format

Every saved brief uses these minimum sections:

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

Number requirements as `R1`, `R2`, etc. A complete spec with settled goals, constraints, and acceptance criteria may go directly to `genius-impl-plans`.

## After the Brief

- Save the approved brief to `specs/YYYY-MM-DD-<topic>-design.md` unless the user names another path
- Do not `git commit` unless the user asks
- Ask them to review the file before `genius-impl-plans`
- If they request changes, edit and re-review. Only then invoke `genius-impl-plans`

## Key Principles

- One question at a time
- Multiple choice when possible
- YAGNI
- Compare 2-3 approaches when multiple viable options have meaningful trade-offs; if one approach is clearly appropriate, explain why and proceed
- Incremental approval
- Explain why, then stop. Coding is the next skill's job

## Visual Companion

Optional, Full tier only. Use when seeing beats reading (mockups, layouts, diagrams). A UI topic is not automatically visual. Details: `visual-companion.md`. If `scripts/` is missing, stay in the terminal.

## Gotchas

- Lite stops at a brief. Picking an approach is not permission to code.
- Clear-scope work should skip this skill entirely.
- `genius-impl-plans` is the only next skill. Do not jump to implementation skills.

## Module Layout

- `visual-companion.md` — optional browser companion
- `spec-document-reviewer-prompt.md` — Full-tier spec review persona
- `scripts/server.cjs`, `scripts/frame-template.html`, `scripts/helper.js` — companion runtime
- `scripts/start-server.sh`, `scripts/stop-server.sh` — Unix launchers

```
genius-brief-thinking/
├── SKILL.md
├── agents/
├── visual-companion.md
├── spec-document-reviewer-prompt.md
└── scripts/
```
