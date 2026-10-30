# 项目架构与渲染

## 放哪里：公用3D动画工作台还是独立工程

| 情况 | 放哪里 |
|---|---|
| 日常项目：一两条短片、单个原理演示、快速出图 | 公用3D动画工作台，按项目建文件夹 |
| 大项目：镜头多、多个版本、要长期迭代、有自己的审片记录 | 独立工程（复制 `assets/starter/`） |
| 已有独立工程的项目 | 在它自己的工程里做 |

拿不准先放工作台；项目长大了再把文件夹搬出去成独立工程。

### 公用3D动画工作台

路径：`~/Documents/Genius_Sync_Projects/ChatWrok/公用3D动画工作台`。依赖和无头 Chrome 已装好，不要为日常项目另起工程。

```text
src/Root.tsx          每个项目挂一行（new_project.mjs 自动加）
src/<项目>/           起步模板的 src 全套 + vo.txt + props/；入口 index.tsx 包在 <Folder name="<项目>"> 里
src/demo/             起步模板原样，用来确认 WebGL 出图、改模板时对照
public/<项目>/        该项目的配音 vo.wav
out/<项目>/           该项目的成片和关键帧
```

- 新建：在工作台根目录运行 `node <skill>/scripts/new_project.mjs <项目名>`（小写英文和连字符），合成 ID 是 `<项目名>-main`。
- 各项目的模型、镜头、配色互不引用；确实要跨项目复用的，提到 `src/shared/` 再引用，改 `shared/` 后回归所有用到它的项目。
- 配音时间点：`node <skill>/scripts/vo_timeline.mjs --text src/<项目>/vo.txt [--clips <目录> --audio public/<项目>/vo.wav] --out src/<项目>/vo.json`。
- 关键帧：`node <skill>/scripts/stills.mjs --comp <项目>-main --out out/<项目>/stills --frames ... [--props src/<项目>/props/x.json]`。
- 出片没有每个项目单独的 npm 命令，统一用 genius-motion-graphics skill 的 `deliver.py`（会做 H.265 转码、预乘、`hvc1` 标签和系统解码校验），加 `--props` 传渲染参数：

```bash
python <motion-graphics skill>/scripts/deliver.py --comp <项目>-main --out out/<项目>/draft.mp4 --opaque --scale 0.5 --crf 24 --props src/<项目>/props/draft.json
python <motion-graphics skill>/scripts/deliver.py --comp <项目>-main --out out/<项目>/video.mp4 --opaque --crf 16
python <motion-graphics skill>/scripts/deliver.py --comp <项目>-main --out out/<项目>/video-nosub.mp4 --opaque --crf 16 --props src/<项目>/props/nosub.json
python <motion-graphics skill>/scripts/deliver.py --comp <项目>-main --out out/<项目>/layer-3d.mp4 --opaque --crf 16 --props src/<项目>/props/3d.json
python <motion-graphics skill>/scripts/deliver.py --comp <项目>-main --out out/<项目>/layer-hud-hevc.mov --props src/<项目>/props/hud.json
```

下面「安装」「渲染与交付」里的 npm 命令适用于独立工程。

## 安装（独立工程）

复制 `assets/starter/` 到新目录，在目录里装依赖。Remotion 的几个包版本必须一致，一条命令一起装最省事。

macOS / Linux：

```bash
npm i remotion @remotion/cli @remotion/three @remotion/bundler @remotion/renderer react react-dom three @react-three/fiber @react-three/drei postprocessing
npm i -D typescript @types/react @types/three
```

Windows PowerShell 命令相同，分两行执行即可。

装完先渲一帧确认 WebGL 能出图：

```bash
npx remotion still Main out/check.png --frame=30
```

第一次会下载无头 Chrome，比较慢。

## 目录结构

```text
vo.txt           口播文本，每行一句，行首 + 表示新增口播（显示成字幕）
props/           渲染参数：draft.json、nosub.json、3d.json、hud.json
public/          配音音频等静态文件（vo_timeline.mjs 会把 vo.wav 放在这里）
src/
  index.ts       注册根组件
  Root.tsx       合成：ID、尺寸、帧率、总时长
  fps.ts         帧率和画面尺寸
  vo.json        配音时间点（vo_timeline.mjs 生成）
  vo.ts          读 vo.json，cue(id) 返回某句的起止帧
  timeline.ts    每个镜头的起止帧（卡在配音句子上）+ 插值工具
  options.ts     读渲染参数：小样、字幕开关、分层
  state.ts       由帧号算出的业务状态：哪些部件亮、计数、读数（3D 和标注共用）
  camera.ts      相机函数 getCam(f)、applyCam、标注用的投影 project(f, p)
  Scene.tsx      ThreeCanvas：相机、灯光、环境反射、模型、后期
  PostFX.tsx     手动后期管线
  Product.tsx    产品模型（按项目改名）
  Overlay.tsx    HTML/SVG 叠加层、配音、按分层参数组装成片
  hud.tsx        叠加层公共组件：字幕、引线标注、面板、字体
```

