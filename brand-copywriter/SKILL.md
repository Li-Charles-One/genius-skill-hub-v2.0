---
name: brand-copywriter
description: "Use when user needs advertising copy, landing pages, email sequences, social media posts, or brand marketing content in English or Chinese. 品牌营销文案生成器：14种框架双版本对比，覆盖14个中外平台，严格AI禁用词过滤。Do not use for product UI DESIGN.md work, image generation, or ordinary non-marketing writing."
license: MIT
metadata:
  version: 2.0.0
  author: Linus
  hermes:
    tags: [copywriting, marketing, brand, ads, landing-page, email, social-media, AIDA, PAS, 文案, 种草, 私域, 小红书, 抖音]
    related_skills: []
---

# Brand Copywriter

## Gotchas

- This skill writes marketing copy. It does not produce DESIGN.md or generate images.

**来源**：适配自 [ognjengt/founder-skills](https://github.com/ognjengt/founder-skills)（170 stars, MIT），v2.0 增强中文平台、中文文案方法论、4A/本土机构、AI 净化流水线。

## 核心机制

生成**双版本文案**（最优框架 + 对比框架），供 A/B 测试选择。中英文双轨——西方大师 × 中国本土方法论 × 全球 14 个平台。

## 工作流程

### Step 1：读取参考文件（必须）

**前置检查**：以下5个文件必须全部可读，任一缺失则立即停止并提示用户修复路径，禁止在文件缺失情况下继续生成（否则框架/禁用词将凭空编造，输出完全不可信）：

```
references/copy_frameworks.md    ← 14种框架详解 + 28行中英文平台选择矩阵
references/writing_styles.md     ← 12位西方+13位中国/本土大师 · 中英禁用词 · 36个灵感来源
references/anti-slop-pass.md     ← 反AI腔净化流水线（门检→四遍审校→仲裁树→10问→5维评分→打磨报告）
references/platform-rules.md     ← 14个平台硬约束 + 7种中文特有文案类型
references/quality-checklist.md  ← 中英文双轨自检清单
```

### Step 2：检查品牌上下文

- 用户提供品牌/产品信息 → 使用
- 没有 → 默认值，必要时追问。中文品牌注意提取已有品牌色、品牌人设

### Step 3：分析输入

提取：文案类型、平台、产品/服务、目标受众（中文区分圈层）、核心转化、语气、长度限制。

### Step 4：选择框架

主框架根据平台 × 产品角度 × 受众认知层级选。对比框架必须提供真正不同的方法。不确定时 AIDA 或 PAS 兜底。

### Step 5：写作

参考 `references/writing_styles.md` 的写作硬规则和当前平台/大师方法选择指南。

### Step 6：输出后净化（必须，不可跳过）

写完文案后，**执行 `references/anti-slop-pass.md` 完整流水线**：门检→四遍审校→冲突仲裁树→10问自检→5维评分→强制附打磨报告。

**重写上限**：若评分 <30/50 需重写，最多重写 **2次**。第2次结束后无论得分如何，输出当前最优版本并附注：`⚠️ 本版本未完全达到反AI腔标准（<30/50），建议人工审查后使用。`

---

## 输出格式

```markdown
## Copy Brief
**文案类型：** [类型，如"小红书种草笔记"]
**平台：** [微信/小红书/抖音/Facebook 等]
**产品/服务：** [产品]
**目标受众：** [受众 + 圈层]
**核心转化：** [客户得到什么]
**平台约束：** [字符限制、违禁词等]
**语气：** [口语化/专业/温暖/犀利等]

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
[先测哪个版本，为什么。中文平台额外提醒违禁词和限流风险。]
```

---

## Pitfalls

1. **框架不是万能的**：选择矩阵是参考，不确定时 AIDA 或 PAS 兜底
2. **禁用词只是底线**：好文案不是"没用禁用词"，是"有具体细节、有观点、有节奏"
3. **平台约束是硬的**：Facebook 125 字符折叠、小红书 ≤1000 字——不是建议
4. **受众认知层级决定一切**：对"不知道自己有问题"的人讲解决方案，他们根本不会看
5. **中文文案 ≠ 英文翻译**：中文有短句+逗号节奏、关系先于功能的信任逻辑、种草>广告的平台生态
6. **不发明事实**：终稿里的数字/事件/引文，原文必须能打钩。打不到就删——这是第一宪法
