---
name: genius-motion-ref
description: "Remotion 动画参考库（motion-reference）导航与配方转化技能：当用户用 Remotion 做动画缺审美灵感、想找现成镜头模板/分镜配方/花字/数据表/黑底原理科普/设备样机套壳/转场效果，或点名查阅 motion-reference、video-shotcraft、video-talkcraft、anything2explainer、remocn、snapcn、awesome-ai-motion、OpenMontage，以及需要借用剪映草稿导出或字级配音对齐脚本时使用。负责从参考仓检索最佳镜头配方与 .tsx 源码，并配合官方 remotion-best-practices 将其改写为可在 Remotion Studio 画布直接鼠标拖拽编辑的 Interactive 组件。不要用于 AI 生图生视频大模型调用（用 dreamina-cli）、实拍视频调色剪辑或静态品牌 VI 文档生成（用 genius-design）。"
metadata:
  version: "1.0.0"
---

# Genius Motion Ref

将 `motion-reference`（8 大开源动效/分镜/组件参考库）作为「审美与镜头配方弹药库」，与官方 `remotion-best-practices`（「编码规范与 Studio 鼠标交互引擎」）打配合：**从参考库借审美、节奏和数学曲线，用官方 `<Interactive.*>` 标准落地成可在 Studio 里用鼠标直接拖拽改源码的组件。**

## 定位 `motion-reference` 根目录

按以下顺序解析本地 `MOTION_REF` 路径（跨平台兼容 macOS / Linux / Windows）：

1. 环境变量 `MOTION_REFERENCE_DIR`（若已设置且存在）；
2. 本技能真实路径（解析软链后）的同级工作区目录：`../../motion-reference`（即与 `genius-skill-hub-v2.0` 同级的 `motion-reference/`）；
3. 用户同步目录 `~/Documents/Genius_Sync_Projects/motion-reference`。

若本地均不存在，提示用户执行一次克隆：

```bash
git clone --recurse-submodules https://github.com/Li-Charles-One/motion-reference.git
```

## 与 `remotion-best-practices` 打配合的 4 条硬规则

1. **必须双技能联动**：凡涉及编写或修改 Remotion 代码，**必须同时加载 `remotion-best-practices`**（及其下的 `remotion-interactivity`、`remotion-markup`、`remotion-studio`、`remotion-render`）。
2. **只借「审美与运动数学」，不搬「死板 DOM 与私有工程壳」**：
   - 从参考仓提取：**构图层次、配色与光影、缓动曲线（`Easing.bezier` / `spring`）、错峰帧数节奏、几何/SVG 路径数据**；
   - **禁止**原样照搬参考仓里的 `.map()` 批量静态 `<div>`、`...style` 对象展开、外部样式常量或外层 `transform: scale(width / 1920)` 缩放壳（这些会导致 Remotion Studio 画布无法点选或拖拽偏移）。
3. **强制转化为官方 `<Interactive.*>` 可交互写法**：
   - 每个需独立选中的视觉单元（标题、副标题、光带、卡片、HUD 装饰、矢量箭头）写成独立的 `<Interactive.Div>`、`<Interactive.Svg>` 或 `<Interactive.Path>`，并赋予中文直观 `name`；
   - 样式直接写内联字面量对象，位移/缩放/旋转一律用 `translate`、`scale`（配 `output: 'perceptual-scale'`）、`rotate` 属性并内联 `interpolate(frame, ...)`，确保用户在 Studio 画布里鼠标一拖就能自动写回 `.tsx` 源码。
4. **预览与交付归官方管，特殊工序按需借脚本**：
   - 默认通过 `npx remotion studio` 打开交互预览供用户鼠标微调，除非用户明确要求否则不默认慢渲整片；
   - 仅当用户明确需要**「导出剪映专业版草稿」**或**「本地 CPU 字级配音时间戳对齐」**等 Remotion 官方未内置的工具时，按 `references/catalog.md` 调用参考仓里的对应脚本。

## 先分清去哪个子库找配方