镜头多了以后，把叠加层按镜头拆成 `hud/S1.tsx`、`hud/S2.tsx` 等。

## 帧驱动模式

- 组件里用 `useCurrentFrame()` 拿帧号，所有位置、亮度、透明度都由它算出。
- 材质、几何体在 `useMemo` 里只建一次，每帧在组件函数体里直接改属性（`emissiveIntensity`、`opacity`、`map.offset`）。不要每帧新建材质。
- Remotion 渲染时，`ThreeCanvas` 会关掉 R3F 自己的帧循环，每换一帧手动推进一次。所以 `useFrame` 回调每帧都会执行一次，可以在里面调用后期管线的 `render()`。

## 时间轴与关键帧

`timeline.ts` 提供这几个工具：

- `prog(f, a, b)`：帧 a 到 b 之间的 0→1 进度；
- `smooth`、`easeInOutCubic`、`easeOutExpo`：缓动曲线；
- `envelope(f, a, b, c, d)`：a→b 淡入，c→d 淡出；
- `keys(f, [[帧, 值], ...])`：分段关键帧插值，每段各自缓动，适合灯光、透明度这类分段变化；
- `spline(f, [[帧, 值], ...])`：平滑穿过所有关键帧，中途速度连续，只在首尾起停，**连续运镜用它**。

每个镜头用 `{start, end}` 表示，镜头内部的时间点都写成「镜头开始 + 偏移」，整段挪动时内部节奏不会乱。镜头边界尽量引用配音时间点（`cue('c2').end`），见 `audio-sync.md`。

## 相机系统

- `getCam(f)` 返回 `{pos, target, up, fov, focus}`。镜头内用 `blend(a, b, t)` 在两个机位之间插值；需要弧线运动时，给位置加 `sin(πt) × 高度`。
- **大幅推拉按对数距离插值**：`d = exp(lerp(ln d0, ln d1, t))`，从 4cm 拉到 1.3m 看起来是匀速的。
- **一段连续运镜只用一条缓动**：先算整段的进度 `u = spline(f, [[起, 0], …, [止, 1]])`，再让距离 `d = d0 × (d1/d0)^u`，横移、转角也用 `spline(u, …)` 按 `u` 取值。这样所有参数同步变速，不会在各自的关键点急刹。想让开头多停留一会儿，就在 `u` 的曲线里加一个早期的小值点（比如 `[起+40, 0.15]`），而不是给距离单独加关键帧。
- 横向平移放在镜头慢下来的段落做；在推拉最快的时候再叠加横移，屏幕位移会叠加成峰值。
- **仰拍或俯拍**时 `up` 不能和视线平行；镜头切换时 `up` 也一起插值再归一化。
- `applyCam` 里近裁剪面跟着对焦距离走：`near = clamp(focus × 0.08, 0.002, 0.3)`。
- `focus` 同时传给景深，对焦就会跟着镜头走。

## 标注投影

- 叠加层的 `project(f, p)` 用一台独立的 `PerspectiveCamera`，套用同一个 `getCam(f)`，把 3D 点投影成屏幕像素。标注就能贴着部件移动。
- 计数、读数这类数字，要和 3D 用同一个状态函数算（比如 `litCount(f)`），画面里亮了几颗，数字就是几。

## 多版本共用建模

同一套建模要出长短不同的版本（比如完整科普版和短版），不要复制模型代码，用一个「版本」上下文：

```ts
type Cut = {
  state: (f: number) => number; // 本片帧号 → 长版时间轴上的状态帧（灯亮几颗、灯罩开合、房间亮度都按它算）
  cam: (f: number) => CamState; // 本片自己的运镜
  area: (sf: number) => number; // 其他需要单独覆盖的状态
};
export const CutContext = createContext<Cut>(LONG_CUT);
export const useStateFrame = () => useContext(CutContext).state(useCurrentFrame());
```

- 模型、灯光、后期里原来用 `useCurrentFrame()` 的地方改成 `useStateFrame()`；相机、景深、跟镜头走的主光改用 `cut.cam(useCurrentFrame())`。长版传默认值，行为不变。R3F 的 Canvas 会自动把 React 上下文桥接进 3D 场景。
- 短版的 `state` 用分段线性映射到长版的状态帧（`keys(f, [...], t => t)`），跳过不需要的段落；长版里某段状态（比如面积扫动）短版不要时，用 `area` 这类字段单独覆盖，不要靠映射去躲。
- 标注的投影要用同一个 `cut.cam`；建模核对、对比实拍用的固定机位，也做成一个只有一两帧的版本（见 `look-dev.md` 的「照实拍核对建模」）。
- 改完共用代码，抽几帧长版和改之前的成片做 PSNR 比对，确认长版没被改坏：
  `ffmpeg -i old.png -i new.jpg -lavfi psnr -f null -`，结果在 40dB 左右以上就是只差压缩噪声。

