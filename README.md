# Genius Skill Hub

Personal monorepo of **self-built** Agent Skills (OpenCode / Codex / Claude Code compatible).

Third-party skills (Tavily / Firecrawl / Context7 / PPT …) live in [NIUBI-skills-collection](https://github.com/Li-Charles-One/NIUBI-skills-collection).

## Skills (13)

### Workflow

| Skill | Purpose |
|:--|:--|
| [brainstorming](./brainstorming/) | Explore intent & design before complex multi-file work |
| [writing-plans](./writing-plans/) | Turn a spec into an implementation plan |
| [we-planing](./we-planing/) | Project memory lifecycle (`.agent-memory/`) |

### Creative / media

| Skill | Purpose |
|:--|:--|
| [genius-design](./genius-design/) | DESIGN.md brand systems (templates or reverse-engineer) |
| [genius-image](./genius-image/) | Image generation via Crun.ai (single / batch / multi-model) |
| [genius-vision](./genius-vision/) | Image & video analysis via doubao vision API |
| [dreamina-cli](./dreamina-cli/) | Dreamina（即梦） image/video generation CLI |
| [brand-copywriter](./brand-copywriter/) | Ad / landing / email / social brand copy |
| [officecli](./officecli/) | Create & edit Office docs (`.docx` / `.xlsx` / `.pptx`) |

### Tools

| Skill | Purpose |
|:--|:--|
| [github-cli](./github-cli/) | GitHub CLI: auth, repos, PRs, issues, Actions, API |
| [lark](./lark/) | Lark/Feishu CLI: docs, wiki, IM, calendar, mail… |
| [x-search-grok](./x-search-grok/) | Real-time X/Twitter search via Grok-compatible relay |
| [genius-skill-creator](./genius-skill-creator/) | Create, repair, validate, evaluate, port skills |

## Skill pipeline

For complex multi-step work:

```
brainstorming  →  writing-plans  →  implementation  →  we-planing
   (WHAT/WHY)       (HOW)            (do the work)      (record state)
```

- `brainstorming` — only when approach is ambiguous (or user asks to plan)
- `writing-plans` — turns the design spec into a step plan
- `we-planing` — persists durable session state
- All other skills are leaf tools and do not sit in this pipeline

## Layout

```
genius-skill-hub-v2.0/
├── brainstorming/
├── brand-copywriter/
├── dreamina-cli/
├── genius-design/
├── genius-image/
├── genius-skill-creator/
├── genius-vision/
├── github-cli/
├── lark/
├── officecli/
├── we-planing/
├── writing-plans/
└── x-search-grok/
```

Each skill is a folder with `SKILL.md` at its root.

## Local use (OpenCode)

Symlink / junction skills into `~/.config/opencode/skills/`, e.g.:

```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.config\opencode\skills\github-cli" `
  -Target "C:\path\to\genius-skill-hub-v2.0\github-cli"
```

Restart OpenCode after adding or removing skills.

## Validation

GitHub Actions `validate` checks skill metadata and WePlaning smoke tests.

Locally:

```powershell
git status --short
node we-planing/scripts/check-memory.cjs <project-root>
node we-planing/scripts/check-memory.cjs <project-root> --audit
node we-planing/tools/smoke-weplaning.cjs
```
