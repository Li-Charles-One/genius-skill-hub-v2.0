---
name: genius-impl-plans
description: "在编写代码前，将已确认的设计简报（Brief/Spec）转化为逐项可执行的代码实现计划。不要在已进入编码阶段使用，且不要在需求目标仍不明确时使用（需求阶段用 genius-brief-thinking）。"
metadata:
  version: "1.2.0"
---

# Genius Impl Plans

Write an implementation plan an engineer can follow without extra context: exact files, exact commands, expected results. DRY. YAGNI.

Write real code where a wrong guess is costly: tests, public signatures and data shapes, and non-obvious logic. Routine code may instead be specified precisely in words (file, function, inputs, behavior, error cases), so the plan does not write the whole feature twice.

Save to `docs/plans/YYYY-MM-DD-<feature-name>.md` unless the user names another path.

This skill stops at the plan (handoff state `PLAN_DRAFT`). Writing it is not permission to code or commit; implementation starts only after the user approves.

## Before You Write

- If there is no brief/spec and the approach is still ambiguous, send them to `genius-brief-thinking`.
- If one spec covers independent subsystems, suggest one plan per subsystem.
- Map files first: what is created, modified, or tested, and what each file is for. Follow existing repo patterns. Do not plan unrelated refactors.

## Task Granularity

Each step is one action. Prefer the repo's real loop over a generic TDD ritual.

If the repo already uses tests:

1. Write or update the test
2. Run the project's test command
3. Write the minimal code
4. Run the same command again
5. Commit only if the user asked for commits in the plan

If the repo has no test runner, write the verification step that this repo actually uses (typecheck, script smoke test, or manual check). Do not force pytest, TDD, worktrees, or per-step commits onto a repo that does not use them.

## Plan Header

Every plan starts with:

```markdown
# [Feature Name] Implementation Plan

> Implement task-by-task. Steps use `- [ ]`. Verify each task before the next.

**Goal:** [one sentence]

**Architecture:** [2-3 sentences]

**Tech Stack:** [what this repo already uses]

---
```

## Task Shape

The bracketed parts are slots to fill, in the target repo's language and commands. Use as many steps as the task needs.

````markdown
### Task N: [Component Name]

**Covers:** R1, R2

**Files:**
- Create: `exact/path/to/new-file`
- Modify: `exact/path/to/existing-file:123-145`
- Test: `exact/path/to/test-file`

- [ ] **Step 1: [one action, e.g. write the failing test]**

```[language]
[the actual test, signature, or change]
```

- [ ] **Step 2: [verify]**

Run: `[the command this repo already uses]`
Expected: [specific result, e.g. FAIL with the reason before the change, PASS after]
````

End every plan with a `## Requirement Coverage` table mapping each brief requirement to its task and verification.

## No Placeholders

These are plan failures — never write them:

- TBD, TODO, implement later, fill in details
- "Add error handling" / "add validation" without naming the cases and what happens in each
- "Write tests" without the actual test
- "Similar to Task N" without stating exactly what differs
- Steps that say what but not how
- Types or functions never defined in any task

## Self-Review

After the plan is written, check it yourself:

1. **Spec coverage:** every spec requirement has a task
2. **Placeholder scan:** none of the failures above
3. **Name consistency:** later tasks use the same types and function names as earlier ones

Fix inline and save.

## After the Plan

Tell the user where the file is. Stop.

If they ask to execute: follow the plan in this session, one task at a time, and pause after each group. Do not spawn implementation subagents unless they ask for that.

Trigger checks: `evals/evals.json`.