| 用户想做的画面 / 需求 | 首选参考子库（相对于 `MOTION_REF`） | 检索入口 |
|---|---|---|
| **产品/网页宣传片镜头**（开场遮罩、2.5D 网页立体运镜/爆炸图、发牌飞入、聚光灯、快闪卡点） | `video-shotcraft/`（124 张配方卡 / 150 镜头） | 查 `video-shotcraft/references/shots/<分类>/`，源码在 `video-shotcraft/demos/<分类>/<卡名>/` |
| **口播/评测解说包装**（花字、砸字、数据对比表、证据巡游、G5 线稿示意图、荧光笔、视频边框） | `video-talkcraft/`（108+ 张口播动效卡） | 查 `video-talkcraft/references/taxonomy.md` 或 `cards-index.json`，单文件源码在 `video-talkcraft/template/cards/` 与 `template/components/` |
| **黑底科技科普 / 原理拆解**（暗黑画布流向图、结构图解、底部章节进度条） | `anything2explainer/` | 查 `anything2explainer/reference/motion-vocabulary.md` 与 `style-guide.md`，源码在 `anything2explainer/template/src/` |
| **即拷即用的通用动效组件 / 背景 / 转场** | `remocn/` | 查 `remocn/registry/remocn/` 与 `remocn/registry/remocn-templates/` |
| **数码/软件演示套壳**（手机/桌面样机框、文字揭示、终端命令行、Logo 定版） | `snapcn/` | 查 `snapcn/registry.json` 与 `snapcn/registry/snap-cn/` |
| **拿不准用什么动效手法、想查 637 种技法与缓动参数** | `awesome-ai-motion/` | 查 `awesome-ai-motion/index.json`、`effects/` 与 `recipes/` |
| **细分垂类动效技能包索引**（短视频、数据图表、WebGL、Manim、透明字幕条） | `motion-skills/` | 查 `motion-skills/README.md` 的 19 个技能包列表按需拉取 |
| **全链路分镜脚本与电影运镜语法** | `OpenMontage/` | 查 `OpenMontage/skills/` 与 `OpenMontage/remotion-composer/` |
| **把 Remotion 成片导出为「剪映专业版」草稿** | `video-shotcraft/jianying-export/` | 读 `video-shotcraft/references/jianying-export.md` |

详细目录结构、检索命令与转化范式见 `references/catalog.md`。

## 标准工作流（4 步借方改写）

1. **检索配方与源码**：根据上表和 `references/catalog.md`，在 `MOTION_REF` 下定位最匹配的 1~2 张配方卡（`.md`）及其 `.tsx` 实现源码；必要时先向用户展示选中的镜头思路。
2. **拆解视觉与时间轴要素**：从参考源码里提取核心参数（配色渐变、模糊/发光层级、关键帧区间 `[start, end]`、缓动函数 `Easing.bezier(...)`）。
3. **按 `remotion-best-practices` 重写为 Interactive 组件**：
   - 将坐标直接换算到当前工程画布尺寸（如 2560×1440 或 1920×1080），去掉外层 `transform: scale(...)`；
   - 将每个可编辑图层写成 `<Interactive.Div name="...">` / `<Interactive.Svg name="...">` / `<Interactive.Path name="...">`，把 `from`、文字内容、`style` 和 `interpolate(frame, ...)` 内联到节点上；
   - 在 `Root.tsx` 或项目文件夹的 `<Composition>` 上使用内联字面量注册。
4. **启动 Studio 联调交付**：按 `remotion-best-practices` 规范启动 `npx remotion studio`（或渲染单帧验证画面），告诉用户哪些图层、文字和关键帧可以直接在 Studio 画布中用鼠标拖拽微调。

## Gotchas

- **绝不要在参考仓子模块里跑 `npm install`**：`motion-reference` 仅作源码与配方查阅库；若在 8 个子模块里装依赖会白白占用数 GB 磁盘并拖慢同步。所有代码都应改写后放进你当前工作的 Remotion 工程里运行。
- **坐标系直写，别套外层 `transform: scale()`**：很多参考卡默认按 1920×1080 编写再套一层 `scale`。移植到 2K/4K 合成时，直接把字号和 `left`/`top`/`width` 换算成目标画布像素，保证在 Studio 里鼠标拖拽 `translate` 时 1:1 跟手。
- **单图层合并阴影与面层**：旧式花字常把同一行字拆成“底层阴影 `<div>` + 顶层渐变 `<div>`”，在 Studio 里鼠标拖顶层字会导致阴影留在原地。改写为 `<Interactive.Div>` 时，优先用单个节点的 `color` + 多重 `textShadow` / `filter: drop-shadow(...)` 实现，确保点选拖拽时整行字一体移动。
- **注意开源许可差异**：`video-shotcraft`、`remocn` 等为宽松开源协议（Apache-2.0 / MIT），而 `video-talkcraft` 为 `PolyForm Noncommercial 1.0.0`（个人与研究免费，参考其设计思路用官方 Interactive 重写即可，不要直接商用分发其专有工具链）。

## 输出标准

交付借方改写后的动画组件时，简要说明：

- **参考来源**：借鉴了 `motion-reference` 里的哪个子库、哪张配方卡（附卡片路径）；
- **落地文件**：当前工程中新增或修改的 `.tsx` 路径与 `<Composition id="...">`；
- **Interactive 可调清单**：列出已在 Studio 时间轴与画布中解锁的中文图层名（`name`），提示用户可直接鼠标拖拽位置、修改文字或调整关键帧。

## Resource Map

- `references/catalog.md`：`motion-reference` 8 大子仓的精确目录地图、快速检索命令、`<Interactive.*>` 转化前后对照范例与剪映导出/配音对齐工具指南。
- `agents/openai.yaml`：Codex / UI 展示元数据。
- `evals/evals.json`：正负触发与配合行为测试用例。
