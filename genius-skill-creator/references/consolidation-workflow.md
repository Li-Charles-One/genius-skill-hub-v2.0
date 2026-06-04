# Skill Consolidation Workflow

When multiple skills overlap, consolidate into class-level skills following this workflow.

## When to Consolidate

- 2+ skills cover the same domain with overlapping functionality
- User reports "too many skills" or "which one do I use?"
- Skills have clear sub-roles that could be one unified skill with sections

## Consolidation Pattern

### Step 1: Inventory

PowerShell:

```powershell
Get-ChildItem -Path "$HOME/.hermes/skills" -Recurse -Filter SKILL.md |
  Select-String -Pattern "关键词" -List |
  Select-Object -ExpandProperty Path
```

Bash:

```bash
find ~/.hermes/skills -name "SKILL.md" -print0 | xargs -0 grep -l "关键词"
```

Read each candidate skill. For each, note:
- **Unique content** — what only this skill provides
- **Overlap** — what'"'"'s duplicated across skills
- **Trigger conditions** — when each skill fires

### Step 2: Design the Unified Skill

Choose a structure:

**Option A: Orchestration layer** (like design-plan)
- One routing skill receives all requests
- Specialist skills handle specific sub-tasks
- Router analyzes need → loads specialist → executes

**Option B: Single unified skill** (like document, hyperframes)
- One skill with sections for each sub-domain
- Clear section headers for navigation
- References to deep-dive docs in `references/`

**Option C: Class + sub-skills** (like github-cli + sub-skills)
- Main skill covers common cases
- Sub-skills for niche scenarios (but consider if they'"'"'re needed)

### Step 3: Merge Content

1. Start with the most comprehensive skill as base
2. Add unique content from other skills
3. Cross-reference: "For X, see section Y"
4. Add routing table if orchestration pattern

### Step 4: Mark Deprecated

For each old skill, update description:
```yaml
description: "⚠️ 已合并到 <new-skill>。[功能] 现在是 <new-skill> skill 的一部分。请直接使用 <new-skill>。"
```

### Step 5: Delete

After confirming the new skill works:
PowerShell:

```powershell
Remove-Item -Path "$HOME/.hermes/skills/<deprecated-skill>" -Recurse -Force
```

Bash:

```bash
rm -rf ~/.hermes/skills/<deprecated-skill>
```

## Naming Convention

- **Class-level**: `document`, `github-cli`, `remotion`, `project-plan`
- **NOT session-level**: `fix-pdf-bug`, `debug-video-pipeline`
- **NOT library-level**: `pymupdf`, `reportlab`

The name should describe the DOMAIN, not the TOOL.

## Example: This Session'"'"'s Consolidation

| Before | After | Pattern |
|--------|-------|---------|
| design-plan + design-md + frontend-design + ui-ux-pro-max + claude-design + popular-web-designs + sketch | design-plan (router) + 4 specialists | Orchestration |
| hyperframes + hyperframes-cli + hyperframes-media + hyperframes-registry | hyperframes (unified) | Single skill |
| remotion-best-practices + remotion-to-hyperframes | remotion (unified) | Single skill |
| plan + writing-plans + planning-with-files + superpowers + systematic-debugging + test-driven-development | project-plan + task-plan | Split by scope |
| pdf + ocr-and-documents + markdown-converter + nano-pdf | document (unified) | Single skill |
| github-cli + github-auth + github-code-review + github-issues + github-pr-workflow + github-repo-management | github-cli (already comprehensive) | Keep best, delete rest |

## Removing an Orchestrator (De-consolidation)

Sometimes an orchestration layer is created but the user wants sub-skills to operate independently. When removing an orchestrator:

### Step 1: Distribute Reference Files
Orchestrators often accumulate `references/` files. Each file belongs to a specific sub-skill:
- Execution patterns, delegate_task guides → the sub-skill that does the parallel work
- Prompt formulas, templates → the sub-skill that uses them
- Batch generation guides → the sub-skill that produces the output
- Asset prompts, visual references → the sub-skill that generates visuals

PowerShell:

```powershell
$target = "$HOME/.hermes/skills/creative/<sub-skill>/references"
New-Item -ItemType Directory -Path $target -Force | Out-Null
Copy-Item -Path "$HOME/.hermes/skills/creative/<orchestrator>/references/<file>.md" -Destination $target
```

Bash:

```bash
mkdir -p ~/.hermes/skills/creative/<sub-skill>/references/
cp ~/.hermes/skills/creative/<orchestrator>/references/<file>.md \
   ~/.hermes/skills/creative/<sub-skill>/references/
```

### Step 2: Clean Up References
After copying, grep for the old orchestrator name in copied files and replace with the correct sub-skill name:
PowerShell:

```powershell
Get-ChildItem -Path "$HOME/.hermes/skills/creative/<sub-skill>/references" -Recurse -File |
  Select-String -Pattern "<orchestrator-name>"
# Replace any scheduled-task examples, skill references, etc.
```

Bash:

```bash
grep -rn '<orchestrator-name>' ~/.hermes/skills/creative/<sub-skill>/references/
# Replace any cronjob examples, skill references, etc.
```

### Step 3: Delete the Orchestrator
```python
skill_manage(action='delete', name='<orchestrator>',
             absorbed_into='<primary-sub-skill>')
```
The `absorbed_into` parameter tells the curator where the content went.

### Step 4: Update Memory
Remove or update any memory entries that reference the orchestrator pattern.

## Pitfalls

1. **Don'"'"'t merge tools into skills** — `pymupdf` is a tool, `document` is a skill. Skill = domain knowledge, not library docs.
2. **Orchestration needs clear routing table** — If using pattern A, the router must have a decision table, not vague "use the right skill".
3. **Don'"'"'t over-consolidate** — If two skills are truly independent (e.g., `minecraft` and `spotify`), keep them separate.
4. **Mark deprecated BEFORE deleting** — Gives users a transition period. Mark, verify, then delete.
5. **Preserve all unique content** — When merging, every unique section from every source skill must appear in the unified skill. Don'"'"'t lose knowledge.
6. **Don'"'"'t assume user wants orchestration** — If sub-skills are already self-contained, an orchestrator adds complexity without value. User preference: flat/independent > orchestrated. When in doubt, make sub-skills standalone first; add orchestration later only if the user asks for it.
7. **When deleting an orchestrator, distribute references first** — Orchestrators accumulate `references/` files. Before deleting, copy each file to the sub-skill that owns that knowledge. Then grep+replace the old orchestrator name in copied files.
