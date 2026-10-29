---
name: genius-code-motion
description: "用代码做 3D 产品科普 / TVC 质感动画：Remotion 逐帧渲染 + Three.js（React Three Fiber）建模运镜 + postprocessing 辉光景深 + HTML/SVG 标注字幕，配音锁节奏，输出 MP4 和分层素材。适用于任何产品（灯具、家电、数码、电池、净化器等）的原理动画、拆解爆炸图、内部结构科普、3D 产品展示片、带数据标注的动效，或用户明确要「用代码做动画 / 不用 AE、C4D、Blender」时；也用于这类 Remotion + Three.js 项目的改镜头、对配音、提质感、出小样或分层、排查黑屏或部件消失。不要用于 AI 生图生视频（用 dreamina-cli）、剪辑或调色实拍素材、网页 UI 交互动效、纯 2D 字幕条或 PPT 动画、需要安装 Blender/C4D 等外部 DCC 软件的流程。"
metadata:
  version: "1.2.0"
---

# Genius Code Motion

用代码把任何产品的原理做成可逐帧复现的 3D 科普动画：开工清单 → 建模确认 → 配音时间点 → 静帧分镜确认 → 动画 → 小样审片 → 成片和分层交付。所有画面只由帧号算出，同一帧每次渲染结果一致，改一个参数就能重出整片。

## 先分清请求

| 用户要 | 做法 |
|---|---|
| 从零做一条动画 | 走完整工作流，两道确认关都过了才做动画 |
| 改已有项目的镜头、节奏、文案 | 只改 `timeline.ts`、`vo.txt` 和对应镜头，改完抽帧检查 |
| 配音到了，要对节奏 | `references/audio-sync.md` |
| 提高质感 | `references/look-dev.md` 的「质感升级阶梯」，按实测结论从上往下做 |
| 出小样、无字幕版、透明叠加层 | `references/architecture.md` 的「渲染与交付」 |
| 黑屏、闪烁、部件消失、亮度跳变 | `references/review-loop.md` 的排查顺序 |
| 动画卡、一顿一顿、不流畅 | `references/review-loop.md` 的「流畅度检查」：先量化，再改运镜 |
| 只有旧成片没有源码，要换建模、运镜不变 | `references/architecture.md` 的「照旧成片复刻运镜」 |
| 照实拍照片修正建模（造型、比例、材质） | `references/look-dev.md` 的「照实拍核对建模」 |
| 同一套建模出长短不同的版本、整片改时长 | `references/architecture.md` 的「多版本共用建模」 |
| 和实拍素材衔接 | `references/storyboard.md` 的「与实拍衔接」 |

## 硬规则

- **先要齐资料。** 开工时按 `references/kickoff.md` 给用户一张开工清单，逐项标出已有、缺、不需要；缺的项说清楚影响哪些镜头。影响建模或核心卖点的缺项，停下来等资料。
- **两道确认关，过了才做动画。**
  1. **建模确认**：先列出从照片或资料读出的结构（部件、数量、排布、尺寸），再渲一张模型静帧，一起给用户确认。
  2. **静帧分镜确认**：建模确认后出分镜表（时长、口播、要讲明白什么、画面），每镜配 1–2 张关键姿态静帧，用户确认后才开始做镜头动画。
- **画面上的数字必须有出处。** 产品参数来自用户给的资料；估算值写明假设；推断值告诉用户待品牌方确认；资料互相矛盾时先指出来；没有数据就用定性刻度，不编数字。
- **节奏跟着配音走。** 有配音就用配音的真实时长，没有就按字数估，并告诉用户这是估的。
- **一切动画只由帧号决定。** 不用 `Date.now()`、`Math.random()`、`requestAnimationFrame`、物理模拟；需要随机就用固定种子。
- **3D 和标注共用同一个相机函数和状态函数。** 标注用投影坐标贴住 3D 点；计数、读数和画面用同一个函数算。
- **每改一轮都抽关键帧看图。** 不凭代码推断「应该好了」。
- **修改轮次也要先给图再出片。** 建模、运镜、标注改完，先发关键帧静帧（流畅度问题发半分辨率小样），用户确认后才渲整片。整片耗时长，用户要先把关。
- **流畅度用数字判断。** 用户说「卡」时先量逐帧位移和画面差，找到停顿、突变和峰值再改，改完再量一次，不凭肉眼说「应该顺了」。
- **不装 Blender、C4D 等外部软件**，除非用户明确要求。

