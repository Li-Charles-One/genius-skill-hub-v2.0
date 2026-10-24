import {AbsoluteFill} from 'remotion';
import {HEIGHT, WIDTH, easeOutExpo, envelope, lerp, prog, smooth} from './timeline';

export const MONO = '"SF Mono", Menlo, Consolas, monospace';
export const SANS = '"PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
export const INK = 'rgba(255,255,255,0.94)';
export const DIM = 'rgba(255,255,255,0.6)';
export const LINE = 'rgba(255,255,255,0.65)';
export const SHADOW = '0 2px 16px rgba(0,0,0,0.75), 0 0 3px rgba(0,0,0,0.6)';

// 由下往上浮入
export const rise = (f: number, a: number, dist = 16) => ({
  opacity: smooth(prog(f, a, a + 14)),
  transform: `translateY(${lerp(dist, 0, easeOutExpo(prog(f, a, a + 30)))}px)`,
});

// 字幕：新增口播定稿前用
export const Subtitle: React.FC<{f: number; from: number; to: number; text: string}> = ({f, from, to, text}) => {
  const o = envelope(f, from, from + 8, to - 8, to);
  if (o <= 0) return null;
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 56, opacity: o}}>
      <div style={{fontFamily: SANS, fontSize: 40, color: '#fff', textShadow: SHADOW, padding: '6px 22px', background: 'rgba(0,0,0,0.28)', borderRadius: 6}}>
        {text}
      </div>
    </AbsoluteFill>
  );
};

// 引线标注：锚点 → 斜线 → 横线 + 文字。锚点坐标来自 project()
export const Callout: React.FC<{f: number; at: number; out: number; x: number; y: number; dir: 1 | -1; title: string; sub?: string}> = ({
  f,
  at,
  out,
  x,
  y,
  dir,
  title,
  sub,
}) => {
  const o = envelope(f, at, at + 10, out, out + 12);
  if (o <= 0) return null;
  const draw = easeOutExpo(prog(f, at, at + 26));
  const bx = x + dir * 60;
  const by = y - 60;
  const len = 260;
  const d1 = Math.min(1, draw * 2.5);
  const ex = bx + dir * len * Math.max(0, draw * 1.4 - 0.4);
  return (
    <AbsoluteFill style={{opacity: o}}>
      <svg width={WIDTH} height={HEIGHT} style={{position: 'absolute'}}>
        <circle cx={x} cy={y} r={6} fill="none" stroke={LINE} strokeWidth={1.6} />
        <polyline points={`${x},${y} ${lerp(x, bx, d1)},${lerp(y, by, d1)} ${ex},${by}`} fill="none" stroke={LINE} strokeWidth={1.6} />
      </svg>
      <div style={{position: 'absolute', left: dir > 0 ? bx + 4 : bx - len - 4, width: len, top: by - (sub ? 80 : 50), textAlign: dir > 0 ? 'left' : 'right', textShadow: SHADOW, ...rise(f, at + 12, 10)}}>
        <div style={{fontFamily: SANS, fontSize: 34, color: INK, letterSpacing: 3}}>{title}</div>
        {sub && <div style={{fontFamily: SANS, fontSize: 22, color: DIM, marginTop: 4}}>{sub}</div>}
      </div>
    </AbsoluteFill>
  );
};

export const Panel: React.FC<{style?: React.CSSProperties; children: React.ReactNode}> = ({style, children}) => (
  <div
    style={{
      position: 'absolute',
      background: 'linear-gradient(180deg, rgba(10,10,12,0.62), rgba(10,10,12,0.42))',
      border: '1px solid rgba(255,255,255,0.12)',
      borderRadius: 10,
      padding: '20px 26px',
      ...style,
    }}
  >
    {children}
  </div>
);
