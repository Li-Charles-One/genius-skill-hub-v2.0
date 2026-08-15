# Genius Skill Hub v2.0

可分享、相对通用的 Agent Skills monorepo。

## 定位

- **给谁用**：任何人可 clone / 适配到自己的 Agent 环境
- **是什么**：自研、可复用的 skill 包（流程、创意媒体、工具 CLI）
- **不是什么**：不含 Charles 个人主机路径、私有运维拓扑、生产密钥约定

个人高定制 skill 见 private 仓 [chales_wrokflow_skills](https://github.com/Li-Charles-One/chales_wrokflow_skills)。  
第三方聚合 skill（Tavily / Firecrawl / Context7 / OfficeCLI 等）见 [NIUBI-skills-collection](https://github.com/Li-Charles-One/NIUBI-skills-collection)。

| | 本仓库 | chales_wrokflow_skills |
|---|---|---|
| 受众 | 可分享 / 相对通用 | Charles 个人专用 |
| 内容 | 环境尽量可配置、无硬绑私人拓扑 | 真实主机、本机路径、发布闸门 |
| 可见性 | public | private |

## Skills

### Workflow

| Skill | Purpose |
|:--|:--|
| [genius-brief-thing](./genius-brief-thing/) | Turn an unclear idea into a design brief (formerly brainstorming) |
| [writing-plans](./writing-plans/) | Turn a spec into an implementation plan |
| [genius-weplaning](./genius-weplaning/) | Project memory lifecycle (`.agent-memory/`) |

### Creative / media

| Skill | Purpose |
|:--|:--|
| [genius-design](./genius-design/) | DESIGN.md brand systems (templates or reverse-engineer) |
| [genius-cpa-image](./genius-cpa-image/) | Multi-provider CPA images: Gemini + gpt-image-2 |
| [genius-omni](./genius-omni/) | Image / video / audio analysis via multimodal providers（视听） |
| [genius-shotlist-director](./genius-shotlist-director/) | Seedance 2.0 director shotlist → editable HTML (15s English prompts) |
| [dreamina-cli](./dreamina-cli/) | Dreamina（即梦） image/video generation CLI |
| [brand-copywriter](./brand-copywriter/) | Ad / landing / email / social brand copy |

### Tools

| Skill | Purpose |
|:--|:--|
| [github-cli](./github-cli/) | GitHub CLI: auth, repos, PRs, issues, Actions, API |
| [lark](./lark/) | Lark/Feishu CLI: docs, wiki, IM, calendar, mail… |
| [x-search-grok](./x-search-grok/) | Real-time X/Twitter search via Grok-compatible relay |
| [genius-skill-creator](./genius-skill-creator/) | Create, repair, validate, evaluate, port skills |

## Skill pipeline

复杂多步工作建议：

```
genius-brief-thing  →  writing-plans  →  implementation  →  genius-weplaning
   (WHAT/WHY)            (HOW)            (do the work)      (record state)
```

- `genius-brief-thing` — 方案不清时先收成 brief（旧名 brainstorming）
- `writing-plans` — 把设计规格拆成可执行步骤
- `genius-weplaning` — 持久化项目记忆
- 其余 skill 为叶子工具，不强制进这条流水线

## Layout

```
genius-skill-hub-v2.0/
├── genius-brief-thing/
├── brand-copywriter/
├── dreamina-cli/
├── genius-cpa-image/
├── genius-design/
├── genius-omni/
├── genius-shotlist-director/
├── genius-skill-creator/
├── genius-weplaning/
├── github-cli/
├── lark/
├── writing-plans/
└── x-search-grok/
```

每个 skill 根目录含 `SKILL.md`。

## Local use (OpenCode)

将 skill 目录 junction / symlink 到 `~/.config/opencode/skills/`，例如：

```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.config\opencode\skills\github-cli" `
  -Target "C:\path\to\genius-skill-hub-v2.0\github-cli"
```

部分 skill 依赖外部 CLI 或 API Key，请按各 skill 内文档自行配置；**不要**把密钥写进本仓库。
