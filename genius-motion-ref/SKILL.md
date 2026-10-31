---
name: genius-motion-ref
description: "Remotion 动画参考库（motion-reference）导航与配方转化：用 Remotion 做动画缺审美灵感，想找现成镜头配方、花字、数据卡、黑底原理科普、设备样机、转场，或点名 motion-reference、video-shotcraft、video-talkcraft、anything2explainer、remocn、snapcn、awesome-ai-motion、motion-skills、OpenMontage，或要导出剪映草稿、做字级配音对齐时使用。从参考仓检索配方与 .tsx 源码，配合官方 remotion-best-practices 改写为 Studio 可拖拽编辑的 Interactive 组件。不要用于 AI 生图生视频（用 dreamina-cli）、实拍剪辑调色或静态品牌 VI（用 genius-design）。"
metadata:
  version: "1.1.0"
---

# Genius Motion Ref

`motion-reference`（8 个开源动效/分镜/组件参考库）是「审美与镜头配方弹药库」，官方 `remotion-best-practices` 是「编码规范与 Studio 交互标准」。**从参考库借审美、节奏和运动数学，按官方标准落地成可在 Studio 里拖拽改源码的组件。**

## 定位 `motion-reference` 根目录

按以下顺序解析 `MOTION_REF`：

1. 环境变量 `MOTION_REFERENCE_DIR`（若已设置且存在）；
2. 本技能真实路径（解析软链后）的 `../../motion-reference`（即与 `genius-skill-hub-v2.0` 同级）；
3. `~/Documents/Genius_Sync_Projects/motion-reference`。

均不存在时，提示用户克隆一次：

```bash
git clone --recurse-submodules https://github.com/Li-Charles-One/motion-reference.git
```

## 与 `remotion-best-practices` 的分工

1. **写或改 Remotion 代码时加载 `remotion-best-practices`，按它的路由按需加载子技能**（改写组件通常需要 `remotion-interactivity` 与 `remotion-markup`）。不要一次性全部加载；只有用户明确要求导出成片时才看 `remotion-render`。
2. **Interactive 写法以官方 `remotion-interactivity` 为准**（内联 style、内联 `interpolate()`、用 `translate`/`scale`/`rotate` 代替 `transform`、硬编码 `name` 等），本技能不重复这些规则，以免与官方版本漂移。
3. **只把需要独立调整的单元包成 `<Interactive.*>`**（标题、卡片、关键图形、可编辑路径）。纯布局容器和装饰性内部元素保持普通 HTML，否则 Studio 时间轴会冒出一堆无意义的行。
4. **预览交付归官方管**：默认打开 `npx remotion studio` 供用户拖拽微调，不默认渲染整片。剪映草稿导出、字级配音对齐这类官方未内置的工序，按 `references/catalog.md` 第三节调用参考仓脚本。

## 先分清去哪个子库找配方

| 用户想做的画面 / 需求 | 首选子库（相对 `MOTION_REF`） | 检索入口 |
|---|---|---|
| **产品/网页宣传片镜头**（开场遮罩、2.5D 运镜/爆炸图、发牌飞入、聚光灯、卡点） | `video-shotcraft/`（10 类 125 张配方卡） | `references/shots/<分类>/<卡>.md`，源码 `demos/<分类>/<卡>/` |
| **口播/评测包装**（花字、数据对比、强调标注、素材呈现、转场） | `video-talkcraft/`（108 张卡） | `references/cards-index.json` 或 `taxonomy.md`，源码 `template/cards/` |
| **黑底科技科普 / 原理拆解** | `anything2explainer/` | `reference/motion-vocabulary.md`、`style-guide.md`，源码 `template/src/` |
| **即拷即用的通用动效组件 / 背景 / 转场** | `remocn/` | `registry/__manifest__.ts`，源码 `registry/remocn/`、`registry/remocn-templates/` |
| **数码/软件演示套壳**（设备样机、文字揭示、终端、Logo 定版） | `snapcn/` | `registry.json`，源码 `registry/snap-cn/` |
| **拿不准用什么手法、查 637 种技法与缓动参数** | `awesome-ai-motion/` | `index.json`（正文为韩文，用 `en`/`oneLinerEn` 字段检索） |
| **细分垂类技能包**（数据图表、WebGL、字幕条等） | `motion-skills/` | `README.md` 的技能包列表 |
| **全链路分镜脚本与电影运镜语法** | `OpenMontage/` | `skills/`、`remotion-composer/` |

目录细节、可直接执行的检索命令和转化对照见 `references/catalog.md`。

## 标准工作流

1. **检索**：用 `references/catalog.md` 的检索命令定位 1~2 张最匹配的配方卡（`.md`）及其 `.tsx` 源码；不确定时先给用户看选中的镜头思路。
2. **拆解**：提取配色渐变、模糊/发光层级、关键帧区间、缓动（`Easing.bezier(...)` / `spring`）、错峰帧数与 SVG 路径数据。
3. **改写**：按官方 `remotion-interactivity` 重写进当前工程，并处理下方 Gotchas 里参考仓特有的写法。
4. **联调**：启动 Studio（或渲染单帧验证画面），告诉用户哪些图层可以直接拖拽微调。

## Gotchas（参考仓特有的坑）

- **不要在参考仓里跑 `npm install`**：`motion-reference` 只用来查阅；在子模块里装依赖会占用数 GB 并拖慢同步。代码一律改写后放进当前 Remotion 工程。
- **去掉外层 `transform: scale(width / 1920)` 缩放壳**：很多卡按 1920×1080 编写再整体缩放。移植时把字号和 `left`/`top`/`width` 直接换算成目标画布像素，Studio 拖拽才能 1:1 跟手。
- **2~5 个独立元素不要用 `.map()` 生成**：拆成独立 JSX 节点，各自带 `name` 和时序，Studio 才能分别选中并写回源码；大量重复的装饰元素（粒子、网格点）可以保留 `.map()`。
- **阴影层与文字层合成单节点**：旧式花字常拆成「底层阴影 div + 顶层渐变 div」，拖动时阴影会留在原地。改用单节点的多重 `textShadow` 或 `filter: drop-shadow(...)`。
- **一个 demo 目录可能有多个镜头**：如 `demos/camera/space-camera-moves/` 下有 `ExplodedView.tsx` 与 `DroneDiveLanding.tsx`，先列目录再选文件。
- **许可证不同**：`video-shotcraft`、`remocn` 等是宽松协议（Apache-2.0 / MIT）；`video-talkcraft` 是 `PolyForm Noncommercial 1.0.0`，只借设计思路自行重写，不要直接商用分发其源码或工具链。

## 输出标准

交付时简要说明：

- **参考来源**：借鉴了哪个子库、哪张配方卡（附路径）；
- **落地文件**：新增或修改的 `.tsx` 路径与 `<Composition id="...">`；
- **可调清单**：已在 Studio 中可选中的图层 `name`，提示用户可直接拖拽位置、改文字或调关键帧。

## Resource Map

- `references/catalog.md`：8 个子仓的目录地图、检索命令、参考仓写法到 Interactive 写法的对照，以及剪映导出与字级配音对齐的用法。
- `agents/openai.yaml`：Codex / UI 展示元数据。
- `evals/evals.json`：正负触发与配合行为测试用例。
