# 项目架构与渲染

## 安装

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
src/
  index.ts       注册根组件
  Root.tsx       合成：ID、尺寸、帧率、总时长
  timeline.ts    每个镜头的起止帧 + 插值工具（改节奏只动这里）
  state.ts       由帧号算出的业务状态：哪些部件亮、计数、读数（3D 和标注共用）
  camera.ts      相机函数 getCam(f)、applyCam、标注用的投影 project(f, p)
  Scene.tsx      ThreeCanvas：相机、灯光、模型、后期
  PostFX.tsx     手动后期管线
  Product.tsx    产品模型（按项目改名，比如 Lamp.tsx）
  Overlay.tsx    HTML/SVG 叠加层：标注、面板、字幕
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
- `keys(f, [[帧, 值], ...])`：分段关键帧插值，适合相机距离、角度这类多段变化。

每个镜头用 `{start, end}` 表示，镜头内部的时间点都写成「镜头开始 + 偏移」，整段挪动时内部节奏不会乱。

## 相机系统

- `getCam(f)` 返回 `{pos, target, up, fov, focus}`。镜头内用 `blend(a, b, t)` 在两个机位之间插值；需要弧线运动时，给位置加 `sin(πt) × 高度`。
- **大幅推拉按对数距离插值**：`d = exp(lerp(ln d0, ln d1, t))`，从 4cm 拉到 1.3m 看起来是匀速的。
- **仰拍或俯拍**时 `up` 不能和视线平行；镜头切换时 `up` 也一起插值再归一化。
- `applyCam` 里近裁剪面跟着对焦距离走：`near = clamp(focus × 0.08, 0.002, 0.3)`。
- `focus` 同时传给景深，对焦就会跟着镜头走。

## 标注投影

- 叠加层的 `project(f, p)` 用一台独立的 `PerspectiveCamera`，套用同一个 `getCam(f)`，把 3D 点投影成屏幕像素。标注就能贴着部件移动。
- 计数、读数这类数字，要和 3D 用同一个状态函数算（比如 `litCount(f)`），画面里亮了几颗，数字就是几。

## 渲染

```bash
npx remotion render Main out/video.mp4 --crf=16
```

- 整片渲染耗时较长，放后台跑；渲完用 `ffprobe` 核对时长、分辨率和帧数。
- 改帧率、尺寸在 `Root.tsx` 里改；改时长改 `timeline.ts` 的镜头表。
- 想并排对比新旧版本，就换一个输出文件名，旧版本保留。
- `remotion.config.ts` 里已设置 WebGL 用 `angle`、帧图用 JPEG。在没有显卡的 Linux 服务器上要换 GL 后端，以 Remotion 文档为准（未在本流程实测）。
