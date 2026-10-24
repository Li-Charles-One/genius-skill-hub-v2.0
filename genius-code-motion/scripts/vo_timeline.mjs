#!/usr/bin/env node
// 生成配音时间点文件 vo.json，让镜头卡在句子边界上。两种用法：
//   1) 每句一个音频文件：拼成一条配音并按真实时长算时间点（需要 ffmpeg / ffprobe）
//      node vo_timeline.mjs --clips <音频目录> --text <口播.txt> --audio public/vo.wav --out src/vo.json [--gap 0.4] [--lead 0.5]
//   2) 只有文字：按字数估时长
//      node vo_timeline.mjs --text <口播.txt> --out src/vo.json [--cps 4.5] [--gap 0.4] [--lead 0.5]
// 口播.txt 每行一句；行首写「+」表示新增口播（还没录音，要显示成字幕），例如：+ 驱动把交流电变成直流电
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const usage = `usage:
  node vo_timeline.mjs --clips <dir> --text <lines.txt> --audio public/vo.wav --out src/vo.json [--gap 0.4] [--lead 0.5]
  node vo_timeline.mjs --text <lines.txt> --out src/vo.json [--cps 4.5] [--gap 0.4] [--lead 0.5]`;

const a = {gap: '0.4', lead: '0.5', cps: '4.5'};
const argv = process.argv.slice(2);
for (let i = 0; i < argv.length; i++) if (argv[i].startsWith('--')) a[argv[i].slice(2)] = argv[++i];
if (!a.out || (!a.text && !a.clips) || (a.clips && !a.audio)) {
  console.error(usage);
  process.exit(2);
}
const gap = Number(a.gap);
const lead = Number(a.lead);
const round = (x) => Math.round(x * 1000) / 1000;

const readLines = (file) =>
  fs
    .readFileSync(file, 'utf8')
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => (s.startsWith('+') ? {text: s.slice(1).trim(), subtitle: true} : {text: s, subtitle: false}));

const run = (cmd, args) => {
  const r = spawnSync(cmd, args, {encoding: 'utf8'});
  if (r.error) throw new Error(`没有找到 ${cmd}，请先安装 ffmpeg（含 ffprobe）`);
  if (r.status !== 0) throw new Error(`${cmd} 失败：${r.stderr.trim().split('\n').slice(-3).join(' ')}`);
  return r.stdout;
};

let cues = [];
let audio = null;

if (a.clips) {
  const dir = path.resolve(a.clips);
  const clips = fs
    .readdirSync(dir)
    .filter((f) => /\.(wav|mp3|m4a|aac|aiff?|flac|ogg)$/i.test(f))
    .sort((x, y) => x.localeCompare(y, undefined, {numeric: true}))
    .map((f) => path.join(dir, f));
  if (clips.length === 0) throw new Error(`${dir} 里没有音频文件`);
  const lines = a.text ? readLines(a.text) : [];
  if (lines.length && lines.length !== clips.length) {
    console.warn(`提示：口播 ${lines.length} 句，音频 ${clips.length} 个，按顺序对应，多出的用文件名代替`);
  }
  let t = lead;
  clips.forEach((clip, i) => {
    const d = Number(run('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', clip]).trim());
    const line = lines[i] ?? {text: path.parse(clip).name, subtitle: false};
    cues.push({id: `c${i + 1}`, text: line.text, subtitle: line.subtitle, start: round(t), end: round(t + d)});
    t += d + gap;
  });
  // 拼接：每句后面补静音，整体前面留开头空白，统一成 48kHz 单声道
  const inputs = clips.flatMap((c) => ['-i', c]);
  const chains = clips.map((_, i) => `[${i}:a]aresample=48000,aformat=channel_layouts=mono,apad=pad_dur=${gap}[a${i}]`);
  const concat = `${clips.map((_, i) => `[a${i}]`).join('')}concat=n=${clips.length}:v=0:a=1[c];[c]adelay=delays=${Math.round(lead * 1000)}:all=1[out]`;
  const outAudio = path.resolve(a.audio);
  fs.mkdirSync(path.dirname(outAudio), {recursive: true});
  run('ffmpeg', ['-v', 'error', '-y', ...inputs, '-filter_complex', [...chains, concat].join(';'), '-map', '[out]', outAudio]);
  audio = path.basename(outAudio);
  console.log(`audio → ${outAudio}`);
} else {
  // 按字数估：只数汉字、字母和数字
  const cps = Number(a.cps);
  let t = lead;
  readLines(a.text).forEach((line, i) => {
    const n = (line.text.match(/[\p{L}\p{N}]/gu) ?? []).length;
    const d = Math.max(1, n / cps);
    cues.push({id: `c${i + 1}`, text: line.text, subtitle: line.subtitle, start: round(t), end: round(t + d)});
    t += d + gap;
  });
}

const total = round((cues.at(-1)?.end ?? 0) + gap);
const out = path.resolve(a.out);
fs.mkdirSync(path.dirname(out), {recursive: true});
fs.writeFileSync(out, JSON.stringify({audio, estimated: !a.clips, total, cues}, null, 2) + '\n');
console.log(`cues → ${out}`);
for (const c of cues) console.log(`${c.id}  ${c.start.toFixed(2)}–${c.end.toFixed(2)}s  ${c.subtitle ? '[字幕] ' : ''}${c.text}`);
