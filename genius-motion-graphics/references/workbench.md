# 工作台

## 放哪里：公用工作台还是独立工程

| 情况 | 放哪里 |
|---|---|
| 日常小件：几条花字、一两张表、一个叠加层 | 公用工作台 `公用2D动画工作台`，按项目建文件夹隔离 |
| 重要项目：镜头多、要长期迭代、有自己的数据表和审片记录、要单独交接 | 独立工程，放在该项目目录下 |

拿不准时先放工作台；项目长大了再整个文件夹搬出去成独立工程。

## 公用工作台

路径：`~/Documents/Genius_Sync_Projects/ChatWrok/公用2D动画工作台`

```
src/Root.tsx            每个项目挂一行
src/shared/             跨项目复用的组件（如 TechTitle.tsx 科技光效花字）
src/<项目>/             一个项目一个文件夹；合成包在 <Folder name="<项目>"> 里
out/<项目>/             该项目的成片
out/<项目>/stills/<合成>/  关键帧和对照拼图
README.md               通用规范 + 项目清单
```

新开小项目：

1. 建 `src/<项目>/`（小写连字符英文），写一个导出 `<Folder name="<项目>">…</Folder>` 的文件；能用 `shared/` 组件传 props 的就不另写组件。
2. 在 `src/Root.tsx` 挂上。
3. 成片输出到 `out/<项目>/<名字>-2k-hevc.mov`；出关键帧时 `stills.py` 加 `--project <项目>`。
4. 在工作台 README 的「项目清单」加一行。

隔离规矩：

- 项目专属的文字、数据、配色、审片要求只写在项目文件夹里，不写进 `shared/` 和工作台通用规范。
- `shared/` 的组件改动会影响所有项目：改之前渲一张各项目的定版帧，改完用 `cmp` 逐字节比对。新加的能力做成可选 props，默认值保持旧行为。
- 两个项目都要用的组件才放 `shared/`；只有一个项目用的留在项目文件夹里。

其他：

- 依赖和渲染用的无头 Chrome 已装好，不要在工作台旁边另起工程做小件。
- 工作台在 Syncthing 同步目录里，`node_modules` 也会被同步；中间文件渲完即删。
- 工作台不存在或 `node_modules` 缺失时，先告诉用户，经同意再安装。
- 没有 git，回归靠渲帧比对。

## 新建独立工程

重要项目要单独建工程时：复制工作台的 `package.json`、`package-lock.json`、`tsconfig.json`、`remotion.config.ts`、`src/index.ts`，在新目录 `npm ci --prefer-offline`（走 npm 缓存）；再把工作台 `node_modules/.remotion` 整个复制过去，免得再下载一次 Chrome。要用的 `shared/` 组件复制一份进去，之后两边各自维护。

## 画布与坐标

- 合成统一 2560×1440、30fps。
- 组件内部按 1920×1080 设计，最外层套一层：

```tsx
<AbsoluteFill style={{width: 1920, height: 1080, transformOrigin: '0 0', transform: `scale(${width / 1920})`}}>
```

- 要 4K（3840×2160）就渲染时加 `--scale=1.5`，要 1080p 用 `--scale=0.75`；两者都能整除。`--scale` 只改像素密度，`useVideoConfig().width` 仍是 2560，布局不用动。
- 也可以注册一个 3840×2160 的合成（组件按 `width / 1920` 缩放，同样不用改布局）；二选一，同一画面别两套都维护。
- 4K 下细线、模糊半径、发光会跟着放大 1.5 倍，观感一致；但 1px 级细节在 2K 下可能是亚像素，出 4K 前先用 `stills.py --scale 1.5` 看一张。
- 透明画面的根节点背景设为 `transparent`。

## 通用视觉规范

- 字体：思源黑体（Source Han Sans SC），标题 Bold / Heavy，正文 Regular；回退苹方。
- 黑底：径向渐变 `#1A1A1C → #0B0B0C → #070707`，白字，说明文字用半透明白。
- 白底：`#FFFFFF`，正文 `#141414`，说明文字黑 50%。
- 动画：淡入 + 上移、线条从左往右画出、标题从遮罩下升起；缓动统一 `Easing.bezier(0.16, 1, 0.3, 1)`。
- 强调色按项目定，写在项目文件夹里。
- 所有动画只由 `useCurrentFrame()` 算出；不用 `Math.random()`、`Date.now()`。

## 常用命令（在工作台根目录）

```bash
npm run studio
```

关键帧和成片用本 skill 的 `scripts/stills.py`、`scripts/deliver.py`，见 `delivery.md`。
