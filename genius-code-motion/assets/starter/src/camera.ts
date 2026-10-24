import * as THREE from 'three';
import {HERO, FRONT_Z, BEAD} from './state';
import {S2, WIDTH, HEIGHT, keys, lerp} from './timeline';

export type CamState = {pos: THREE.Vector3; target: THREE.Vector3; up: THREE.Vector3; fov: number; focus: number};

const UP = new THREE.Vector3(0, 1, 0);

// 从目标点沿斜前方 tilt 角退 d 米。正对拍摄时 tilt = 0
const orbit = (tx: number, ty: number, d: number, tilt: number): CamState => {
  const target = new THREE.Vector3(tx, ty, FRONT_Z + BEAD.d);
  const dir = new THREE.Vector3(Math.sin(tilt) * 0.6, -Math.sin(tilt) * 0.5, Math.cos(tilt)).normalize();
  const pos = target.clone().addScaledVector(dir, d);
  return {pos, target, up: UP, fov: 35, focus: d};
};

export const getCam = (f: number): CamState => {
  // 大幅推拉按对数距离插值：从 5cm 拉到 1.2m 看起来是匀速的
  const d = Math.exp(
    keys(f, [
      [S2.start, Math.log(0.05)],
      [S2.end - 10, Math.log(1.2)],
    ]),
  );
  const c = keys(f, [
    [S2.start + 10, 0],
    [S2.end - 20, 1],
  ]);
  const tilt = keys(f, [
    [0, 0.65],
    [S2.start, 0.6],
    [S2.end - 20, 0.08],
  ]);
  return orbit(lerp(HERO.x, 0, c), lerp(HERO.y, 0, c), d, tilt);
};

export const applyCam = (cam: THREE.PerspectiveCamera, s: CamState) => {
  cam.position.copy(s.pos);
  cam.up.copy(s.up);
  cam.fov = s.fov;
  // 近裁剪面跟着拍摄距离走，远景时贴得很近的两层面才不会互相遮挡
  cam.near = Math.min(0.3, Math.max(0.002, s.focus * 0.08));
  cam.far = 60;
  cam.aspect = WIDTH / HEIGHT;
  cam.lookAt(s.target);
  cam.updateProjectionMatrix();
  cam.updateMatrixWorld(true);
};

// 叠加层用：同一个相机函数把 3D 点投影成屏幕像素
const projCam = new THREE.PerspectiveCamera();
export const project = (f: number, p: THREE.Vector3) => {
  applyCam(projCam, getCam(f));
  const v = p.clone().project(projCam);
  return {x: ((v.x + 1) / 2) * WIDTH, y: ((1 - v.y) / 2) * HEIGHT};
};