**整片改时长**：时间点按原时长写不动，加一个换算 `toBase(f) = f × 原帧数 / 新帧数`，`cut.state`、`cut.cam` 和整个叠加层都先过 `toBase`，合成的 `durationInFrames` 改成新帧数。所有动作、停留按同一比例变慢；只想拉长某几段时再单独改时间点。

## 照旧成片复刻运镜（没有源码）

用户只有一条旧成片，要换建模、运镜和节奏不变时：

1. **先确认源码真的没了**：查版本管理、同步盘的历史版本目录、其他机器。找不到再复刻，并提前告诉用户复刻的运镜会很接近、但不会逐帧一致。
2. **逐秒拆旧片**：每秒抽一帧拼成总览图，转场和快速运镜段再按每秒 3 帧加密。记下每个镜头的起止秒、主体在画面里的位置和大小、计数之类的数字在哪一帧到哪个值、字幕何时出现。
3. **用旧片的帧号写新版本**：新做一个 `Cut`，相机按旧片的构图摆，状态帧映射到建模所在的时间轴。
4. **同帧并排对比**：用同一组帧号，左边旧片、右边新渲，拼成对照图逐格调；调完再按 `review-loop.md` 的「流畅度检查」量一遍，复刻时容易为了对准构图加太多关键帧，导致走走停停。
5. 交付时说明哪些地方和旧片不同（建模变了导致数量、颜色、排布变化）。

## 渲染与交付

渲染参数通过 `--props=<json 文件>` 传入，代码里由 `options.ts` 读取。**所有出片默认 H.265。** 起步模板的 `package.json` 已经写好了这几条命令，每条都是先渲到 `out/` 下以点开头的中间文件，转好后删掉：

| 命令 | 产出 | 用途 |
|---|---|---|
| `npm run draft` | 半分辨率小样（H.265 MP4），关掉景深和多重采样，速度明显更快 | 审节奏和内容 |
| `npm run render` | 完整成片（H.265 MP4），带配音和字幕 | 正式交付 |
| `npm run render:nosub` | 不带字幕的成片 | 给剪辑自己加字幕 |
| `npm run render:3d` | 只有 3D 画面，不带标注和配音 | 剪辑自己合成 |
| `npm run render:hud` | 只有标注和字幕的透明叠加层（H.265 带 Alpha 的 MOV） | 叠在剪辑自己的画面上 |

- 先出小样给用户审，节奏和内容定了再出正式成片。
- H.265 的两个坑，模板命令已处理，手写命令时别漏：
  - Remotion `--codec=h265` 出的标签是 `hev1`，QuickTime 和预览打不开；要 `ffmpeg -c copy -tag:v hvc1` 改标签。
  - 透明层不能直接出 H.265：先渲 ProRes 4444，**预乘 Alpha** 后再用 macOS 的 `hevc_videotoolbox` 编码；不预乘的话，Mac 上半透明的光晕会变成实心色块。`hevc_videotoolbox` 只在 macOS 上有，其他系统或用户点名时改交 ProRes 4444。
- 整片渲染放后台跑；渲完用 `ffprobe` 核对时长、分辨率、帧数、有没有音轨。ffprobe 会把 H.265 透明层报成 `yuv420p`（读不到透明层），透明要用 genius-motion-graphics 的 `scripts/check_alpha.swift` 检查：输出 `ContainsAlphaChannel: 1`，再解一帧叠灰底看光晕颜色正常。
- H.265 带透明在 Windows 剪辑软件上多半显示黑底；成片要交给 Windows 剪辑时先提醒用户，按需改交 ProRes 4444。
- 要交 4K：渲染时加 `--scale=2`，见 `look-dev.md` 的质感升级阶梯。
- 要交 2K（2560×1440）：从 1080p 放大 4/3 倍，写成 `--scale=1.3333333333333333`（写满 16 位）。`--scale` 乘出来的宽高必须是整数，少写几位会得到 1439.9999 之类的高度，渲完所有帧后在合成视频这一步报错、白跑一遍。其他非整数倍同理，先用 `node -e` 算一下宽高是不是整数。
- 改帧率、尺寸在 `fps.ts` 里改；改时长改 `timeline.ts` 或重新生成 `vo.json`。
- 新旧版本对比时换一个输出文件名，旧版本保留。
- `remotion.config.ts` 里已设置 WebGL 用 `angle`、帧图用 JPEG。在没有显卡的 Linux 服务器上要换 GL 后端，以 Remotion 文档为准（未在本流程实测）。
- 用户想自己拖时间轴看任意一帧，可以开 `npm run studio`，前提是能在浏览器里打开它。
