---
name: genius-motion-graphics
description: "用 Remotion 写代码做 2D 视频包装：花字（标题字、口播关键词、科技光效字）、表格 / 选型表 / 参数对比表、柱状图 / 数据信息图、带透明窗口的对比叠加层，16:9 2K 或 4K，成片默认 H.265（透明的交 H.265 带 Alpha 的 MOV）。用户发参考截图说「照这个效果做个花字」「做个表格动画」「出个透明通道的字幕 / 信息图」「把这句话做成动效字」，或要改已有花字、表格的文字、颜色、节奏、重新出片、转透明格式、排查透明视频发黑发红色块时使用。不要用于 3D 产品原理动画和三维建模（用 genius-code-motion）、AI 生图生视频（用 dreamina-cli）、剪辑或调色实拍素材、品牌 VI 规范（用 genius-design）、PPT 文件、网页 UI 交互动效。"
metadata:
  version: "1.0.0"
---

# Genius Motion Graphics

在固定的 Remotion 工作台里，用代码做 2D 花字、表格和信息图动画：先出关键帧给用户确认，再渲成片，成片默认 H.265（透明的带 Alpha）。画面完全由帧号算出，改字、改色、改时长后重渲即可。

## 先分清请求

| 用户要 | 做法 |
|---|---|
| 照参考图做花字 | `references/title-recipes.md`：拆参考图的层次，再按配方组合 |
| 已有花字换文字、改行数、改字号 | 复用 `src/shared/` 的组件，在项目文件夹里加一个传 props 的合成，不复制组件 |
| 表格、选型表、参数总览、柱状图 | `references/table-recipes.md` |
| 对比叠加层（中间挖透明窗口放实拍） | `references/table-recipes.md` 的「透明窗口」 |
| 改颜色、透明度、节奏 | 只改对应常量或 props，改完重出关键帧 |
| 出成片、换透明格式 | `references/delivery.md` |
| 透明视频在播放器里发黑、光晕变实心色块 | `references/delivery.md` 的「排查」 |

## 硬规则

- **日常小件在公用工作台做，按项目分文件夹隔离；重要项目单独建工程。** 怎么判断、目录约定见 `references/workbench.md`。只换文字、颜色、行数的版本用 props，不复制组件；项目专属的数据和配色不进 `shared/`。
- **先出关键帧，确认后再渲成片。** 用 `scripts/stills.py` 出入场中、入场完、效果进行中、定版四个时刻，透明画面铺在灰底上拼成一张图发给用户。用户在同一句话里明确要成片时可以同时渲，但关键帧照样发。
- **所有成片默认 H.265。** 透明的出 H.265 带 Alpha 的 MOV（必须先预乘 Alpha），自带背景的出 `hvc1` 标签的 H.265 MP4。一律用 `scripts/deliver.py`，不要手写 ffmpeg 命令漏掉预乘或标签。只有用户点名、或成片要交给 Windows 剪辑时才交 ProRes 4444 或 PNG 序列，交付前先说明兼容性。
- **交付前自己验证。** 检查分辨率、帧率、帧数、透明通道标记，并用系统解码叠灰底和关键帧对比颜色；不凭「应该好了」交付。
- **改 `shared/` 组件后回归所有用到它的合成。** 重渲各合成的定版帧，和改动前逐字节比对，确认没被改坏。
- **画面数字要有出处。** 表格、图表里的数值来自用户资料；换算值、示意曲线要在画面或交付说明里标明不是实测。
- **同步更新工作台 README 的项目清单**，否则以后找不到入口。

## 工作流

1. 读 `references/workbench.md`，确认工作台依赖已装好（`node_modules` 存在）。
2. 看参考图或需求，按 `references/title-recipes.md` 或 `references/table-recipes.md` 拆出层次和动画节奏；有歧义（比如「背景偏红」指光效还是底色）先问一句再动手。
3. 在 `src/<项目>/` 里写组件或加 props 合成，包在 `<Folder name="<项目>">` 里并在 `src/Root.tsx` 挂上，2560×1440、30fps；要 4K 时渲染加 `--scale 1.5`，不另做一套布局。
4. 在工作台根目录运行 `python <skill>/scripts/stills.py --comp <ID> --project <项目>`，看拼图自查，再发给用户。
5. 按反馈修改，每轮重出关键帧。
6. 确认后运行 `python <skill>/scripts/deliver.py --comp <ID> --out out/<项目>/<名字>-2k-hevc.mov`；自带背景的画面加 `--opaque`、输出 `.mp4`；4K 加 `--scale 1.5`，文件名用 `-4k-`。脚本会渲染、转码、用系统解码校验并删掉中间文件。
7. 更新工作台 README 的项目清单，按「交付时报告」回复。

