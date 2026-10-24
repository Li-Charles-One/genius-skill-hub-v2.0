import * as THREE from 'three';
import {useMemo} from 'react';
import {useThree} from '@react-three/fiber';
import {ThreeCanvas} from '@remotion/three';
import {useCurrentFrame} from 'remotion';
import {applyCam, getCam} from './camera';
import {PostFX} from './PostFX';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';
import {Product} from './Product';
import {BEAD, BEADS, FRONT_Z, HERO, beadLevel, litCount} from './state';
import {HEIGHT, S2, WIDTH, clamp01, keys, lerp, prog, smooth} from './timeline';

// 棚拍环境反射：白色塑料、金属、玻璃类产品建议设 0.2–0.4，质感提升最大。
// 它会提亮整个画面，开了以后要同时调低主光；要保持暗调 TVC 气氛就设小一点或设 0
const ENV_INTENSITY = 0;
const Env: React.FC = () => {
  const {gl, scene} = useThree();
  useMemo(() => {
    const pmrem = new THREE.PMREMGenerator(gl);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environmentIntensity = ENV_INTENSITY;
  }, [gl, scene]);
  return null;
};

const CameraRig: React.FC = () => {
  const f = useCurrentFrame();
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  applyCam(camera, getCam(f));
  return null;
};

// 主光跟着镜头目标走：微距时贴着打低角度侧光，强度 = 目标照度 × 距离²
const KeyLight: React.FC = () => {
  const f = useCurrentFrame();
  const light = useMemo(() => {
    const l = new THREE.SpotLight('#ffffff');
    l.angle = 0.6;
    l.penumbra = 1;
    l.decay = 2;
    return l;
  }, []);
  const cam = getCam(f);
  const t = clamp01((Math.log(cam.focus) - Math.log(0.05)) / (Math.log(1.2) - Math.log(0.05)));
  const off = new THREE.Vector3(lerp(0.07, 0.6, t), lerp(0.05, 0.5, t), lerp(0.04, 0.9, t));
  light.position.copy(cam.target).add(off);
  light.target.position.copy(cam.target);
  light.target.updateMatrixWorld();
  const e = keys(t, [
    [0, 0.6],
    [0.5, 0.3],
    [1, 0.5],
  ]);
  light.intensity = e * off.lengthSq() * smooth(prog(f, 0, 20));
  return <primitive object={light} />;
};

// 发光体亮起时照亮周围
const SpillLights: React.FC = () => {
  const f = useCurrentFrame();
  const hero = beadLevel(f, 0) * (1 - smooth(prog(f, S2.start + 20, S2.start + 70)));
  const all = litCount(f) / BEADS.length;
  return (
    <>
      <pointLight position={[HERO.x, HERO.y, FRONT_Z + BEAD.d + 0.006]} intensity={0.0002 * hero} decay={2} color="#ffd2a0" />
      <pointLight position={[0, 0, FRONT_Z + 0.08]} intensity={0.006 * all} decay={2} color="#fff0e0" />
    </>
  );
};

export const Scene: React.FC = () => (
  <ThreeCanvas width={WIDTH} height={HEIGHT}>
    <color attach="background" args={['#030305']} />
    <CameraRig />
    {ENV_INTENSITY > 0 && <Env />}
    <hemisphereLight args={['#e9eef7', '#2a2420', 0.25]} />
    <KeyLight />
    <SpillLights />
    <Product />
    <PostFX />
  </ThreeCanvas>
);
