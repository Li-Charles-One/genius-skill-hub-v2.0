# `motion-reference` 检索地图与 Interactive 转化指南

本文件记录 `motion-reference` 仓库内 8 个子模块的精确目录结构、检索方法，以及如何把参考仓里的普通 React/Remotion 代码改造成符合官方 `remotion-best-practices` 标准的 `<Interactive.*>` 组件。

---

## 一、8 大参考子模块精确路径速查

假设已定位 `MOTION_REF`（如 `~/Documents/Genius_Sync_Projects/motion-reference` 或 `../../motion-reference`）：

### 1. `video-shotcraft`（124 张配方卡 / 150 个产品宣传片镜头）

- **10 大镜头分类目录**（位于 `video-shotcraft/references/shots/` 与 `video-shotcraft/demos/`）：
  - `opening/`：开场与品牌揭示（如 `text-as-mask` 巨字镂空透出界面、`logo-shrink-wordmark-lockup`）
  - `camera/`：2.5D 空间运镜与拆解（如 `exploded-view` 网页立体倾斜爆炸图、`graze-face-tour`、`space-camera-moves`）
  - `transition/`：丝滑转场（如 `card-flock-tumble` 卡片群翻滚成标题、`shot-transitions` 闪白/甩镜/遮罩转场）
  - `typography/`：动态大字排版（如 `flying-words` 文字隧道、`assemble-then-type-flyin`）
  - `ui-entrance/`：UI 卡片与组件入场（如 `card-stack` 扇形发牌、`product-card-progressive-assemble`）
  - `interaction/`：交互反馈与主题切换（如 `palette-theme-ripple` 主题色波纹扩散、`autolayout-gap-dial`）
  - `data/`：数据图表冲击力镜头（如 `axis-rescale-shock` 数据暴涨冲破坐标轴）
  - `effects/`：光效与聚光灯强调（如 `spotlight-sweep` 舞台聚光灯扫过标题、`spotlight-hero-card`）
  - `rhythm/`：快节奏闪切（如 `paparazzi-flash` 三连闪光灯裁切）
  - `outro/`：片尾收束（如 `input-morph-assemble` 输入框变形组装成 Logo）
- **怎么读**：
  1. 先读 `video-shotcraft/references/shots/<category>/<card>.md` 看设计意图、时长与缓动节奏；
  2. 再读 `video-shotcraft/demos/<category>/<card>/` 下的 `.tsx` 源码。
- **特殊工具（剪映专业版草稿导出）**：
  - 指南：`video-shotcraft/references/jianying-export.md`
  - 脚本目录：`video-shotcraft/jianying-export/`

### 2. `video-talkcraft`（108+ 张口播解说与评测包装卡）

- **全量卡片分类索引**：
  - Markdown 分类总表：`video-talkcraft/references/taxonomy.md`（按输入素材类型和场景分类）
  - JSON 机器索引：`video-talkcraft/references/cards-index.json`
- **单卡设计说明**：`video-talkcraft/references/cards/<card-id>.md`
- **即拷即用 Remotion 源码**：
  - 108 张自包含卡片组件：`video-talkcraft/template/cards/<card-id>.tsx`
  - 通用包装小组件（素排字幕、花字、砸字、荧光笔、手绘圈注、数字滚动、视频容器八式边框）：`video-talkcraft/template/components/`
  - 相机推拉与 12 款动态幕底：`video-talkcraft/template/motion-systems/`（`backdrop.tsx`、`schematic.tsx` 等）
- **审美与排版纪律文档**：
  - `video-talkcraft/references/design-language.md`（色板、字阶、布局）
  - `video-talkcraft/references/layout.md`（12 栏栅格、安全区与防遮挡自检）
  - `video-talkcraft/references/schematic.md`（G5 线稿示意图系统）
- **特殊工具（字级配音对齐与预剪）**：
  - `video-talkcraft/scripts/timestamps_cpu.py`：口播稿与音频本机字级时间戳对齐
  - `video-talkcraft/scripts/voice_trim.py`：按文稿自动剪除口水词与停顿

### 3. `anything2explainer`（黑底科技科普与原理拆解）

