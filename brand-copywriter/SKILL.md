---
name: brand-copywriter
description: "Use when user needs to write advertising copy, landing pages, email sequences, social media posts, or brand marketing content. 品牌营销文案生成器 — 14种经典框架双版本对比输出，严格AI禁用词过滤。"
license: MIT
metadata:
  version: 1.0.0
  author: Linus
  hermes:
    tags: [copywriting, marketing, brand, ads, landing-page, email, social-media, AIDA, PAS]
    related_skills: []
---

# Brand Copywriter

**来源**：适配自 [ognjengt/founder-skills](https://github.com/ognjengt/founder-skills)（170 stars, MIT）
**原始仓库**：https://github.com/ognjengt/founder-skills

## 核心机制

生成**双版本文案**：一个用最优框架，一个用对比框架，供 A/B 测试选择。

## 工作流程

### Step 1：读取参考文件（必须）

```
references/copy_frameworks.md    ← 14种框架详解 + 选择矩阵
references/writing_styles.md     ← 大师写作规则 + AI禁用词列表
```

### Step 2：检查品牌上下文

- 如果用户提供了品牌/产品信息 → 使用
- 如果没有 → 用默认值，必要时追问

### Step 3：分析输入

从用户需求中提取：
- **文案类型**（Facebook广告、landing page、TikTok等）
- **产品/服务**
- **目标受众**
- **核心卖点/转化**
- **语气**
- **长度限制**

### Step 4：选择框架

**主框架**根据：
- 文案类型/平台（参考选择矩阵）
- 产品角度（痛点→PAS，转型→BAB，功能→FAB）
- 受众认知层级（无意识→ACCA/AIDA，问题意识→PAS/BAB）

**对比框架**必须：
- 提供真正不同的方法
- 结构有对比性（如痛点导向 vs 转型导向）

### Step 5：写作 + 验证

## 写作硬规则

### 核心规则
- 写给**一个具体的人**，不是一群人
- 用**最强元素**开头（痛点、卖点或钩子）
- **一句话一个观点**
- **只用主动语态**
- **用具体数字**：`"127%"` 不是 `"超过100%"`，`"$45K/月"` 不是 `"六位数"`
- **卖点优先于功能** — 他们得到什么，不是它有什么
- **单一明确 CTA**：`"获取免费模板"` 不是 `"注册"`
- **用缩写**：`"You're"` 不是 `"You are"`
- **要有观点** — 温吞水卖不出东西
- 适当承认局限性 — 比吹嘘更能建立信任

### 禁用词列表（AI 味杀手机）

**绝对禁止的表达：**
- 用破折号制造戏剧效果
- `"And honestly?"`、`"Here's the thing..."`、`"The truth is..."`、`"At the end of the day..."`
- `"It's not X. It's Y."` 结构（整体删除）
- `"Let's dive in"`、`"Whether you're a X or a Y..."`、`"Unlock your potential"`
- `"game-changer"`、`"revolutionary"`、`"seamless"`、`"robust"`、`"leverage"`、`"streamline"`、`"delve"`
- `"Now,"` 开头的段落
- 连续三个短句制造虚假节奏感
- 结尾重复前面内容的一句话
- 假装脆弱实际是 humble brag

**懒惰形容词替换：**
- `"incredible"`、`"amazing"`、`"powerful"` → 用**具体细节证明**

## 平台适配规则

| 平台 | 硬约束 |
|------|--------|
| **Facebook/Instagram 广告** | 125 字符前折叠（hook 前置），主文案最多 1000 字符 |
| **TikTok/Reels** | 前 3 秒 = hook，15-60 秒脚本，口语化 |
| **LinkedIn** | 专业但人性化，首行 = hook，最多 1300 字符 |
| **YouTube** | 前 5 秒关键，长视频用时间戳 |
| **Landing Page** | 首屏 = 标题 + 副标题 + CTA，可扫读段落 |
| **Email** | 主题行 <50 字符，预览文字很重要，一封邮件一个 CTA |
| **Sales Page** | 允许长文案，多处证明点，建议 FAQ |

## 输出格式

```markdown
## Copy Brief
**文案类型：** [类型]
**产品/服务：** [产品]
**目标受众：** [受众]
**核心转化：** [客户得到什么]
**平台约束：** [字符限制、长度等]

---

## Version A: [主框架名称]

**选择原因：** [1-2句解释为什么选这个框架]

### 文案：
[完整文案，按平台格式]

---

## Version B: [对比框架名称]

**选择原因：** [为什么这个对比框架也值得试]

### 文案：
[完整文案，按平台格式]

---

## 建议
[先测哪个版本，为什么。A/B 测试建议。]
```

## 质量自检清单

### 执行前
- [ ] 已读取 copy_frameworks.md
- [ ] 已读取 writing_styles.md
- [ ] 两个框架 AND 写作规则都在上下文中

### 输入检查
- [ ] 文案类型/平台已确认
- [ ] 目标受众清晰
- [ ] 核心转化点明确

### 输出检查
- [ ] 两个版本用了不同框架
- [ ] 没有禁用词
- [ ] 没有懒惰形容词
- [ ] 用具体数字代替模糊表述
- [ ] CTA 具体且命名了动作
- [ ] 写给一个人，不是一群人

## Pitfalls

1. **框架不是万能的**：选择矩阵是参考，不是公式。如果用户的场景不在矩阵里，用 AIDA 或 PAS 兜底
2. **禁用词只是底线**：真正好的文案不是"没用禁用词"，而是"有具体细节、有观点、有节奏"
3. **双版本不是必须都用**：输出两个版本是为了对比和 A/B 测试，不是每个都要发布
4. **平台约束是硬的**：Facebook 125 字符折叠是技术限制，不是建议
5. **受众认知层级决定一切**：对"不知道自己有问题"的人讲解决方案，他们根本不会看
