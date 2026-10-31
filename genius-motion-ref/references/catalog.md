# `motion-reference` 检索地图与 Interactive 转化指南

本文件记录 `motion-reference` 里 8 个子模块的目录结构、可直接执行的检索命令、参考仓写法到官方 `<Interactive.*>` 写法的对照，以及剪映导出与字级配音对齐两个特殊工具的用法。

---

## 一、8 个参考子模块路径速查

下文命令假设已设置 `MOTION_REF`（如 `~/Documents/Genius_Sync_Projects/motion-reference`）。

### 1. `video-shotcraft`（10 类 125 张配方卡，产品宣传片镜头）

- **分类目录**（`references/shots/` 与 `demos/` 同名），括号内为真实卡名示例：
  - `opening/`：开场与品牌揭示（`text-as-mask`、`spotlight-hero-card`、`crane-rise-reveal`）
  - `camera/`：2.5D 空间运镜与拆解（`space-camera-moves`，内含爆炸图 `ExplodedView.tsx`；`graze-face-tour`、`crash-zoom-punch`）
  - `transition/`：转场（`card-flock-tumble`、`shot-transitions`、`circle-match-iris`）
  - `typography/`：动态大字排版（`flying-words`、`gradient-word-sweep`、`typewriter-moves`）
  - `ui-entrance/`：UI 卡片与组件入场（`card-stack`、`deck-deal-flyin`、`product-card-progressive-assemble`）
  - `interaction/`：交互反馈与主题切换（`theme-switch-moves`、`autolayout-gap-dial`、`collab-cursor-moves`）
  - `data/`：数据镜头（`chart-live-moves`、`gauge-readout-moves`、`before-after-slider-scrub`）
  - `effects/`：光效与强调（`spotlight-sweep-moves`、`assemble-then-type-flyin`、`fui-hud-moves`）
  - `rhythm/`：快节奏闪切（`beat-cut-moves`、`speed-ramp-freeze`、`trailer-grammar-moves`）
  - `outro/`：片尾收束（`logo-shrink-wordmark-lockup`、`ui-to-brand-morph`、`grain-dissolve`）
- **怎么读**：先读 `references/shots/<分类>/<卡>.md` 看设计意图、时长与缓动节奏，再看 `demos/<分类>/<卡>/` 下的 `.tsx`（个别卡没有 demo；一个目录可能有多个镜头文件）。

```bash
# 按关键词找配方卡（中英文都试）
rg -il '爆炸|exploded' "$MOTION_REF/video-shotcraft/references/shots"
# 列某分类全部卡名
ls "$MOTION_REF/video-shotcraft/references/shots/camera"
# 看某张卡对应的源码文件
ls "$MOTION_REF/video-shotcraft/demos/camera/space-camera-moves"
```

### 2. `video-talkcraft`（108 张口播解说与评测包装卡）

- **索引**：`references/cards-index.json`（每张卡含 `slug`、`title`、`oneliner`、`category`、`code`），人读版 `references/taxonomy.md`。
- **分类**：字幕花字、素材呈现、强调标注、数据信息图、转场结构、人物互动、运镜。
- **单卡说明**：`references/cards/<slug>.md`；**源码**：`template/cards/<slug>.tsx`。
- **通用小组件**：`template/components/`（花字、砸字、荧光笔、手绘圈注、数字滚动、视频边框）；镜头推拉与动态幕底：`template/motion-systems/`。
- **排版纪律**：`references/design-language.md`（色板、字阶）、`references/layout.md`（栅格与安全区）、`references/schematic.md`（线稿示意图）。

```bash
# 按分类列卡：slug / 标题 / 源码路径
jq -r '.cards[] | select(.category=="数据信息图") | "\(.slug)\t\(.title)\t\(.code)"' \
  "$MOTION_REF/video-talkcraft/references/cards-index.json"
# 按一句话描述搜关键词
jq -r '.cards[] | select(.oneliner | test("对比")) | "\(.slug)\t\(.title)"' \
  "$MOTION_REF/video-talkcraft/references/cards-index.json"
```

### 3. `anything2explainer`（黑底科技科普与原理拆解）

- **设计规范**：`reference/motion-vocabulary.md`（动效语汇）、`reference/composition-and-light.md`（黑底构图与发光层次）、`reference/style-guide.md`（配色、字体、底部章节进度条）。
- **模板源码**：`template/src/` 与 `examples/`。

### 4. `remocn`（`shadcn/ui` 风格 Remotion 组件库）

- **清单**：`registry/__manifest__.ts`、`registry/__index__.tsx`。
- **源码**：`registry/remocn/`（基础动效）、`registry/remocn-templates/`（场景模板）、`registry/remocn-ui/`、`registry/remocn-icons/`。

### 5. `snapcn`（设备样机套壳、文字揭示、产品演示）

- **清单**：`registry.json`、`MOTION.md`；**源码**：`registry/snap-cn/`、`registry/snap-cn-ui/`。

### 6. `awesome-ai-motion`（637 种动效技法图鉴）

