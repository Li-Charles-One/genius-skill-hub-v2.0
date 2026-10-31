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
| [genius-weplaning](./genius-weplaning/) | Project memory lifecycle (`.agent-memory/`) |

### Creative / media

| Skill | Purpose |
|:--|:--|
| [genius-design](./genius-design/) | DESIGN.md brand systems (templates or reverse-engineer) |
| [genius-omni](./genius-omni/) | Analyze images, video/audio, and OCR（视听） |
| [genius-voice](./genius-voice/) | Speech-to-text and text-to-speech via Xiaomi MiMo（语音） |

### Tools

| Skill | Purpose |
|:--|:--|
| [genius-github-usage](./genius-github-usage/) | Genius GitHub usage via `gh` |
| [genius-lark-use](./genius-lark-use/) | Lark/Feishu CLI: docs, wiki, IM, calendar, mail… |
| [genius-x-search](./genius-x-search/) | Real-time X/Twitter search via Grok-compatible relay |
| [genius-skill-creator](./genius-skill-creator/) | Create, repair, validate, evaluate, port skills |

## Layout

```
genius-skill-hub-v2.0/
├── genius-design/
├── genius-omni/
├── genius-skill-creator/
├── genius-voice/
├── genius-weplaning/
├── genius-github-usage/
├── genius-lark-use/
├── genius-x-search/
└── hermes-install.md    # Hermes Agent 安装说明
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