## Gotchas

- Remotion 导出的是未预乘 Alpha。直接转 H.265 带透明，Mac 的预览和 QuickTime 会把半透明光晕显示成实心色块、硬边。转码前必须预乘，`scripts/deliver.py` 已处理。
- ffprobe 把 H.265 带透明的文件报成 `yuv420p`，因为它读不到透明层；这不代表透明丢了。用 `scripts/check_alpha.swift` 检查。
- Remotion 不能直接输出 H.265 带透明，只能先渲 ProRes 4444 再转；硬件编码器 `hevc_videotoolbox` 只在 macOS 上有。
- Remotion `--codec=h265` 出的文件标签是 `hev1`，QuickTime 和预览打不开，要改成 `hvc1`（`deliver.py --opaque` 已处理）。
- `--scale` 必须让宽高都是整数：2K 合成出 4K 用 1.5（3840×2160），出 1080p 用 0.75；`1.3333` 会算出非整数高度直接报错。组件按 1920×1080 设计、按实际宽度整体缩放，所以换分辨率不用改布局。
- 渐变字面用 `background-clip: text` 时，同一层的 `text-shadow` 会盖住渐变。投影和外发光放到下面单独一层同样的字上。
- 用负字间距叠字符做 `›››` 箭头，三个会挤成一个；箭头用 SVG 画。
- 中文长句会在不该断的地方掉单个字。表格里手动用 `\n` 断行，配 `whiteSpace: 'pre-line'`。
- 逐帧调 `remotion still` 每次都要重新打包、开浏览器；出关键帧用 `scripts/stills.py`，它一次打包连续出图。
- 工作台的字体依赖本机安装的思源黑体；换机器没装就回退到苹方，字重和字宽都会变。

## Resource Map

- `references/workbench.md`：公用工作台与独立工程的分界、目录与隔离规矩、新建独立工程、画布与坐标、通用视觉规范。
- `references/title-recipes.md`：花字的层次拆解、各层配方、入场节奏、单行与多行排版、可调参数。
- `references/table-recipes.md`：表格、总览、柱状图、透明窗口叠加层的做法和配色禁忌。
- `references/delivery.md`：关键帧拼图、格式选择与兼容性、预乘转码、校验、排查。
- `scripts/stills.py`：批量出关键帧、铺灰底、拼 2×N 对照图；`--scale` 可出 4K 静帧查细节。
- `scripts/render_stills.mjs`：`stills.py` 调用的渲染部分，一次打包、一个浏览器连续出多帧透明 PNG。
- `scripts/deliver.py`：出成片，默认 H.265。透明：ProRes 中间文件 → 预乘转 H.265 带 Alpha；`--opaque`：H.265 MP4 并改 `hvc1` 标签；都用系统解码校验并删中间文件；`--format prores` 时只交 ProRes；`--scale 1.5` 出 4K；`--props` 传渲染参数（3D 工作台的小样、分层也用它出）。
- `scripts/check_alpha.swift`：macOS 上检查文件是否带透明通道，可解出一帧叠到灰底存 PNG。
- `evals/evals.json`：触发和行为测试用例。
- `agents/openai.yaml`：Codex/UI 元数据。

## 交付时报告

- 成片路径、格式、分辨率、帧率、时长、文件大小，有没有透明通道、有没有音轨；
- 动画节奏：几秒出完、何时扫光或高亮、有没有出场；
- 校验做了哪些（透明标记、系统解码对比、旧合成回归），哪些没验证（例如没在用户的剪辑软件里打开）；
- 兼容性提醒：H.265 带透明在 Windows 剪辑软件上可能显示黑底；
- 画面数据的出处和示意性质；
- 改文字、颜色的入口（项目文件夹里的合成 props 或组件文件）和重新出片的命令。
