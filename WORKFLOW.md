# Workflow Handoff

The planning skills share one lightweight handoff:

```text
BRIEF_APPROVED → PLAN_DRAFT → PLAN_APPROVED → IMPLEMENTING → BLOCKED / DONE
```

- **Brief:** `specs/YYYY-MM-DD-<topic>-design.md`, with numbered requirements (`R1`, `R2`, …).
- **Plan:** `docs/plans/YYYY-MM-DD-<feature>.md`, with each task declaring `Covers: Rn` and a final coverage table.
- **Memory:** record `Brief`, `Plan`, `Status`, and `Current Task` in the existing `.agent-memory/CURRENT.md` sections. Do not create a second state file or change the WePlaning schema.

Only durable transitions or blockers need a memory write. Routine edits and ordinary progress do not. The plan skill stops at `PLAN_DRAFT`; implementation starts only after approval. `genius-weplaning` records accepted transitions and verifies memory after writing.
