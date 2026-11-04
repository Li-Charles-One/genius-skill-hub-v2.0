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

The script uses only the Python standard library (3.9+). Verify with `python3 scripts/voice.py --check` (Windows: `python scripts\voice.py --check`): `ok: true` means ffmpeg, ffprobe, the Doubao ASR key, Doubao audio generation (`audio_gen: ok`, a free empty-prompt probe) and all three MiMo TTS models are reachable.

## Setup (`scripts/.env`)

```bash
# ASR and gen: Doubao speech key with volc.seedasr.auc and Seed Audio enabled
DOUBAO_API_KEY=your-doubao-key
# Only if the account is granted a variant name, e.g. seed-audio-1.0-multilingual
# DOUBAO_AUDIO_MODEL=seed-audio-1.0
# TTS
MIMO_API_KEY=your-mimo-key
# Pay-as-you-go keys use the default; Token Plan keys need their regional URL, e.g.
# MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
```

Process environment variables override `scripts/.env`. ASR calls `https://openspeech.bytedance.com/api/v3/auc/bigmodel/{submit,query}` with `X-Api-Key`; `gen` calls `https://openspeech.bytedance.com/api/v3/tts/create` (synchronous, one request per scene) with the same key. MiMo default base URL: `https://api.xiaomimimo.com/v1`; both `api-key` and `Authorization: Bearer` headers are sent.

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

