# 后期管线

## 为什么手动搭

`@react-three/postprocessing` 的 `<EffectComposer>` 在 Remotion 逐帧渲染下输出全黑（只开辉光也一样，根因未查实）。直接用 `postprocessing` 库自己搭管线，输出尺寸和渲染时机都自己控制，就能稳定出图。完整代码见 `assets/starter/src/PostFX.tsx`。

## 管线顺序

```text
RenderPass → 景深（单独一个 EffectPass）→ 辉光 + 色调映射 + 暗角 + 颗粒（同一个 EffectPass）
```

要点：

- `new EffectComposer(gl, {frameBufferType: HalfFloatType, multisampling: 4})`，再 `composer.setSize(宽, 高)`，尺寸写死成合成尺寸。
- 在 `useFrame(() => composer.render(), 1)` 里渲染。优先级大于 0，R3F 就不再自己渲染。
- **色调映射**：渲到中间缓冲时渲染器不做色调映射。在管线末尾加 `ToneMappingEffect({mode: ACES_FILMIC})`，并在 `useFrame` 里设 `gl.toneMapping = NoToneMapping`，避免重复映射。
- **颗粒**：`NoiseEffect` 默认不透明度是 100%，要设 `noise.blendMode.opacity.value` 到约 0.03–0.05。
- **暗角**：`VignetteEffect`，offset 约 0.3、darkness 约 0.6–0.75。

## 每帧更新的参数

- **景深**：`dof.cocMaterial.focusDistance` 和 `focusRange` 用世界单位（米），每帧从 `getCam(f).focus` 赋值。微距时 `focusRange` 取对焦距离的约 1/4、`bokehScale` 取 4–5；拉远后 `focusRange` 放大、`bokehScale` 降到约 0.5，画面整体清晰。
- **辉光**：`BloomEffect({mipmapBlur: true, luminanceThreshold: ≈0.95, intensity: ≈1.1, radius: ≈0.78})`。只有强度超过阈值的自发光才会发光，所以发光材质要设 `toneMapped: false`，强度大于 1。

## 排查后期问题

1. 先把整个后期关掉，确认 3D 本身能出图。
2. 再把效果逐个加回去，找出是哪一个出的问题。
3. 画面发灰、发白：检查色调映射是不是做了两次，或者一次都没做。
4. 部件消失，不要先怀疑景深，先查深度精度（见 `review-loop.md`）。
