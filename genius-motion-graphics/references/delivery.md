# 关键帧、成片与校验

## 关键帧

在工作台根目录运行：

```bash
python <skill>/scripts/stills.py --comp TechTitleDemo --project <项目> --frames 8,20,45,90
```

- 输出到 `out/<项目>/stills/<合成 小写>/`（不加 `--project` 时是 `out/stills/<合成 小写>/`）：每帧原始透明 PNG、铺灰底的预览 JPG、一张 2×N 的 `contact.jpg`。
- 挑帧：入场进行中、入场完成、效果进行中（扫光、跳数、高亮）、定版。
- 透明画面铺在 `#2a2f38` 深灰上预览；深色文字的叠加层用 `--bg ffffff` 换浅底。
- 发给用户时说明灰底只是预览，成片是透明底。
- 要交 4K 时加 `--scale 1.5` 出一张 4K 静帧，检查细线和光晕边缘。

## 格式选择

**所有成片默认 H.265**：要透明的出 H.265 带 Alpha 的 MOV，自带背景的出 H.265 MP4。其他格式只在用户点名或下表的特殊情况才用。

| 格式 | 何时用 | 兼容性 |
|---|---|---|
| **H.265 带 Alpha（透明默认）** | 叠在实拍上的花字、叠加层 | Final Cut、Mac 上的 Premiere 和达芬奇、QuickTime、预览可识别透明；Windows 剪辑软件多半显示黑底；剪映未验证，先让用户试 |
| ProRes 4444 | 用户点名、交给 Windows 剪辑或要做母版 | 剪辑软件通用，文件约为 H.265 的上百倍 |
| PNG 序列 | 任何软件都要能用、要无损 | 通用，但一个画面一百多个文件 |
| WebM（VP9 带透明） | 网页、H5 | 主流剪辑软件基本不认 |
| **H.265 MP4（不透明默认）** | 自带背景的整屏信息图、表格 | Mac 全部可用；标签必须是 `hvc1`，Remotion 默认的 `hev1` 在 QuickTime / 预览里打不开 |
| H.264 MP4 | 用户的平台或软件不收 H.265 时 | 最通用，文件比 H.265 大 |

## 出成片

```bash
python <skill>/scripts/deliver.py --comp <合成> --out out/<项目>/<名字>-2k-hevc.mov
```

```bash
python <skill>/scripts/deliver.py --comp <合成> --out out/<项目>/<名字>-2k.mp4 --opaque
```

透明（默认）的脚本步骤：

1. `remotion render` 出 ProRes 4444 中间文件（`yuva444p10le`，`--image-format=png`，`--color-space=bt709`）。
2. ffmpeg 预乘 Alpha 后用 `hevc_videotoolbox` 编码：

```bash
ffmpeg -i tmp.mov -vf "format=rgba,premultiply=inplace=1,format=bgra" -c:v hevc_videotoolbox -alpha_quality 0.9 -q:v 70 -tag:v hvc1 out.mov
```

3. 用 `check_alpha.swift` 确认 `ContainsAlphaChannel: 1`，并解第 3 秒一帧叠灰底存到成片同目录的 `stills/<合成 小写>/deliver-check.png`。
4. 打印分辨率、帧率、帧数、时长、大小，删除中间文件。

不透明（`--opaque`）的脚本步骤：Remotion 直接 `--codec=h265 --crf=18` 出中间文件 → `ffmpeg -c copy -tag:v hvc1 -movflags +faststart` 改标签 → 用系统解码器解一帧确认能打开 → 删中间文件。

要 4K 时加 `--scale 1.5`（输出 3840×2160），文件名用 `-4k-`；H.265 带透明 4K 依然很小。要 ProRes 时加 `--format prores`，脚本只渲 ProRes 并直接放到 `--out`。非 macOS 环境没有 `hevc_videotoolbox`，脚本会报错并提示改用 ProRes。

## 校验

- **规格**：ffprobe 看分辨率、帧率、帧数、时长。H.265 带透明会被报成 `yuv420p`，正常。
- **透明标记**：`swift <skill>/scripts/check_alpha.swift <文件>` 输出 `ContainsAlphaChannel: 1`。
- **颜色**：`swift <skill>/scripts/check_alpha.swift <文件> <输出.png> <秒数>` 用系统解码出一帧叠灰底，和同一时刻的关键帧拼图比；光晕颜色和浓淡应一致。
- **ProRes / PNG 的透明**：`ffmpeg -ss 3 -i x.mov -frames:v 1 -vf alphaextract a.png`，再用 `crop` + `signalstats` 看空白处 YMAX 为 0、文字处为满值。
- **回归**：改过共用组件时，重渲旧合成的定版帧，用 `cmp` 和改动前的 PNG 比对。
- 我们看不到用户的播放器。交付时请用户打开确认一次。

## 排查

| 现象 | 原因 | 处理 |
|---|---|---|
| Mac 预览里半透明光晕变成实心色块、硬边、颜色过饱和 | 转 H.265 前没预乘 Alpha | 用 `deliver.py` 重转 |
| H.265 MP4 在 QuickTime / 预览里打不开，系统解码报错 | 标签是 `hev1` | `ffmpeg -i x.mp4 -c copy -tag:v hvc1 y.mp4`，或用 `deliver.py --opaque` 重出 |
| 光晕颜色变灰、字边出现彩色描边 | 同上（系统解码对未预乘数据的另一种表现） | 同上 |
| 透明区域显示黑色 | 播放器或剪辑软件不支持透明，普通播放器常见 | 放进剪辑软件上层轨道再看；Windows 改交 ProRes |
| 渲染报非整数高度 | `--scale` 让宽高不是整数（如 1.3333） | 2K 合成用 1.5 出 4K、0.75 出 1080p |
| 字重、字宽和之前不一样 | 本机没装思源黑体，回退苹方 | 装字体后重渲 |