- **索引**：`index.json`，`effects[]` 每项含 `slug`、`en`、`oneLinerEn`、`ease`、`params`、`snippet`；`recipes[]` 是 11 个组合场景配方。正文字段（`ko`、`oneLiner` 等）是韩文，**检索用 `en` / `oneLinerEn`**。
- **详情目录**：`effects/<slug>/`、`recipes/<slug>/`。

```bash
# 按英文关键词搜技法
jq -r '.effects[] | select(((.en // "") + " " + (.oneLinerEn // "")) | test("stagger"; "i")) | "\(.slug)\t\(.en)"' \
  "$MOTION_REF/awesome-ai-motion/index.json"
# 列全部组合配方
ls "$MOTION_REF/awesome-ai-motion/recipes"
```

### 7. `motion-skills`（垂类动效技能包索引）

- **入口**：`README.md`，列出各独立仓库（如 `iart-ai/data-animation-skills`、`iart-ai/kinetic-typography-skills`、`iart-ai/lower-thirds-skills`、`iart-ai/webgl-animation-skills`），需要时按 README 查看或拉取。

### 8. `OpenMontage`（全链路视频制片知识库）

- **Remotion 合成器与模板**：`remotion-composer/`；**制片与分镜知识**：`skills/`、`styles/`。

---

## 二、参考仓写法 → 官方 Interactive 写法对照

通用规则以官方 `remotion-best-practices/remotion-interactivity` 为准。下表只列参考仓里高频出现、必须改的写法：

| 参考仓常见写法（❌ 不要照搬） | 改写为（✅） |
|---|---|
| 外层 `<AbsoluteFill style={{ transform: \`scale(\${width / 1920})\` }}>` | 去掉缩放壳，按目标画布像素直接写 `left` / `top` / `width` / `fontSize` |
| `const p = interpolate(frame, [0, 20], [0, 1]);`<br>`style={{ transform: \`translateX(\${(1-p)*100}px) scale(\${p})\`, opacity: p }}` | 不抽中间变量、不拼 `transform` 字符串，每个属性各自内联：<br>`style={{ translate: interpolate(frame, [0, 20], ['100px 0px', '0px 0px'], { easing: Easing.bezier(0.16, 1, 0.3, 1), extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), scale: interpolate(frame, [0, 20], [0.9, 1], { easing: Easing.bezier(0.16, 1, 0.3, 1), output: 'perceptual-scale', extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }), opacity: interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) }}` |
| `style={{ ...baseStyle, fontSize: SIZE, color: PRIMARY }}` | 直接写字面量：`style={{ fontSize: 160, color: '#ffffff' }}` |
| 2~5 个标题/卡片用 `items.map((item, i) => <div key={i}>...</div>)` | 拆成独立的 `<Interactive.Div name="...">` 节点；大量重复的装饰元素（粒子、网格点）可保留 `.map()` 并用普通 `div` |
| 同一行字拆成阴影 div + 渐变 div 两层 | 单个 `<Interactive.Div>`，用多重 `textShadow` 或 `filter: drop-shadow(...)` |
| `<svg><path d={PATH} /></svg>` | `<Interactive.Svg><Interactive.Path name="..." d="M ..." /></Interactive.Svg>`，路径字符串直接写在 `d` 上；形变用内联 `interpolatePaths()` |

---

## 三、特殊工具（官方未内置）

只在用户明确需要时使用。脚本都在参考仓里，**从当前工程目录调用，不要在参考仓里装依赖**。

### 导出剪映专业版草稿

- **指南**：`video-shotcraft/references/jianying-export.md`（分层原则、底片渲染、建轨、安装、验收共 6 节，执行前通读）。
- **脚本**：`video-shotcraft/jianying-export/`，Mac 用 `mac_draft.py`（剪映专业版 11.2 实测通过），Windows 用 `windows_draft.py`（未真机验证，先跑 `smoke_test.py`）。
- **要点**：镜头内动效会烘焙进底片，字幕和音频是可编辑轨；剪映打开后会加密保存，是单向转换，要修改就重新导出覆盖。

### 口播配音预剪与字级时间戳

顺序固定：**先预剪，再打时间戳**，反过来会让后续时序整体错位。

```bash
# 1) 预剪口水词与长停顿：先看报告，认可后再落盘
python3 "$MOTION_REF/video-talkcraft/scripts/voice_trim.py" audio/raw.wav script.json --dry-run
python3 "$MOTION_REF/video-talkcraft/scripts/voice_trim.py" audio/raw.wav script.json --out audio/full.wav
# 2) 本机 CPU 字级时间戳（默认 FireRedASR2，需手动下载约 767MB 模型；--backend whisper 首跑自动下载约 460MB）
python3 "$MOTION_REF/video-talkcraft/scripts/timestamps_cpu.py" audio/full.wav script.json audio/timestamps.json
```

- 口播稿里的**数字必须写成汉字**，否则无法和读音对齐。
- 长音频脚本会自动按静音切成 ≤75s 的段；详细参数见两个脚本开头的 docstring。
