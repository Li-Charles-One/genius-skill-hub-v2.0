# Eval Workflow

Use evals to check whether a skill improves behavior, triggers correctly, and avoids unnecessary context.

## When To Use Evals

Use evals when:

- output can be checked objectively;
- the skill has a fragile workflow;
- trigger behavior matters;
- the skill is meant to be reused by many agents;
- a revision could regress existing behavior.

Use lighter manual review when the task is subjective or small.

## Eval Set Shape

For behavior:

- 2-5 prompts for small skills.
- 5-10 prompts for reusable tool or document workflows.
- Include edge cases and near misses.

For trigger optimization:

- 8-10 should-trigger prompts.
- 8-10 should-not-trigger prompts.
- Mix formal and casual phrasing.
- Include prompts that do not mention the skill name.

## Description Optimization

The `description` field is the primary trigger surface. Improve it by:

- naming the task type;
- listing concrete trigger contexts, a bit pushy so the skill is not under-triggered;
- naming important file types, tools, or workflows;
- saying when not to use the skill, using near misses rather than unrelated chores;
- avoiding vague claims like "helps with productivity";
- keeping platform-specific assumptions out unless the skill is platform-specific.

Should-trigger prompts should sound like a real user: casual, typo-prone, and not always naming the skill.

Should-not-trigger prompts must be near misses. "Write a Fibonacci function" is too easy for a PDF skill. Good negatives share keywords but need a different tool.

For high-stakes trigger tuning, create roughly half should-trigger prompts and half should-not-trigger prompts. Behavior comparisons use `eval-run-loop.md`, not string matches on this creator's reply.

## Evals JSON

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": "basic-trigger",
      "prompt": "Concrete user task",
      "trigger_expected": true,
      "expected_output": "What good looks like",
      "files": [],
      "assertions": [
        {"type": "contains", "value": "expected phrase"}
      ]
    }
  ]
}
```

Rules:

- `id` is a stable string, not a number.
- `trigger_expected` is required and boolean.
- Assertion types: `contains`, `not_contains`, `file_exists`, `exit_code`.
- For this hub, classify behavior with Create / Repair / Audit / Evaluate / Optimize / Port / Merge. Do not use Standardize as a mode name.

## Review Checklist

- Did the skill trigger for the right reason?
- Did it read only needed references?
- Did it use bundled scripts/assets correctly?
- Was output better than a baseline run?
- Did the description cause false positives?
- Did the skill overfit one example?

## Iteration

1. Run the evals.
2. Review failures and near misses.
3. Patch the smallest useful instruction or resource.
4. Rerun the same evals.
5. Add new evals only after the original failure mode is understood.
