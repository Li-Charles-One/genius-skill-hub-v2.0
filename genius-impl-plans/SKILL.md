---
name: genius-impl-plans
description: "Turn an approved brief or spec into a task-by-task implementation plan before coding. Use after genius-brief-thinking, or when the user already has a spec and asks for a plan. Triggers: genius-impl-plans, writing-plans, implementation plan. Do not use while already writing code, and do not use when what to build is still unclear — that is genius-brief-thinking."
---

# Genius Impl Plans

Write an implementation plan an engineer can follow without extra context. Exact files, complete code for code steps, exact commands, expected results. DRY. YAGNI.

Save to `docs/plans/YYYY-MM-DD-<feature-name>.md` unless the user names another path.

This skill stops at the plan. Do not start implementation unless the user asks.

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

If the repo has no test runner, write the verification step that this repo actually uses (typecheck, script smoke test, or manual check). Do not invent `pytest` for a Node or PowerShell project.

Do not make every step a commit. Frequent commits are optional and only when the user wants them.

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

````markdown
### Task N: [Component Name]

**Covers:** R1, R2

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run the project test command**

Run: `<the command this repo already uses>`
Expected: FAIL with a specific reason

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Re-run the same command**

Expected: PASS

- [ ] **Step 5: Commit** (only if the user asked)

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

End every plan with a `## Requirement Coverage` table mapping each brief requirement to its task and verification.

Use the languages and commands of the target repo. The Python above is an example, not a requirement.

## No Placeholders

These are plan failures — never write them:

- TBD, TODO, implement later, fill in details
- "Add error handling" / "add validation" without the code
- "Write tests" without the actual test
- "Similar to Task N" (repeat the code)
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

## Gotchas

- No brief and the approach is still fuzzy → `genius-brief-thinking`, not this skill.
- Writing the plan is not permission to code or commit.
- Do not force pytest, TDD, worktrees, or per-step commits onto a repo that does not use them.