# Generation: sound effects / music / scene / timeline / references
python3 scripts/voice.py gen "雨夜的老街，持续的中雨打在铁皮屋檐上，远处偶尔一声闷雷，约 15 秒。" --out rain.wav
python3 scripts/voice.py gen "一首 30 秒的中文儿歌，木琴和尤克里里伴奏，童声欢快地唱：“小星星，眨眼睛……”" --out song.mp3
python3 scripts/voice.py gen --text-file timed-lines.txt --subtitle --out redub.wav
python3 scripts/voice.py gen "用@音频1的声音，惊讶地说：“你怎么来了？”" --ref voice.wav --out line.wav
python3 scripts/voice.py gen "开心地说：“今天天气真好。”" --speaker zh_female_cancan_uranus_bigtts --out sunny.wav
```

On Windows, write `python scripts\voice.py …`; pass long text with `--text-file` rather than shell quoting.

## Output

- ASR text mode prints one utterance per line, prefixed `[S1]`, `[S2]`… with `--speakers`. `--output json` prints `{file, model, language, duration, segments, text}`; each segment is one utterance: `{start, end, text, speaker?, emotion?, gender?, speech_rate?, words: [{start, end, text}]}`, times in seconds. `speech_rate` is characters per second; emotion and gender are unreliable where voices overlap.
- TTS writes 24 kHz mono 16-bit audio and prints `{"out": <absolute path>, "seconds": <duration>}`.
- Gen writes 48 kHz stereo 16-bit audio (non-wav outputs at 192 kbps) and prints `{"out", "seconds"}`; with `--subtitle` also `segments: [{start, end, text, words: [{start, end, text}]}]`, times in seconds.
- Progress goes to stderr as `[genius-voice] …`.

| Code | Exit | Typical cause |
|---|---|---|
| `INPUT_NOT_FOUND` | 3 | audio, reference or text file does not exist |
| `UNSUPPORTED_FORMAT` | 4 | ffmpeg cannot decode the input; empty text; clone reference under 1s or over 10MB; `gen` prompt over 3000 chars, timeline past 120s, more than 3 `--ref`, a `--ref` over 30s, `--image` not jpeg/png/webp ≤10MB or combined with `--ref`/`--speaker` |
| `DEPENDENCY_MISSING` | 5 | `ffmpeg` / `ffprobe` not on PATH |
| `PROVIDER_ERROR` | 6 | missing key, HTTP error, ASR status code other than success/processing/silence, content filter, empty audio |
| `TIMEOUT` | 7 | no API response within `VOICE_TIMEOUT`, ASR job unfinished within its wait (see Measured limits), or ffmpeg timed out |

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

## Audio generation (`gen`)

One prompt describes the whole take (≤3000 chars, ≤120s of output). The model reads it in order, so write it as a script:

- **Sounds**: what, how loud or far, how long, in sequence — `先是一声手机震动，环境中持续的鸟鸣声……然后是轻微的汽车刹车声，随后两声高跟鞋脚步声。`
- **Music**: lead instrument, other instruments, mood — `音乐以马林巴为主奏，加入合成器 lead、电贝斯、打击乐，整体紧张悬疑。` Songs work too; give the lyrics in quotes.
- **Characters**: introduce each once with gender, age, accent and timbre, then tag every line with who says it and how — `男子1（中青年男性，台湾口音，嗓音低沉）用严肃语气说道：“……” 男子2 平静无奈地说：“……”`
- **Timing**: start a line with `[开始s:结束s]`, one line per cue:

  ```text
  [0s:2.5s] 女声（年轻，紧张）小声说：“有人吗？”
  [3s:4s] 一声木门吱呀
  [4.2s:6s] 男声（低沉）回答：“别出声。”
  ```

References (`--ref`, `--speaker`, `--image`): up to 3 audio clips (mp3/wav ≤10MB sent as-is, anything else re-encoded to 192 kbps mp3; each ≤30s), referred to as `@音频1`…`@音频3` in upload order; a `--speaker` voice id from the Doubao TTS 2.0 voice list (https://www.volcengine.com/docs/6561/1257544) or a Doubao cloned voice; or one image (jpeg/png/webp ≤10MB), in which case the prompt may be just the text to speak — the image cannot be mixed with audio references or `--speaker`. 18 languages, including Chinese, English, Japanese, Korean, Spanish, French and German.

Billing follows `original_duration` (the model's raw output length).

## Measured limits

| Env | Default | Why |
|---|---|---|
| `VOICE_TTS_CHUNK_CHARS` | `150` | one 503-char request garbled a sentence mid-way (round-trip similarity 0.93); ~100–140-char chunks scored 0.996+ |
| `VOICE_TIMEOUT` | `600` | seconds per API request; one ASR job waits the larger of this and 0.3 × audio duration (≈3× the measured rate, so a 3.5h file gets ~63 min) |

ASR (measured): 5 min of speech ≈ 28s, 8 min ≈ 43s per pass; a 216s multi-speaker video took 36s for both passes. Audio is sent inline as 16 kHz mono 64 kbps mp3; above 100MB base64 (~3.5h) the provider wants `audio.url`, which the script does not use. Status `20000003` (no valid speech) maps to `NO_SPEECH_DETECTED`. The speaker pass uses `ssd_version: "200"` (it separated 5 speakers where 300 merged them into 3) and changes wording (100 → 一百), so only its labels are kept, plus utterances that pass 1 missed.

TTS: MiMo returns wav by default.

Gen (measured 2026-11-04): a 10s, 3-line timeline matched the total length exactly, line ends within 0.1s, line starts 0.2–0.4s late. A 43s, 17-line redub landed starts between 0.28s early and 0.38s late; moving every start 0.3s earlier did not reliably help, and the model added a “嘘” not in the script. A free-text "3秒钟" sound came back 0.54s long. A 6s, 3-line check with `--subtitle` came back exactly 6.0s, but put line 1 (tagged 0–2.5s, a whisper) at 1.72–2.68s and line 3 (tagged 4.2–6s) at 4.48–5.84s. `--ref` with `--speaker` in one request is accepted by the API; which voice wins has not been checked by ear. A 320×240 `--image` was rejected (`402 InvalidPayload:ImageSizeOutOfRange`); 512×512 and 1024×1024 worked. One request was dropped by the server without a response (retried as a network error); typical short requests return in 5–20s. To check male vs female per line, cut each line into its own clip and read `asr --output json` `gender` (on the whole clip ASR merged two lines under one label).

## Verification

- [ ] `python3 scripts/voice.py --check` → `ok: true`, `asr: ok`, `audio_gen: ok`, three TTS models listed
- [ ] `python3 scripts/voice.py tts "你好，这是一段测试。" --out t.wav` then `python3 scripts/voice.py asr t.wav -l zh` returns the same sentence
- [ ] A multi-person recording with `--speakers` shows `[S1]`/`[S2]` lines and the last utterance ends near the file duration
- [ ] Silent audio prints `NO_SPEECH_DETECTED`
- [ ] `--clone` and `--design` each produce a playable file; listen to confirm the timbre
- [ ] A missing file exits 3 with `INPUT_NOT_FOUND`
- [ ] `gen` with a 3-line `[开始s:结束s]` prompt and `--subtitle` produces a playable file whose `segments` start near the tagged times
- [ ] `gen` with a tag ending past 120s exits 4 before any request is sent
