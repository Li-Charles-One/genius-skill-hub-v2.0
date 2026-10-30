#!/usr/bin/env node
// stills.py 的渲染部分：一次打包、一个浏览器连续出多帧透明 PNG（f<帧号>.png）。
// 在 Remotion 工程根目录运行：
//   node render_stills.mjs --comp <合成> --out <目录> --frames 8,20,45,90 [--scale 1.5] [--props <json>] [--entry src/index.ts]
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';

const a = {entry: 'src/index.ts'};
const argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i++) if (argv[i].startsWith('--')) a[argv[i].slice(2)] = argv[++i];
if (!a.comp || !a.out || !a.frames) {
  console.error('usage: node render_stills.mjs --comp <合成> --out <目录> --frames 8,20,45,90 [--scale 1.5] [--props <json>] [--entry src/index.ts]');
  process.exit(2);
}

// 从工程自己的 node_modules 加载 Remotion
const req = createRequire(path.join(process.cwd(), 'package.json'));
let bundle, openBrowser, renderStill, selectComposition;
try {
  ({bundle} = req('@remotion/bundler'));
  ({openBrowser, renderStill, selectComposition} = req('@remotion/renderer'));
} catch {
  console.error('当前目录找不到 @remotion/bundler 或 @remotion/renderer，请在装好依赖的 Remotion 工程根目录运行');
  process.exit(1);
}

const frames = a.frames.split(',').map((s) => Number(s.trim())).filter((n) => Number.isInteger(n) && n >= 0);
const inputProps = a.props ? JSON.parse(fs.readFileSync(path.resolve(a.props), 'utf8')) : {};
const scale = a.scale ? Number(a.scale) : 1;
fs.mkdirSync(a.out, {recursive: true});

const serveUrl = await bundle({entryPoint: path.resolve(a.entry)});
const browser = await openBrowser('chrome', {logLevel: 'warn'});
try {
  const composition = await selectComposition({serveUrl, id: a.comp, inputProps, puppeteerInstance: browser, logLevel: 'warn'});
  for (const f of frames) {
    if (f >= composition.durationInFrames) throw new Error(`帧 ${f} 超出合成长度 ${composition.durationInFrames}`);
    const output = path.resolve(a.out, `f${f}.png`);
    await renderStill({composition, serveUrl, frame: f, output, inputProps, imageFormat: 'png', scale, puppeteerInstance: browser, logLevel: 'warn'});
    console.log(`frame ${f} -> ${output}`);
  }
} finally {
  await browser.close({silent: true});
}