## 工作流

1. **开工清单**：读 `references/kickoff.md`，一次要齐资料，并交叉核对有没有矛盾。
2. **搭项目**：复制 `assets/starter/` 到新目录，按 `references/architecture.md` 安装依赖，先渲一帧确认 WebGL 出图。
3. **建模**：读 `references/look-dev.md`。按实物资料还原结构、数量和排布，单位用米；贴图用 Canvas 程序化绘制。列出结构清单，渲一张模型静帧。**交用户确认。**
4. **配音时间点**：读 `references/audio-sync.md`，用 `scripts/vo_timeline.mjs` 生成 `src/vo.json`。有配音用真实时长，没有就按字数估。
5. **静帧分镜**：读 `references/storyboard.md`。每镜只讲一件事，科普点用图形讲。只摆关键姿态，用 `scripts/stills.mjs --html` 渲出图册，和分镜表一起**交用户确认**。
6. **动画与后期**：补全运镜、转场、动画；后期按 `references/postprocessing.md` 手动搭管线。
7. **抽帧检查**：`scripts/stills.mjs` 批量渲关键帧并拼对照图，按 `references/review-loop.md` 的清单逐镜看。
8. **小样审片**：`npm run draft` 出半分辨率小样，带配音给用户审节奏和内容。
9. **成片与分层交付**：`npm run render`，再按用户需要出无字幕版、纯 3D 版、透明叠加层。渲完用 ffprobe 核对，再抽一张对照图确认。

## Gotchas

- `@react-three/postprocessing` 的 `<EffectComposer>` 在 Remotion 逐帧渲染下输出全黑，根因未查实。改用 `postprocessing` 库手动搭管线（见 `references/postprocessing.md`）。
- 手动管线渲到中间缓冲时，渲染器不会做色调映射：管线末尾要加 `ToneMappingEffect`，并把 `gl.toneMapping` 设为 `NoToneMapping`。
- `NoiseEffect` 默认不透明度是 100%，必须手动压低，否则满屏颗粒。
- 贴得很近的两层表面，镜头拉远后会因深度精度不够互相遮挡。近裁剪面要跟着拍摄距离走（约 0.08 × 距离），层与层之间留足间距，再加 `polygonOffset`。
- 透明材质的自发光也会被不透明度缩放；为了补亮把自发光调大，整个就会变成白色实心。透镜、玻璃的自发光要很低，要真实质感就用 `transmission` 做真折射。
- 用「白色 + 低不透明度」做透镜，看起来是一层奶白色的皮。透明件改用 `transmission`，再用菲涅尔轮廓光、底部边沿亮线、内部亮芯表现「光被透镜兜住」，配方见 `look-dev.md`。
- 用 `keys()` 给一段连续运镜打多个关键帧，每段各自慢起慢停，镜头每到一个关键点就减速到 0，走走停停。连续运镜只用一条缓动 `u`，距离、横移、转角都挂在 `u` 上，用 `spline()` 穿过关键点（starter 的 `timeline.ts` 已提供）。
- 30fps、没有运动模糊时，每帧屏幕位移过大就会一格一格地跳。大幅推拉按对数距离均匀分配，不要把大部分拉远量挤在一小段里；还不够就整体拉长时长。
- 透明且不写深度的贴片（微距高清补丁、印刷层）会盖掉比它先画的加法发光（透镜轮廓、光晕），表现为某几颗透镜整颗不见。给贴在表面上的透明层设更小的 `renderOrder`，让它先画。
- 点光离自发光面只有几厘米时，线性亮起会在一两帧内把表面照爆，画面突然炸光。强度用 `t³` 先慢后快，或把灯移远。
- 镜头运动时灯光入射角会变，照度会突然跳亮或跳暗。聚光强度按「目标照度 × 距离²」算，转角过程中再单独压一下。
- 黑底上的半透明物体看起来像一块深灰色实心板。拆解图靠拉开间距表现层次，不靠半透明。
- 加法混合的发光效果会画到几何体外面的虚空里：给材质加 `clippingPlanes`，并开启 `renderer.localClippingEnabled`。
- 正上方或正下方拍摄时，`up=(0,1,0)` 会退化。按镜头选 `up`，切换镜头时插值 `up`。
- 环境反射（`RoomEnvironment`）会提亮整个画面，开了以后要同时调低主光。
- Remotion 的 `CameraMotionBlur` 套在 3D 画布外面，实测出现背景色带、构图偏移、几乎没有拖影，不要用。
- N8AO 没有 TypeScript 类型声明，要自己加一行 `declare module 'n8ao';`；它的 `aoRadius` 按米算，要按场景尺度设。
- 第一次渲染会下载无头 Chrome，很慢。macOS 上 WebGL 要用 `angle`，已写进 starter 的 `remotion.config.ts`。
- 每次 `remotion still` 都要重新打包、重开浏览器；检查多帧时用 `scripts/stills.mjs`，一次打包连续出图。

