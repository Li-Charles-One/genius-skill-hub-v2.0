---
name: genius-code-motion
description: "用代码做 3D 产品科普 / TVC 质感动画：Remotion 逐帧渲染 + Three.js（React Three Fiber）建模运镜 + postprocessing 辉光景深 + HTML/SVG 标注字幕，输出 MP4。用户要做产品原理动画、拆解爆炸图、内部结构科普、3D 产品展示片、带数据标注的动效，或明确要「用代码做动画 / 不用 AE、C4D、Blender」时使用；也用于这类 Remotion + Three.js 项目的改镜头、调节奏、提质感、排查黑屏或部件消失。不要用于 AI 生图生视频（用 dreamina-cli）、剪辑或调色实拍素材、网页 UI 交互动效、纯 2D 字幕条或 PPT 动画、需要安装 Blender/C4D 等外部 DCC 软件的流程。"
metadata:
  version: "1.0.0"
---

# Genius Code Motion

用代码把产品原理做成可逐帧复现的 3D 科普动画：分镜 → 事实核对 → 建模与材质 → 运镜 → 后期 → 标注字幕 → 抽帧检查 → 出片。所有画面只由帧号算出，同一帧每次渲染结果一致，改一个参数就能重出整片。

## 先分清请求

| 用户要 | 做法 |
|---|---|
| 从零做一条动画 | 走完整工作流：建模确认 → 分镜确认 → 再做动画 |
| 改已有项目的镜头、节奏、文案 | 只改 `timeline.ts` 和对应镜头，改完抽帧检查 |
| 提高质感 | `references/look-dev.md` 的「质感升级阶梯」从上往下做 |
| 黑屏、闪烁、部件消失、亮度跳变 | `references/review-loop.md` 的排查顺序 |
| 和实拍素材衔接 | `references/storyboard.md` 的「与实拍衔接」 |

## 硬规则

- **两道确认关，过了才做动画。**
  1. **建模确认**：先列出从照片或资料读出的结构（部件、数量、排布、尺寸），再渲一张模型静帧，一起给用户确认。
  2. **分镜确认**：建模确认后再出分镜表，至少有时长、口播、要讲明白什么、画面四列，用户确认后才开始做镜头和动画。
- **画面上的数字必须有出处。** 产品参数来自用户给的资料（铭牌、规格书、检测报告）；估算值写明假设；推断值告诉用户待品牌方确认；没有数据就用定性刻度，不编数字。
- **一切动画只由帧号决定。** 不用 `Date.now()`、`Math.random()`、`requestAnimationFrame`、物理模拟；需要随机就用固定种子。
- **3D 和标注共用同一个相机函数。** 标注锚点用投影坐标贴住 3D 点；计数、读数和 3D 状态用同一个状态函数算。
- **每改一轮都抽关键帧看图。** 不凭代码推断「应该好了」。
- **不装 Blender、C4D 等外部软件**，除非用户明确要求。

## 工作流

1. **搭项目**：复制 `assets/starter/` 到新目录，按 `references/architecture.md` 安装依赖，先渲一帧确认 WebGL 出图。
2. **建模**：读 `references/look-dev.md`。按实物照片还原结构、数量和排布，单位用米；贴图用 Canvas 程序化绘制。列出结构清单，渲一张模型静帧。**交给用户确认，确认前不出分镜。**
3. **分镜**：读 `references/storyboard.md`。按口播字数估时长，每镜只讲一件事，科普点用图形讲，字幕只出关键词和算式。**交给用户确认，确认前不做动画。**
4. **时间轴与运镜**：所有镜头起止帧放 `timeline.ts`；相机用关键帧函数，大幅推拉按对数距离插值。
5. **后期**：读 `references/postprocessing.md`，手动搭后期管线。
6. **标注与字幕**：HTML/SVG 叠加层；新增口播做成字幕。
7. **抽帧检查**：用 `scripts/stills.mjs` 批量渲关键帧并拼对照图，按 `references/review-loop.md` 的清单逐镜看。
8. **出片**：`npx remotion render <合成ID> out/<名字>.mp4` 放后台跑，渲完用 ffprobe 核对时长和帧数，再抽一张对照图确认。

