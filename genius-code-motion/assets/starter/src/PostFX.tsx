import * as THREE from 'three';
import {useMemo} from 'react';
import {useFrame, useThree} from '@react-three/fiber';
import {useCurrentFrame} from 'remotion';
import {
  BloomEffect,
  DepthOfFieldEffect,
  EffectComposer,
  EffectPass,
  NoiseEffect,
  RenderPass,
  ToneMappingEffect,
  ToneMappingMode,
  VignetteEffect,
} from 'postprocessing';
import {getCam} from './camera';
import {HEIGHT, S2, WIDTH, lerp, prog, smooth} from './timeline';
import {OPTS} from './options';

// 手动后期管线：@react-three/postprocessing 的 <EffectComposer> 在 Remotion 逐帧渲染下会输出全黑
export const PostFX: React.FC = () => {
  const f = useCurrentFrame();
  const {gl, scene, camera} = useThree();
  const fx = useMemo(() => {
    // 小样模式：关掉多重采样和景深，换渲染速度
    const composer = new EffectComposer(gl, {frameBufferType: THREE.HalfFloatType, multisampling: OPTS.draft ? 0 : 4});
    const dof = new DepthOfFieldEffect(camera, {focusDistance: 0.05, focusRange: 0.02, bokehScale: 1, resolutionScale: 1});
    const bloom = new BloomEffect({mipmapBlur: true, luminanceThreshold: 0.95, luminanceSmoothing: 0.2, intensity: 1.1, radius: 0.78});
    // 颗粒默认不透明度是 100%，必须压低
    const noise = new NoiseEffect({premultiply: true});
    noise.blendMode.opacity.value = 0.04;
    composer.addPass(new RenderPass(scene, camera));
    if (!OPTS.draft) composer.addPass(new EffectPass(camera, dof));
    composer.addPass(
      new EffectPass(
        camera,
        bloom,
        // 渲到中间缓冲时渲染器不做色调映射，在这里补
        new ToneMappingEffect({mode: ToneMappingMode.ACES_FILMIC}),
        new VignetteEffect({offset: 0.3, darkness: 0.7}),
        noise,
      ),
    );
    composer.setSize(WIDTH, HEIGHT);
    return {composer, dof};
  }, [gl, scene, camera]);

  // 景深每帧跟着镜头对焦：微距浅景深，拉开后整体清晰
  const cam = getCam(f);
  const macro = 1 - smooth(prog(f, S2.start + 10, S2.start + 80));
  fx.dof.cocMaterial.focusDistance = cam.focus;
  fx.dof.cocMaterial.focusRange = lerp(cam.focus * 2.5, cam.focus * 0.25, macro);
  fx.dof.bokehScale = lerp(0.5, 5, macro);

  useFrame(() => {
    gl.toneMapping = THREE.NoToneMapping;
    fx.composer.render();
  }, 1);
  return null;
};
