#!/usr/bin/env node
// 批量渲关键帧：一次打包、一个浏览器连续出图，可选拼对照图。
// 在 Remotion 项目根目录运行：
//   node <skill>/scripts/stills.mjs --comp Main --out out/stills --frames 0,60,120-300:60 [--sheet 3] [--html] [--props props/x.json] [--entry src/index.ts] [--gl angle] [--verbose]
// --html 生成带帧号和时间码的图册页 index.html，用于静帧分镜确认
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {spawnSync} from 'node:child_process';

const usage = 'usage: node stills.mjs --comp <合成ID> --out <输出目录> --frames <0,60,120-300:60> [--sheet <每行张数>] [--html] [--props <json 文件>] [--entry src/index.ts] [--gl angle] [--verbose]';

const parseArgs = (argv) => {
  const a = {entry: 'src/index.ts', gl: 'angle', verbose: false, html: false};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k === '--verbose') a.verbose = true;
    else if (k === '--html') a.html = true;
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
// 和渲染命令的 --props 一样，传入渲染参数（比如只出 3D、关掉字幕）
const inputProps = args.props ? JSON.parse(fs.readFileSync(path.resolve(args.props), 'utf8')) : {};
const chromiumOptions = {gl: args.gl};
const serveUrl = await bundle({entryPoint: path.resolve(args.entry)});
const browser = await openBrowser('chrome', {chromiumOptions, logLevel});
const outputs = [];
const shots = [];
try {
  const composition = await selectComposition({serveUrl, id: args.comp, inputProps, puppeteerInstance: browser, chromiumOptions, logLevel});
  for (const f of frames) {
    if (f >= composition.durationInFrames) {
      console.warn(`跳过第 ${f} 帧：超出总帧数 ${composition.durationInFrames}`);
      continue;
    }
    const output = path.join(outDir, `f${String(f).padStart(5, '0')}.jpg`);
    await renderStill({composition, serveUrl, frame: f, output, inputProps, imageFormat: 'jpeg', jpegQuality: 88, puppeteerInstance: browser, chromiumOptions, logLevel});
    outputs.push(output);
    shots.push({frame: f, file: path.basename(output), fps: composition.fps});
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

// 图册页：每张图标出帧号和时间码，方便按「第几秒」反馈
if (args.html && shots.length > 0) {
  const tc = (f, fps) => {
    const s = Math.floor(f / fps);
    return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}+${String(f % fps).padStart(2, '0')}`;
  };
  const cards = shots
    .map((s) => `<figure><img src="${s.file}" loading="lazy"><figcaption>第 ${s.frame} 帧 · ${tc(s.frame, s.fps)}</figcaption></figure>`)
    .join('\n');
  const html = `<!doctype html><meta charset="utf-8"><title>${args.comp} 静帧</title>
<style>body{margin:24px;background:#111;color:#ddd;font:14px -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
main{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:16px}figure{margin:0}
img{width:100%;display:block;border-radius:6px}figcaption{margin-top:6px;color:#aaa}</style>
<h1 style="font-size:18px;font-weight:500">${args.comp} · ${shots.length} 张静帧</h1><main>
${cards}
</main>`;
  const page = path.join(outDir, 'index.html');
  fs.writeFileSync(page, html);
  console.log(`html → ${page}`);
}
