#!/usr/bin/env node
// 批量渲关键帧：一次打包、一个浏览器连续出图，可选拼对照图。
// 在 Remotion 项目根目录运行：
//   node <skill>/scripts/stills.mjs --comp Main --out out/stills --frames 0,60,120-300:60 [--sheet 3] [--entry src/index.ts] [--gl angle] [--verbose]
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {spawnSync} from 'node:child_process';

const usage = 'usage: node stills.mjs --comp <合成ID> --out <输出目录> --frames <0,60,120-300:60> [--sheet <每行张数>] [--entry src/index.ts] [--gl angle] [--verbose]';

const parseArgs = (argv) => {
  const a = {entry: 'src/index.ts', gl: 'angle', verbose: false};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === '--verbose') a.verbose = true;
    else if (k.startsWith('--')) a[k.slice(2)] = argv[++i];
  }
  return a;
};

// "0,60,120-300:60" → [0, 60, 120, 180, 240, 300]
const parseFrames = (spec) => {
  const out = [];
  for (const part of spec.split(',').map((s) => s.trim()).filter(Boolean)) {
    const m = part.match(/^(\d+)-(\d+)(?::(\d+))?$/);
    if (m) {
      const [a, b, step] = [Number(m[1]), Number(m[2]), Number(m[3] ?? 1)];
      for (let f = a; f <= b; f += step) out.push(f);
    } else if (/^\d+$/.test(part)) out.push(Number(part));
    else throw new Error(`无法解析帧号：${part}`);
  }
  return [...new Set(out)].sort((x, y) => x - y);
};

const args = parseArgs(process.argv.slice(2));
if (!args.comp || !args.out || !args.frames) {
  console.error(usage);
  process.exit(2);
}
const frames = parseFrames(args.frames);
const outDir = path.resolve(args.out);
fs.mkdirSync(outDir, {recursive: true});

// 从项目自己的 node_modules 加载 Remotion，而不是从技能目录
const projectRequire = createRequire(path.join(process.cwd(), 'package.json'));
let bundle, openBrowser, renderStill, selectComposition;
try {
  ({bundle} = projectRequire('@remotion/bundler'));
  ({openBrowser, renderStill, selectComposition} = projectRequire('@remotion/renderer'));
} catch {
  console.error('当前目录找不到 @remotion/bundler 或 @remotion/renderer。请在 Remotion 项目根目录运行，并先安装依赖。');
  process.exit(1);
}

const logLevel = args.verbose ? 'verbose' : 'warn';
const chromiumOptions = {gl: args.gl};
const serveUrl = await bundle({entryPoint: path.resolve(args.entry)});
const browser = await openBrowser('chrome', {chromiumOptions, logLevel});
const outputs = [];
try {
  const composition = await selectComposition({serveUrl, id: args.comp, puppeteerInstance: browser, chromiumOptions, logLevel});
  for (const f of frames) {
    if (f >= composition.durationInFrames) {
      console.warn(`跳过第 ${f} 帧：超出总帧数 ${composition.durationInFrames}`);
      continue;
    }
    const output = path.join(outDir, `f${String(f).padStart(5, '0')}.jpg`);
    await renderStill({composition, serveUrl, frame: f, output, imageFormat: 'jpeg', jpegQuality: 88, puppeteerInstance: browser, chromiumOptions, logLevel});
    outputs.push(output);
    console.log(`frame ${f} → ${output}`);
  }
} finally {
  await browser.close({silent: true});
}

// 拼对照图：用 ffmpeg 的 concat 列表，避开不同系统对通配符的差异
const cols = Number(args.sheet);
if (cols > 0 && outputs.length > 0) {
  const rows = Math.ceil(outputs.length / cols);
  const list = path.join(outDir, 'sheet-list.txt');
  fs.writeFileSync(list, outputs.map((p) => `file '${p.replace(/\\/g, '/').replace(/'/g, "'\\''")}'`).join('\n'));
  const sheet = path.join(outDir, 'sheet.jpg');
  const r = spawnSync('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-vf', `scale=640:-1,tile=${cols}x${rows}`, '-frames:v', '1', sheet], {stdio: 'inherit'});
  fs.rmSync(list, {force: true});
  if (r.error) console.warn('没有找到 ffmpeg，跳过对照图。');
  else if (r.status === 0) console.log(`sheet → ${sheet}`);
  else console.warn('对照图生成失败，单帧图片已保留。');
}
