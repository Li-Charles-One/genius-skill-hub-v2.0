# Skill Consolidation Workflow

When multiple skills overlap, consolidate into class-level skills following this workflow.

## When to Consolidate

- 2+ skills cover the same domain with overlapping functionality
- User reports "too many skills" or "which one do I use?"
- Skills have clear sub-roles that could be one unified skill with sections

## Consolidation Pattern

### Step 1: Inventory

Search the skill root you are actually auditing. Resolve that root from `references/runtime-mapping.md`. Do not hardcode a single product path.

PowerShell:

```powershell
Get-ChildItem -Path $SkillRoot -Recurse -Filter SKILL.md |
  Select-String -Pattern "keyword" -List |
  Select-Object -ExpandProperty Path
```

Bash:

```bash
find "$SKILL_ROOT" -name "SKILL.md" -print0 | xargs -0 grep -l "keyword"
```

Common roots:

- OpenCode: `~/.config/opencode/skills` or a hub checkout
- Reasonix: `~/.reasonix/skills`
- Codex: project `.agents/skills`

Read each candidate skill. For each, note:

- **Unique content** — what only this skill provides
- **Overlap** — what is duplicated across skills
- **Trigger conditions** — when each skill fires

### Step 2: Design the Unified Skill

Choose a structure:

**Option A: Orchestration layer** (like design-plan)

- One routing skill receives all requests
- Specialist skills handle specific sub-tasks
- Router analyzes need, loads specialist, executes

**Option B: Single unified skill** (like document, hyperframes)

- One skill with sections for each sub-domain
- Clear section headers for navigation
- References to deep-dive docs in `references/`

**Option C: Class + sub-skills** (like genius-github-usage + sub-skills)

- Main skill covers common cases
- Sub-skills for niche scenarios (but consider if they are needed)

### Step 3: Merge Content

1. Start with the most comprehensive skill as base
2. Add unique content from other skills
3. Cross-reference: "For X, see section Y"
4. Add routing table if orchestration pattern

### Step 4: Mark Deprecated

For each old skill, update description:

```yaml
description: "Merged into new-skill. This capability now lives there. Use new-skill instead."
```

### Step 5: Delete

After confirming the new skill works, delete the deprecated folder from the same skill root you inventoried.

PowerShell:

```powershell
Remove-Item -LiteralPath (Join-Path $SkillRoot $DeprecatedSkill) -Recurse -Force
```

Bash:

```bash
rm -rf "$SKILL_ROOT/$DEPRECATED_SKILL"
```

## Naming Convention

- **Class-level**: `document`, `genius-github-usage`, `remotion`, `project-plan`
- **NOT session-level**: `fix-pdf-bug`, `debug-video-pipeline`
- **NOT library-level**: `pymupdf`, `reportlab`

The name should describe the domain, not the tool.

## Example Consolidations

| Before | After | Pattern |
|---|---|---|
| design-plan + design-md + frontend-design + ui-ux-pro-max | design-plan (router) + specialists | Orchestration |
| hyperframes + hyperframes-cli + hyperframes-media | hyperframes (unified) | Single skill |
| genius-github-usage + github-auth + github-issues + github-pr-workflow | genius-github-usage | Keep best, delete rest |

## Removing an Orchestrator

Sometimes an orchestration layer exists but the user wants sub-skills to operate independently.

1. Copy each `references/` file to the sub-skill that owns that knowledge.
2. Replace the old orchestrator name in the copied files.
3. Delete the orchestrator only after the sub-skills work alone.
4. Update any project memory that still points at the orchestrator.

## Pitfalls

1. **Do not merge tools into skills** — `pymupdf` is a tool, `document` is a skill.
2. **Orchestration needs a routing table** — not "use the right skill".
3. **Do not over-consolidate** — independent domains stay separate.
4. **Mark deprecated before deleting.**
5. **Preserve all unique content.**
6. **Do not assume the user wants orchestration** — prefer flat/independent unless asked.
7. **Distribute references before deleting an orchestrator.**
