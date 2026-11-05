# TTS module: read text aloud (`tts`)

Models `mimo-v2.5-tts` (preset voices), `mimo-v2.5-tts-voiceclone` (`--clone`), `mimo-v2.5-tts-voicedesign` (`--design`). Key: `MIMO_API_KEY` (`references/setup.md`).

```bash
python3 "<skill_dir>/scripts/voice.py" tts "<text>" | --text-file F | -  [--voice ID | --clone REF | --design "..."] [--style "..."] [--out FILE]
```

```bash
# Preset voice + style
python3 scripts/voice.py tts "（温柔）晚安，今天辛苦了。" --voice 冰糖 --out goodnight.mp3
python3 scripts/voice.py tts --text-file script.txt --voice 苏打 --style "像深夜电台主持人，语速偏慢" --out narration.wav
# Clone / design
python3 scripts/voice.py tts "要克隆的台词" --clone sample.m4a --out cloned.wav
python3 scripts/voice.py tts --text-file story.txt --design "低沉沙哑的中年男声，语速偏慢" --out story.wav
```

## Running it

- TTS splits text into ≤150-char sentence chunks and joins the audio. A leading style tag such as `(温柔)` or `（粤语）` applies to every chunk; inline tags such as `（深呼吸）` stay where they are. `--style` is a natural-language direction (with `--design` it is appended to the description).
- `--clone` sends the whole reference file, so pass a prepared clip: one speaker, no music or overlapping voices, about 5–15s, cut at pauses (`ffmpeg -ss START -to END -i IN -vn -ac 1 ref.wav`). To clone one person from a multi-speaker recording or video, first find their stretches with `asr --speakers --output json` (utterance times + speaker labels, `references/asr.md`), then cut and clone.

## Voices and style

Preset voices (`--voice`, `mimo-v2.5-tts` only):

| ID | Language | Gender |
|---|---|---|
| `mimo_default` | 冰糖 on the China cluster, Mia elsewhere | — |
| `冰糖` / `茉莉` | Chinese | female |
| `苏打` / `白桦` | Chinese | male |
| `Mia` / `Chloe` | English | female |
| `Milo` / `Dean` | English | male |

Three ways to steer delivery; they combine:

1. **`--style`** — natural language in the user message, e.g. `语速偏慢，带一点笑意`. Longer "director" form: 角色 / 场景 / 指导 (pace, breath, pauses, stress). Works with presets and `--clone`.
2. **Leading style tag** — `(风格)` at the very start of the text; `()`, `（）` or `[]`; several styles in one bracket.
   - Emotion: 开心 悲伤 愤怒 恐惧 惊讶 兴奋 委屈 平静 冷漠 怅然 欣慰 无奈 愧疚 释然 嫉妒 厌倦 忐忑 动情
   - Tone: 温柔 高冷 活泼 严肃 慵懒 俏皮 深沉 干练 凌厉
   - Timbre / persona: 磁性 醇厚 清亮 空灵 稚嫩 苍老 甜美 沙哑 醇雅 夹子音 御姐音 正太音 大叔音 台湾腔
   - Dialect: 东北话 四川话 河南话 粤语
   - Singing: `(唱歌)` — preset voices only, Chinese lyrics recommended.
3. **Inline audio tags** anywhere in the text, e.g. `（深呼吸）`, `（轻笑）`, `（叹气）`, `（哽咽）`, `（紧张）`, `（声音颤抖）`.

Clone (`--clone`): reference must end up as mp3/wav ≤10MB base64; other formats or larger files are re-encoded to 16 kHz mono mp3 first. No duration limit is documented.

Design (`--design`): 1–4 sentences covering gender/age, timbre, emotion and pace (optionally persona, scene, era). Avoid contradictions, vague words (普通的, 正常的) and studio effects (reverb, EQ). Chinese or English.

## Output

MiMo returns wav by default. TTS writes 24 kHz mono 16-bit audio (non-wav outputs at 64 kbps) and prints `{"out": <absolute path>, "seconds": <duration>}`.

## Report

The output path, duration, and voice used (preset id, clone reference, or design description).

## Measured

| Env | Default | Why |
|---|---|---|
| `VOICE_TTS_CHUNK_CHARS` | `150` | one 503-char request garbled a sentence mid-way (round-trip similarity 0.93); ~100–140-char chunks scored 0.996+ |

## Gotchas

- TTS on one long request (≈250+ chars) skips, repeats or garbles sentences. Keep `VOICE_TTS_CHUNK_CHARS` at 150 or below.
- `--clone` on a very short line (≤8 chars) sent on its own is unreliable: it invents words (measured: "又是完美的一天。" came back followed by "帮我导航到大湾公园"), misreads ("嗨，我是 Leo" as "哎，好实力哦"), drops characters, and once left a 4.5s gap mid-line. Piling on direction drags the pace: a leading `(温柔 开心)`, inline `（轻叹）` and "……" plus a hard order in `--style` such as "每秒三个字" slowed it to 1–2 chars/s. The same ~100-char script in one request came back word-perfect. Generate the whole passage in one request, skip hard pace numbers, and set pauses in the edit.
- A designed voice has no reusable id. The script designs chunk 1 and clones it for later chunks; to reuse a designed voice later, pass its output file to `--clone`.
- Preset voices, cloning and design are separate models; they cannot be combined in one call. Singing `(唱歌)` works only with preset voices; for a song with accompaniment use `gen` (`references/gen.md`).

## Verification

- [ ] `python3 scripts/voice.py tts "你好，这是一段测试。" --out t.wav` then `python3 scripts/voice.py asr t.wav --language zh` returns the same sentence
- [ ] `--clone` and `--design` each produce a playable file; listen to confirm the timbre
