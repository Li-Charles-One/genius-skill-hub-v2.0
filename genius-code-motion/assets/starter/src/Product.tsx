import * as THREE from 'three';
import {useMemo} from 'react';
import {useCurrentFrame} from 'remotion';
import {RoundedBoxGeometry} from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import {BEAD, BEADS, FRONT_Z, PRODUCT, beadLevel} from './state';
import {S2, lerp, prog, smooth} from './timeline';

const WARM = new THREE.Color(1.0, 0.64, 0.33);
const COOL = new THREE.Color(0.8, 0.9, 1.0);

// 演示产品：一块圆角板，正面一排灯珠。按项目换成真实结构
export const Product: React.FC = () => {
  const f = useCurrentFrame();
  const geo = useMemo(
    () => ({
      body: new RoundedBoxGeometry(PRODUCT.w, PRODUCT.h, PRODUCT.depth, 6, 0.012),
      bead: new RoundedBoxGeometry(BEAD.w, BEAD.h, BEAD.d, 3, 0.001),
      core: new THREE.PlaneGeometry(BEAD.w * 0.7, BEAD.h * 0.7),
    }),
    [],
  );
  // 材质只建一次，每帧在函数体里改属性
  const cores = useMemo(
    () =>
      BEADS.map(
        (b) =>
          new THREE.MeshPhysicalMaterial({
            color: b.warm ? '#f2b45e' : '#f4e07c',
            roughness: 0.3,
            clearcoat: 1,
            emissive: b.warm ? WARM : COOL,
            emissiveIntensity: 0,
            toneMapped: false, // 发光强度超过 1 才能触发辉光
            polygonOffset: true,
            polygonOffsetFactor: -2,
            polygonOffsetUnits: -2,
          }),
      ),
    [],
  );
  // 微距时发光体占满画面，强度低一点；拉远后发光体变小，强度要更高
  const gain = lerp(4, 9, smooth(prog(f, S2.start + 20, S2.end - 20)));
  cores.forEach((m, i) => (m.emissiveIntensity = beadLevel(f, i) * gain));

  return (
    <group>
      <mesh geometry={geo.body}>
        <meshStandardMaterial color="#e9e8e3" roughness={0.45} />
      </mesh>
      {BEADS.map((b, i) => (
        <group key={i} position={[b.x, b.y, FRONT_Z + BEAD.d / 2]}>
          <mesh geometry={geo.bead}>
            <meshPhysicalMaterial color="#f6f5f0" roughness={0.35} clearcoat={0.6} />
          </mesh>
          <mesh geometry={geo.core} material={cores[i]} position={[0, 0, BEAD.d / 2 + 0.0002]} />
        </group>
      ))}
    </group>
  );
};
