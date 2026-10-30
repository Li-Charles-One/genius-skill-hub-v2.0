#!/usr/bin/env node
// 在公用3D动画工作台里新建一个项目文件夹：复制起步模板到 src/<项目>/，生成带 <Folder> 的 index.tsx，并挂到 src/Root.tsx。
// 在工作台根目录运行：
//   node <skill>/scripts/new_project.mjs <项目名>
// 项目名用小写英文、数字和连字符（例如 air-purifier）；合成 ID 是 <项目名>-main。
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const name = process.argv[2];
if (!name || !/^[a-z0-9]+(-[a-z0-9]+)*$/.test(name)) {
  console.error('usage: node new_project.mjs <项目名>（小写英文、数字、连字符）');
  process.exit(2);
}
const starter = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../assets/starter');
const root = 'src/Root.tsx';
if (!fs.existsSync(root) || !fs.existsSync('node_modules/remotion')) {
  console.error('请在装好依赖的公用3D动画工作台根目录运行');
  process.exit(1);
}
const dir = path.join('src', name);
if (fs.existsSync(dir)) {
  console.error(`${dir} 已存在`);
  process.exit(1);
}

fs.mkdirSync(dir, {recursive: true});
for (const f of fs.readdirSync(path.join(starter, 'src'))) {
  if (f !== 'index.ts' && f !== 'Root.tsx') fs.copyFileSync(path.join(starter, 'src', f), path.join(dir, f));
}
fs.copyFileSync(path.join(starter, 'vo.txt'), path.join(dir, 'vo.txt'));
fs.cpSync(path.join(starter, 'props'), path.join(dir, 'props'), {recursive: true});
fs.mkdirSync(path.join('public', name), {recursive: true});
fs.mkdirSync(path.join('out', name), {recursive: true});

const comp = name.replace(/(^|-)([a-z0-9])/g, (_, __, c) => c.toUpperCase());
fs.writeFileSync(
  path.join(dir, 'index.tsx'),
  `import {Composition, Folder} from 'remotion';
import {Video} from './Overlay';
import {DURATION, FPS, HEIGHT, WIDTH} from './timeline';

// ${name}：口播在 vo.txt，配音放 public/${name}/，成片输出到 out/${name}/。
export const ${comp}: React.FC = () => (
  <Folder name="${name}">
    <Composition id="${name}-main" component={Video} durationInFrames={DURATION} fps={FPS} width={WIDTH} height={HEIGHT} />
  </Folder>
);
`,
);

const IMPORTS = '// 项目导入（new_project.mjs 在这行上面加）';
const MOUNTS = '{/* 项目挂载（new_project.mjs 在这行上面加） */}';
let r = fs.readFileSync(root, 'utf8');
if (!r.includes(IMPORTS) || !r.includes(MOUNTS)) {
  console.error(`${root} 里找不到标记行，请手动加：import {${comp}} from './${name}'; 和 <${comp} />`);
  process.exit(1);
}
r = r.replace(IMPORTS, `import {${comp}} from './${name}';\n${IMPORTS}`).replace(MOUNTS, `<${comp} />\n    ${MOUNTS}`);
fs.writeFileSync(root, r);

console.log(`created ${dir}/（合成 ${name}-main），已挂到 ${root}`);
console.log(`口播：src/${name}/vo.txt；配音：public/${name}/；渲染参数：src/${name}/props/；成片：out/${name}/`);