- **设计规范**：
  - `anything2explainer/reference/motion-vocabulary.md`：暗黑画布科普常用动效语汇
  - `anything2explainer/reference/composition-and-light.md`：黑底构图与发光层次规范
  - `anything2explainer/reference/style-guide.md`：配色、字体与底部章节进度条规范
- **模板源码**：`anything2explainer/template/src/` 与 `anything2explainer/examples/`

### 4. `remocn`（`shadcn/ui` 风格 Remotion 组件库）

- **组件清单索引**：`remocn/registry/__manifest__.ts` 与 `remocn/registry/__index__.tsx`
- **源码目录**：
  - 基础动效组件：`remocn/registry/remocn/`
  - 场景模板：`remocn/registry/remocn-templates/`
  - UI 与图标动效：`remocn/registry/remocn-ui/`、`remocn/registry/remocn-icons/`

### 5. `snapcn`（产品演示、设备样机套壳与文字揭示）

- **注册表清单**：`snapcn/registry.json` 与 `snapcn/MOTION.md`
- **组件源码**：`snapcn/registry/snap-cn/` 与 `snapcn/registry/snap-cn-ui/`

### 6. `awesome-ai-motion`（637 种动效技法百科图鉴）

- **全局检索入口**：`awesome-ai-motion/index.json`（含 637 种技法的名称、分类、参数与适用场景）
- **单技法详情**：`awesome-ai-motion/effects/`
- **组合场景配方**：`awesome-ai-motion/recipes/`（开场 Hook、产品 UI 演示、数据故事、前后对比等）

### 7. `motion-skills`（19 个垂类动效技能包索引）

- **入口索引**：`motion-skills/README.md`（列出 19 个独立仓库地址，如 `iart-ai/data-animation-skills`、`iart-ai/kinetic-typography-skills`、`iart-ai/lower-thirds-skills`、`iart-ai/webgl-animation-skills` 等；需要某个细分包时可按 README 指引查看或拉取）。

### 8. `OpenMontage`（全链路视频制片知识库）

- **Remotion 合成器与模板**：`OpenMontage/remotion-composer/`
- **700+ 制片知识与分镜技能文件**：`OpenMontage/skills/` 与 `OpenMontage/styles/`

---

## 二、把参考源码转化为官方 `<Interactive.*>` 的标准范式

参考仓里的代码大多是为了批量脚本渲染写的，直接搬进工程虽然能看，但在 Remotion Studio 里**无法鼠标点选、无法拖拽改位置、无法在时间轴拉关键帧**。

落地时必须按以下对照表改写：

| 参考仓常见旧写法（❌ 不要直接照搬） | 官方 `remotion-best-practices` 写法（✅ 必须改写成这样） |
|---|---|
| `<div>{title}</div>` 或 `<svg><path .../></svg>` | `<Interactive.Div name="主标题">直接写固定文案</Interactive.Div>`、`<Interactive.Svg name="图标"><Interactive.Path name="箭头" d="..." /></Interactive.Svg>` |
| `items.map((item, i) => <div key={i}>...</div>)` | 若只有 2~5 个独立卡片/标题，**拆成独立的 JSX 节点**（每个节点有独立 `name` 和 `from`），Studio 才能分别选中并把修改写回源码 |
| `const p = interpolate(frame, [0, 20], [0, 1]);`<br>`style={{ transform: \`translateX(\${(1-p)*100}px) scale(\${p})\`, opacity: p }}` | 不用 `transform` 字符串，不抽中间变量 `p`，直接在 `style` 内联写：<br>`style={{ translate: interpolate(frame, [0, 20], ['100px 0px', '0px 0px'], { easing: Easing.bezier(0.16, 1, 0.3, 1), extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), scale: interpolate(frame, [0, 20], [0.9, 1], { easing: Easing.bezier(0.16, 1, 0.3, 1), output: 'perceptual-scale', extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), opacity: interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) }}` |
| `style={{ ...baseStyle, fontSize: SIZE, color: PRIMARY }}` | 不用 `...spread` 和外部常量，直接写字面量：`style={{ fontSize: 160, color: '#ffffff' }}` |
| 外层套 `<AbsoluteFill style={{ transform: \`scale(\${width / 1920})\` }}>` | 去掉外层缩放，直接按目标画布像素（如 2560×1440）写 `left` / `top` / `width` / `fontSize`，保证 Studio 画布鼠标拖拽 1:1 对齐 |
