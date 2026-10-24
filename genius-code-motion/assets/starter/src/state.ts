import {S1, S2, prog, smooth} from './timeline';

// 由帧号算出的业务状态：3D 和标注共用，画面里亮几颗、计数就是几
export const PRODUCT = {w: 0.6, h: 0.32, depth: 0.03};
export const FRONT_Z = PRODUCT.depth / 2;
export const BEAD = {w: 0.012, h: 0.012, d: 0.003};

export const BEADS = Array.from({length: 12}, (_, i) => ({
  x: -0.22 + i * 0.04,
  y: 0,
  warm: i % 2 === 0,
  lightAt: i === 0 ? S1.start + 30 : S2.start + 10 + i * 6,
}));
export const HERO = BEADS[0];

export const beadLevel = (f: number, i: number) => {
  const b = BEADS[i];
  const ramp = smooth(prog(f, b.lightAt, b.lightAt + 8));
  const flash = f > b.lightAt + 8 ? 0.5 * Math.exp(-(f - b.lightAt - 8) / 5) : 0;
  return ramp + flash;
};
export const litCount = (f: number) => BEADS.filter((b) => f >= b.lightAt + 4).length;
