# Prompt Law — Seedance 2.0 Shotlist

## Style Prefix

**Always check the conversation first** — if the user uploaded or pasted a custom style prefix, use that exact text verbatim.

If none is provided, use this default:

```
Style: 8K IMAX. Photorealistic — no 3D render, no game engine.
Lighting: Natural light only — contre-jour backlight, camera on shadow side, atmospheric haze throughout. Key light from sky and windows only. No artificial lighting.
Color: 60:30:10 — dominant / secondary / accent.
Camera: Physical cine lens. 180° shutter motion blur.
Skin: Pore-level realism — vellus hair, asymmetric moles, capillary flush, pore-shadow matching on-set light.
Acting: Hollywood — micro-pauses before reactions, precise eye-line, living eyes with catch-lights, chest rise from breathing. Characters never standing, always reacting.
Physics: Gravity and inertia respected — mass has real weight, correct contact shadows. No floating props.
Composition: Rule of thirds + golden ratio. Every person moving from frame one.
Continuity: Characters, props, environment identical across every cut. No identity drift.
Technical: 24fps smooth motion. 8K detail. No jitter.
Audio: Environmental SFX only. No music. No subtitles.
```

The Style Prefix appears **once** at the top of the HTML in a collapsible block, **and** is prepended verbatim to every prompt's copy-block so each prompt is standalone in Seedance.

## Prompt structure (this is the law)

Every prompt follows this exact order, top to bottom:

```
[STYLE PREFIX — full block, verbatim]

Characters:
[Character anchors — short, specific, vivid. Only characters in this prompt. Carry forward state from previous scenes — wet hair from rain in scene 3, blood on knuckles from the fight in scene 5, same scar, same wardrobe unless they changed clothes on screen.]

Scene:
[1–2 sentences. What's happening, where, when. Geo-spatial — where each character is positioned relative to the location and to each other. "Anna stands at the kitchen window, back to the room. Marco enters from the hallway, stops in the doorway six feet behind her."]

CUT 1 — [shot type, lens feel, movement]:
[What happens in this shot. Acting beat, gesture, eye-line, breath, micro-pause. What the camera is doing. What the light is doing. Diegetic sound if relevant.]

CUT 2 — [shot type, lens feel, movement]:
[Next beat. Same level of detail.]

CUT 3 — [shot type, lens feel, movement]:
[Final beat of this 15-second prompt.]
```

## 15-second target

Each prompt **targets 15 seconds** of screen time. Write enough cuts and acting beats to fill the full 15 seconds — Seedance generates a fixed-length clip; avoid dead air at the end.

- Most 15-second prompts hold **1–3 cuts** depending on how much the cuts breathe.
- A long held single shot is valid if the moment carries it.
- A rapid-fire 4-cut sequence is valid if the action calls for it.
- Either way: design so all 15 seconds are working.

If a scene is longer than 15 seconds (most are), split across multiple prompts under the same scene number: `3a`, `3b`, `3c`. Each is its own 15-second block with its own full Style Prefix and Characters block. Continuity must hold across them — appearance, position, emotional state, props.

## English only

Prompt text in the HTML is always English even if the user writes in another language.

## What never becomes a visible HTML block

Continuity tracker, character-state notes, pacing notes — keep them in your head; surface only as concrete language inside Characters and CUT lines.