## Resource Map

- `references/kickoff.md`：开工清单、缺项怎么顶、常见资料矛盾。
- `references/storyboard.md`：分镜表、时长、科普图形手法（按道理分类，不限产品）、静帧分镜、事实核对、字幕、与实拍衔接。
- `references/audio-sync.md`：口播文本格式、生成配音时间点、在代码里引用、临时配音。
- `references/architecture.md`：安装、目录结构、帧驱动、时间轴、相机（含连续运镜）、标注投影、多版本共用建模、照旧成片复刻运镜、渲染与分层交付。
- `references/look-dev.md`：建模确认、照实拍核对建模、建模手法、程序化贴图、布光配方、发光、透明透镜配方、拆解图、使用场景、质感升级阶梯（含实测结论）。
- `references/postprocessing.md`：手动后期管线、景深、辉光、色调映射、颗粒。
- `references/review-loop.md`：批量抽帧、逐镜检查清单、排查顺序、流畅度检查（逐帧画面差、逐帧相机像素位移）、给用户审片、出片核对。
- `scripts/stills.mjs`：在项目根目录运行，批量渲关键帧，可选拼对照图（`--sheet`）、出图册页（`--html`）、带渲染参数（`--props`）。
- `scripts/vo_timeline.mjs`：由按句的配音音频或口播文本生成 `src/vo.json`，有音频时同时拼出 `public/vo.wav`。
- `assets/starter/`：最小可运行项目，包含配音时间点、小样和分层渲染命令。文件：`assets/starter/package.json`、`assets/starter/remotion.config.ts`、`assets/starter/tsconfig.json`、`assets/starter/vo.txt`、`assets/starter/props/draft.json`、`assets/starter/props/nosub.json`、`assets/starter/props/3d.json`、`assets/starter/props/hud.json`、`assets/starter/src/index.ts`、`assets/starter/src/Root.tsx`、`assets/starter/src/fps.ts`、`assets/starter/src/vo.json`、`assets/starter/src/vo.ts`、`assets/starter/src/timeline.ts`、`assets/starter/src/options.ts`、`assets/starter/src/state.ts`、`assets/starter/src/camera.ts`、`assets/starter/src/Scene.tsx`、`assets/starter/src/PostFX.tsx`、`assets/starter/src/Product.tsx`、`assets/starter/src/Overlay.tsx`、`assets/starter/src/hud.tsx`。
- `evals/evals.json`：触发和行为测试用例。
- `agents/openai.yaml`：Codex/UI 元数据。

## 交付时报告

- 成片和各分层文件的路径、时长、分辨率、帧率，有没有音轨；
- 每镜讲了什么（表格）；
- 画面上用到的数据和出处，哪些是估算或推断、还要谁确认；
- 节奏是按真实配音还是按字数估的；
- 抽查过哪些帧，哪些没验证；
- 改时长、文案的入口（`vo.txt`、`timeline.ts`）和重新出片的命令。
