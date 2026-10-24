import * as THREE from 'three';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {project} from './camera';
import {Scene} from './Scene';
import {BEAD, FRONT_Z, HERO, litCount} from './state';
import {S1, S2, S3, envelope, prog, smooth} from './timeline';
import {Callout, DIM, INK, MONO, Panel, SANS, Subtitle, rise} from './hud';

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
      <Subtitle f={f} from={S2.start + 20} to={S3.end} text="字幕：新增口播定稿前先放在这里" />
      <AbsoluteFill style={{background: '#000', opacity: 1 - smooth(prog(f, 0, 20))}} />
    </AbsoluteFill>
  );
};

export const Video: React.FC = () => (
  <AbsoluteFill style={{background: '#000'}}>
    <Scene />
    <Overlay />
  </AbsoluteFill>
);
