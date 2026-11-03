# Genius Voice Usage, Config, Limits

## Prerequisites

```bash
# macOS
brew install ffmpeg
# Ubuntu / Debian
sudo apt install ffmpeg
```

```powershell
# Windows
winget install Gyan.FFmpeg
```

The script uses only the Python standard library (3.9+). Verify with `python3 scripts/voice.py --check` (Windows: `python scripts\voice.py --check`): `ok: true` means ffmpeg, ffprobe, the Doubao ASR key and all three MiMo TTS models are reachable.

## Setup (`scripts/.env`)

```bash
# ASR: Doubao speech key with resource volc.seedasr.auc enabled
DOUBAO_API_KEY=your-doubao-key
# TTS
MIMO_API_KEY=your-mimo-key
# Pay-as-you-go keys use the default; Token Plan keys need their regional URL, e.g.
# MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
```

Process environment variables override `scripts/.env`. ASR calls `https://openspeech.bytedance.com/api/v3/auc/bigmodel/{submit,query}` with `X-Api-Key`. MiMo default base URL: `https://api.xiaomimimo.com/v1`; both `api-key` and `Authorization: Bearer` headers are sent.

## Examples

```bash
# ASR
python3 scripts/voice.py asr meeting.m4a --language zh
python3 scripts/voice.py asr interview.mp4 --speakers --output json --out interview.json

# TTS, preset voice + style
python3 scripts/voice.py tts "（温柔）晚安，今天辛苦了。" --voice 冰糖 --out goodnight.mp3
python3 scripts/voice.py tts --text-file script.txt --voice 苏打 --style "像深夜电台主持人，语速偏慢" --out narration.wav

# Clone / design
python3 scripts/voice.py tts "要克隆的台词" --clone sample.m4a --out cloned.wav
python3 scripts/voice.py tts --text-file story.txt --design "低沉沙哑的中年男声，语速偏慢" --out story.wav
```

On Windows, write `python scripts\voice.py …`; pass long text with `--text-file` rather than shell quoting.

## Output

- ASR text mode prints one utterance per line, prefixed `[S1]`, `[S2]`… with `--speakers`. `--output json` prints `{file, model, language, duration, segments, text}`; each segment is one utterance: `{start, end, text, speaker?, emotion?, gender?, speech_rate?, words: [{start, end, text}]}`, times in seconds. `speech_rate` is characters per second; emotion and gender are unreliable where voices overlap.
- TTS writes 24 kHz mono 16-bit audio and prints `{"out": <absolute path>, "seconds": <duration>}`.
- Progress goes to stderr as `[genius-voice] …`.

| Code | Exit | Typical cause |
|---|---|---|
| `INPUT_NOT_FOUND` | 3 | audio, reference or text file does not exist |
| `UNSUPPORTED_FORMAT` | 4 | ffmpeg cannot decode the input; empty text; clone reference under 1s or over 10MB |
| `DEPENDENCY_MISSING` | 5 | `ffmpeg` / `ffprobe` not on PATH |
| `PROVIDER_ERROR` | 6 | missing key, HTTP error, ASR status code other than success/processing/silence, content filter, empty audio |
| `TIMEOUT` | 7 | no API response or unfinished ASR job within `VOICE_TIMEOUT`, or ffmpeg timed out |

Other errors exit 1; `--check` failing exits 2. HTTP 429/5xx and network errors retry after 5s / 15s / 30s.

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

## Measured limits

| Env | Default | Why |
|---|---|---|
| `VOICE_TTS_CHUNK_CHARS` | `150` | one 503-char request garbled a sentence mid-way (round-trip similarity 0.93); ~100–140-char chunks scored 0.996+ |
| `VOICE_TIMEOUT` | `600` | seconds per API request, and the longest wait for one ASR job |

ASR (measured): 5 min of speech ≈ 28s, 8 min ≈ 43s per pass; a 216s multi-speaker video took 36s for both passes. Audio is sent inline as 16 kHz mono 64 kbps mp3; above 100MB base64 (~3.5h) the provider wants `audio.url`, which the script does not use. Status `20000003` (no valid speech) maps to `NO_SPEECH_DETECTED`. The speaker pass uses `ssd_version: "200"` (it separated 5 speakers where 300 merged them into 3) and changes wording (100 → 一百), so only its labels are kept, plus utterances that pass 1 missed.

TTS: MiMo returns wav by default.

## Verification

- [ ] `python3 scripts/voice.py --check` → `ok: true`, `asr: ok`, three TTS models listed
- [ ] `python3 scripts/voice.py tts "你好，这是一段测试。" --out t.wav` then `python3 scripts/voice.py asr t.wav -l zh` returns the same sentence
- [ ] A multi-person recording with `--speakers` shows `[S1]`/`[S2]` lines and the last utterance ends near the file duration
- [ ] Silent audio prints `NO_SPEECH_DETECTED`
- [ ] `--clone` and `--design` each produce a playable file; listen to confirm the timbre
- [ ] A missing file exits 3 with `INPUT_NOT_FOUND`