## Gotchas

- `@react-three/postprocessing` 的 `<EffectComposer>` 在 Remotion 逐帧渲染下输出全黑，根因未查实。改用 `postprocessing` 库手动搭管线（见 `references/postprocessing.md`）。
- 手动管线渲到中间缓冲时，渲染器不会做色调映射：管线末尾要加 `ToneMappingEffect`，并把 `gl.toneMapping` 设为 `NoToneMapping`。
- `NoiseEffect` 默认不透明度是 100%，必须手动压低，否则满屏颗粒。
- 贴得很近的两层表面（比如荧光粉面和封装底面），镜头拉远后会因深度精度不够互相遮挡。近裁剪面要跟着拍摄距离走（约 0.08 × 距离），层与层之间留足间距，再加 `polygonOffset`。
- 透明材质的自发光也会被不透明度缩放；为了补亮把自发光调大，整颗就会变成白色实心圆盘。透镜、玻璃的自发光要很低。
- 镜头运动时灯光入射角会变，照度会突然跳亮或跳暗。聚光强度按「目标照度 × 距离²」算，转角过程中再单独压一下。
- 黑底上的半透明物体看起来像一块深灰色实心板。拆解图靠拉开间距表现层次，不靠半透明。
- 加法混合的发光效果（比如地面光波）会画到几何体外面的虚空里：给材质加 `clippingPlanes`，并开启 `renderer.localClippingEnabled`。
- 正上方或正下方拍摄时，`up=(0,1,0)` 会退化。仰拍灯板用 `up=(0,0,1)`，切换镜头时插值 `up`。
- 第一次渲染会下载无头 Chrome，很慢。macOS 上 WebGL 要用 `angle`，已写进 starter 的 `remotion.config.ts`。
- 每次 `remotion still` 都要重新打包、重开浏览器；检查多帧时用 `scripts/stills.mjs`，一次打包连续出图。

## Resource Map

- `references/storyboard.md`：分镜表、时长估算、科普图形手法、事实核对、字幕规则、与实拍衔接。
- `references/architecture.md`：安装、目录结构、帧驱动模式、时间轴与关键帧、相机系统、标注投影、渲染命令。
- `references/look-dev.md`：建模、程序化贴图、布光配方、发光与辉光、拆解图、室内场景、质感升级阶梯。
- `references/postprocessing.md`：手动后期管线代码、景深、辉光、色调映射、颗粒。
- `references/review-loop.md`：关键帧抽查、逐镜检查清单、问题排查顺序、出片核对。
- `scripts/stills.mjs`：在项目根目录运行，批量渲关键帧，可选拼对照图。
- `assets/starter/`：最小可运行项目。文件：`assets/starter/package.json`、`assets/starter/remotion.config.ts`、`assets/starter/tsconfig.json`、`assets/starter/src/index.ts`、`assets/starter/src/Root.tsx`、`assets/starter/src/timeline.ts`、`assets/starter/src/state.ts`、`assets/starter/src/camera.ts`、`assets/starter/src/Scene.tsx`、`assets/starter/src/PostFX.tsx`、`assets/starter/src/Product.tsx`、`assets/starter/src/Overlay.tsx`、`assets/starter/src/hud.tsx`。
- `evals/evals.json`：触发和行为测试用例。
- `agents/openai.yaml`：Codex/UI 元数据。

## 交付时报告

- 成片路径、时长、分辨率、帧率；
- 每镜讲了什么（表格）；
- 画面上用到的数据和出处，哪些是估算或推断、还要谁确认；
- 抽查过哪些帧，哪些没验证（比如还没对配音节奏）；
- 改时长、文案的入口（`timeline.ts`）和重新出片的命令。
