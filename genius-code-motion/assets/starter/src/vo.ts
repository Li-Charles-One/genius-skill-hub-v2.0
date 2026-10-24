import data from './vo.json';
import {FPS} from './fps';

// 配音时间点：由 scripts/vo_timeline.mjs 生成。有真实配音时 audio 是 public/ 下的文件名，estimated 为 false
export type Cue = {id: string; text: string; subtitle: boolean; start: number; end: number};
export const VO = data as {audio: string | null; estimated: boolean; total: number; cues: Cue[]};

const find = (id: string) => {
  const c = VO.cues.find((x) => x.id === id);
  if (!c) throw new Error(`vo.json 里没有 ${id}`);
  return c;
};
// 句子的起止帧，镜头卡在这上面
export const cue = (id: string) => {
  const c = find(id);
  return {start: Math.round(c.start * FPS), end: Math.round(c.end * FPS)};
};
export const VO_FRAMES = Math.ceil(VO.total * FPS);
