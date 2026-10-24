import {cue, VO_FRAMES} from './vo';
export {FPS, WIDTH, HEIGHT} from './fps';

// 所有镜头的起止帧集中在这里。镜头卡在配音句子的边界上，同时保证动画需要的最短时长；
// 配音一换，重新生成 vo.json，节奏自动跟上
const atLeast = (start: number, min: number, cueEnd: number) => ({start, end: Math.max(start + min, cueEnd + 6)});
export const S1 = atLeast(0, 90, cue('c1').end); // 微距：单颗点亮
export const S2 = atLeast(S1.end, 120, cue('c2').end); // 后拉：逐颗点亮 + 计数
export const S3 = atLeast(S2.end, 60, cue('c3').end + 9); // 全景收尾
export const DURATION = Math.max(S3.end, VO_FRAMES);

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const prog = (f: number, a: number, b: number) => clamp01((f - a) / (b - a));
export const smooth = (t: number) => t * t * (3 - 2 * t);
export const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export const easeOutExpo = (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
// a→b 淡入，c→d 淡出
export const envelope = (f: number, a: number, b: number, c: number, d: number) =>
  Math.min(smooth(prog(f, a, b)), 1 - smooth(prog(f, c, d)));
// 分段关键帧插值：[[帧, 值], ...]
export const keys = (f: number, ks: [number, number][], ease: (t: number) => number = smooth) => {
  if (f <= ks[0][0]) return ks[0][1];
  for (let i = 1; i < ks.length; i++) {
    if (f <= ks[i][0]) {
      const [f0, v0] = ks[i - 1];
      const [f1, v1] = ks[i];
      return lerp(v0, v1, ease((f - f0) / (f1 - f0)));
    }
  }
  return ks[ks.length - 1][1];
};
