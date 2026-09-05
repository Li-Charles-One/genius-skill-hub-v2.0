# Genius Skill Hub v2.0

可分享、相对通用的 Agent Skills monorepo。

## 定位

- **给谁用**：任何人可 clone / 适配到自己的 Agent 环境
- **是什么**：自研、可复用的 skill 包（流程、创意媒体、工具 CLI）
- **不是什么**：不含 Charles 个人主机路径、私有运维拓扑、生产密钥约定

个人高定制 skill 见 private 仓 [chales_wrokflow_skills](https://github.com/Li-Charles-One/chales_wrokflow_skills)。  
第三方聚合 skill（Tavily / Firecrawl / Context7 / 即梦 dreamina-cli 等）见 [NIUBI-skills-collection](https://github.com/Li-Charles-One/NIUBI-skills-collection)。

| | 本仓库 | chales_wrokflow_skills |
|---|---|---|
| 受众 | 可分享 / 相对通用 | Charles 个人专用 |
| 内容 | 环境尽量可配置、无硬绑私人拓扑 | 真实主机、本机路径、发布闸门 |
| 可见性 | public | private |

## Skills

### Workflow

| Skill | Purpose |
|:--|:--|
| [genius-brief-thinking](./genius-brief-thinking/) | Turn an unclear idea into a design brief (formerly brainstorming) |
| [genius-impl-plans](./genius-impl-plans/) | Turn a brief/spec into an implementation plan |
| [genius-weplaning](./genius-weplaning/) | Project memory lifecycle (`.agent-memory/`) |

### Creative / media

| Skill | Purpose |
|:--|:--|
| [genius-design](./genius-design/) | DESIGN.md brand systems (templates or reverse-engineer) |
| [genius-cpa-image](./genius-cpa-image/) | CPA-US gpt-image-2 images |
| [genius-omni](./genius-omni/) | Analyze images, video/audio, and OCR（视听） |
| [genius-shotlist-director](./genius-shotlist-director/) | Seedance 2.0 director shotlist → editable HTML (15s English prompts) |

### Tools

| Skill | Purpose |
|:--|:--|
| [genius-github-usage](./genius-github-usage/) | Genius GitHub usage via `gh` |
| [lark](./lark/) | Lark/Feishu CLI: docs, wiki, IM, calendar, mail… |
| [x-search-grok](./x-search-grok/) | Real-time X/Twitter search via Grok-compatible relay |
| [genius-skill-creator](./genius-skill-creator/) | Create, repair, validate, evaluate, port skills |

## Skill pipeline

复杂多步工作建议：

```
genius-brief-thinking  →  genius-impl-plans  →  implementation  →  genius-weplaning
   (WHAT/WHY)            (HOW)            (do the work)      (record state)
```

- `genius-brief-thinking` — 方案不清时先收成 brief（旧名 brainstorming）
- `genius-impl-plans` — 有 brief/spec 之后，拆成可执行步骤；未叫执行就停
- `genius-weplaning` — 持久化项目记忆和工作流状态
- 交接协议见 [`WORKFLOW.md`](./WORKFLOW.md)：brief 用 R1/R2 编号，plan 标注覆盖需求，memory 记录阶段状态
- 其余 skill 为叶子工具，不强制进这条流水线

## Layout

```
genius-skill-hub-v2.0/
├── genius-brief-thinking/
├── genius-cpa-image/
├── genius-design/
├── genius-omni/
├── genius-shotlist-director/
├── genius-skill-creator/
├── genius-weplaning/
├── genius-github-usage/
├── lark/
├── genius-impl-plans/
└── x-search-grok/
```

每个 skill 根目录含 `SKILL.md`。

## Local use (OpenCode)

将 skill 目录 junction / symlink 到 `~/.config/opencode/skills/`，例如：

```powershell
New-Item -ItemType Junction `
  -Path "$env:USERPROFILE\.config\opencode\skills\genius-github-usage" `
  -Target "C:\path\to\genius-skill-hub-v2.0\genius-github-usage"
```

部分 skill 依赖外部 CLI 或 API Key，请按各 skill 内文档自行配置；**不要**把密钥写进本仓库。
