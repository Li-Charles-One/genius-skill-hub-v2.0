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

## Evals JSON

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "Concrete user task",
      "expected_output": "What good looks like",
      "files": []
    }
  ]
}
```

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
