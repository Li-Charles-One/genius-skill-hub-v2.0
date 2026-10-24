import {getInputProps} from 'remotion';

// 渲染参数：通过 --props=<json 文件> 传入，不传就是完整成片
//   draft: true       低清小样，关掉景深等耗时效果（配合 --scale=0.5）
//   subtitles: false  不要字幕（给剪辑自己加）
//   layer: "3d"       只出 3D 画面；"hud" 只出透明的标注叠加层
type Options = {draft?: boolean; subtitles?: boolean; layer?: 'all' | '3d' | 'hud'};
const p = getInputProps<Options>();
export const OPTS = {draft: p.draft === true, subtitles: p.subtitles !== false, layer: p.layer ?? 'all'};
