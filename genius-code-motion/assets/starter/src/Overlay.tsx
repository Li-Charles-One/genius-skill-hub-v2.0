import * as THREE from 'three';
import {AbsoluteFill, Audio, staticFile, useCurrentFrame} from 'remotion';
import {project} from './camera';
import {Scene} from './Scene';
import {BEAD, FRONT_Z, HERO, litCount} from './state';
import {S1, S2, S3, envelope, prog, smooth} from './timeline';
import {Callout, DIM, INK, MONO, Panel, SANS, Subtitle, rise} from './hud';
import {OPTS} from './options';
import {VO} from './vo';
import {FPS} from './fps';

const heroCorner = new THREE.Vector3(HERO.x + BEAD.w * 0.45, HERO.y + BEAD.h * 0.45, FRONT_Z + BEAD.d);

export const Overlay: React.FC = () => {
  const f = useCurrentFrame();
  const a = project(f, heroCorner);
  const countOpacity = envelope(f, S2.start, S2.start + 12, S3.end, S3.end + 1);
  return (
    <AbsoluteFill>
      <Callout f={f} at={S1.start + 40} out={S2.start + 10} x={a.x} y={a.y} dir={1} title="单颗灯珠" sub="标注跟着 3D 点走" />
      {countOpacity > 0 && (
        <AbsoluteFill style={{opacity: countOpacity}}>
          <Panel style={{right: 90, bottom: 140, width: 300, ...rise(f, S2.start)}}>
            <div style={{fontFamily: MONO, fontSize: 110, fontWeight: 200, color: INK, lineHeight: 1}}>
              {litCount(f)}
              <span style={{fontFamily: SANS, fontSize: 32, color: DIM, marginLeft: 10}}>颗</span>
            </div>
          </Panel>
        </AbsoluteFill>
      )}
      {/* 新增口播（vo.txt 里行首带 +）定稿前显示成字幕 */}
      {OPTS.subtitles &&
        VO.cues
          .filter((c) => c.subtitle)
          .map((c) => <Subtitle key={c.id} f={f} from={Math.round(c.start * FPS)} to={Math.round(c.end * FPS) + 8} text={c.text} />)}
    </AbsoluteFill>
  );
};

const FadeIn: React.FC = () => {
  const f = useCurrentFrame();
  return <AbsoluteFill style={{background: '#000', opacity: 1 - smooth(prog(f, 0, 20))}} />;
};

// layer = all：完整成片；3d：只出 3D；hud：只出透明叠加层（导出带透明通道的格式）
export const Video: React.FC = () => (
  <AbsoluteFill style={{background: OPTS.layer === 'hud' ? 'transparent' : '#000'}}>
    {OPTS.layer !== 'hud' && <Scene />}
    {OPTS.layer !== '3d' && <Overlay />}
    {OPTS.layer !== 'hud' && <FadeIn />}
    {OPTS.layer === 'all' && VO.audio && <Audio src={staticFile(VO.audio)} />}
  </AbsoluteFill>
);
