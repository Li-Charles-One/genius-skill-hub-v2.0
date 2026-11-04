---
name: genius-voice
description: "Genius 语音：用豆包录音文件识别 2.0 做语音转文字（ASR），用小米 MiMo v2.5 做文字转语音（TTS），用豆包音频生成 Seed Audio 1.0 按描述生成音频。录音、播客、会议、采访、音视频素材转成文字，带分句与字级时间戳，多人时可标注说话人；文本朗读、配音、旁白；预设音色加情绪/方言/语气控制；用一段参考录音克隆声音；用文字描述设计新音色；生成音效、环境声、配乐、歌曲与多角色有声剧，可参考音频或图片，可按时间轴卡点配音（单次 ≤120 秒）。不要用于内容总结、声景分析或“这段音视频讲了什么”的理解（用 genius-omni）；不要用于音频剪辑、混音或格式转换；给一段视频做台词、配音、拟音、音效、配乐与混录母带用 genius-sound。"
metadata:
  version: "2.1.3"
---

# Genius Voice（语音）

This skill exists to **turn speech into text** (Doubao ASR), **text into speech** (Xiaomi MiMo v2.5) and **descriptions into audio** (Doubao Seed Audio). Nothing else.

Models: ASR `volc.seedasr.auc` (豆包录音文件识别 2.0); TTS `mimo-v2.5-tts`, `mimo-v2.5-tts-voiceclone`, `mimo-v2.5-tts-voicedesign`; generation `seed-audio-1.0` (豆包音频生成 1.0). Config, voices, style tags, prompt writing and measured limits: `references/usage.md`. Trigger checks: `evals/evals.json`.

## Pick a mode

| User wants | Command |
|---|---|
| Recording / podcast / footage → text (with timestamps in JSON) | `asr <file>` |
| Who said what (interview, meeting, multi-person footage) | `asr <file> --speakers` |
| Read text aloud with a stock voice | `tts "<text>" --voice <id>` |
| Speak in the voice of a sample recording | `tts "<text>" --clone <ref audio>` |
| Invent a voice from a description | `tts "<text>" --design "<description>"` |
| Sound effects, ambience, music, a song, or a multi-role scene with acting directions | `gen "<prompt>"` |
| Lines that must land at given times (redub, timed narration) | `gen` with `[start s:end s]` line prefixes |
| Generate guided by sample audio (a voice, a style, a sound) or by an image | `gen "<prompt with @音频1>" --ref A` / `gen "<text>" --image IMG` |

Plain reading of a given text (any length; stock, cloned or designed voice) is `tts`. Anything that needs sounds, music, several characters in one take, or fixed timing is `gen`. Summaries, soundscape or "what happens in this audio/video" belong to genius-omni, not here.

## Run

```bash
python3 "<skill_dir>/scripts/voice.py" --check
python3 "<skill_dir>/scripts/voice.py" asr <audio_or_video> [--language auto|zh|en] [--speakers] [--output text|json] [--out FILE]
python3 "<skill_dir>/scripts/voice.py" tts "<text>" | --text-file F | -  [--voice ID | --clone REF | --design "..."] [--style "..."] [--out FILE]
python3 "<skill_dir>/scripts/voice.py" gen "<prompt>" | --text-file F | -  [--ref AUDIO]... [--speaker ID] [--image IMG] [--subtitle] [--out FILE]
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe`; no Python packages. Keys (`DOUBAO_API_KEY` for ASR and `gen`, `MIMO_API_KEY` for TTS) live in `scripts/.env`, never in the package.

- ASR accepts anything ffmpeg decodes (video too: the audio track is used). Do not transcode or split it yourself; the script sends the whole file as one job (up to ~3.5h).
- `--speakers` runs a second recognition pass for speaker labels and maps them onto the first pass by time overlap. Use it for multi-person audio; skip it for single-speaker narration (it doubles the time).
- `--language zh` / `en` fixes the language; leave `auto` for mixed or unknown speech.
- TTS splits text into ≤150-char sentence chunks and joins the audio. A leading style tag such as `(温柔)` or `（粤语）` applies to every chunk; inline tags such as `（深呼吸）` stay where they are. `--style` is a natural-language direction (with `--design` it is appended to the description).
- `--clone` sends the whole reference file, so pass a prepared clip: one speaker, no music or overlapping voices, about 5–15s, cut at pauses (`ffmpeg -ss START -to END -i IN -vn -ac 1 ref.wav`). To clone one person from a multi-speaker recording or video, first find their stretches with `asr --speakers --output json` (utterance times + speaker labels), then cut and clone.
- `gen` makes one scene per call: at most 120s of audio from a prompt of at most 3000 chars. For anything longer, split the scene and run several calls; the script refuses a timeline that runs past 120s and warns when the output hits the cap.
- Write the `gen` prompt as a scene: the sounds and music (instruments, mood) in order, and each character (gender, age, accent, timbre) with how they say each quoted line. To pin timing, start a line with `[开始s:结束s]`, e.g. `[2.0s:4.5s] 男声压低声音说：“跑！”`. Examples in `references/usage.md`.
- `gen --ref` (up to 3 clips, each ≤30s) maps in order to `@音频1`…`@音频3` in the prompt. `--speaker` takes a Doubao TTS 2.0 voice id (e.g. `zh_female_cancan_uranus_bigtts`) or a Doubao cloned-voice id, not the MiMo preset names. `--image` (jpeg/png/webp) cannot be combined with `--ref` or `--speaker`.
- Output defaults to `genius-voice-<time>.wav` in the current directory; any other extension (`.mp3`, `.m4a`…) is converted by ffmpeg (64 kbps for `tts`, 192 kbps for `gen`, which is 48 kHz stereo). `tts` and `gen` print `{"out": ..., "seconds": ...}`; `gen --subtitle` adds `segments` with sentence and word times in the same shape as `asr --output json`.
- Run one job at a time.

## Report

- ASR: the transcript as returned, in the source language, unedited (`[S1]`, `[S2]` prefixes with `--speakers`). With `--output json`, also report segment count, speaker count and duration. Pass `NO_SPEECH_DETECTED` through unchanged; never fill in or "fix" words.
- TTS: the output path, duration, and voice used (preset id, clone reference, or design description).
- Gen: the output path, duration, and the references used (`--ref` files, `--speaker` id, `--image`). Pass on the 120s-cap warning if it was printed.

Failures print `Error [CODE]: …` with a non-zero exit. Report the code and message as-is; the code table is in `references/usage.md`.

## Gotchas

- Without `--speakers`, a second speaker who cuts in with no pause can be dropped entirely (measured: two voices back to back lost the second; a 0.6s gap or the speaker pass kept it). With `--speakers` the script fills such gaps from the speaker pass, so use it whenever more than one person talks.
- Homophones survive (采销 → 彩销, JOVO → Jovi). Report the transcript as returned; do not correct it.
- Silent audio returns `NO_SPEECH_DETECTED`.
- TTS on one long request (≈250+ chars) skips, repeats or garbles sentences. Keep `VOICE_TTS_CHUNK_CHARS` at 150 or below.
- A designed voice has no reusable id. The script designs chunk 1 and clones it for later chunks; to reuse a designed voice later, pass its output file to `--clone`.
- Preset voices, cloning and design are separate models; they cannot be combined in one call. Singing `(唱歌)` works only with preset voices; for a song with accompaniment use `gen`.
- In `gen`, a length written in plain words is only a hint (measured: "3秒钟" gave 0.54s). Use `[开始s:结束s]` tags when length or timing matters.
- `gen` timing is close, not exact (measured: total length exact, line ends within 0.1s, line starts usually 0.2–0.4s late but once 1.7s late on a whispered opening line; shifting starts earlier did not reliably help). It can also add words that are not in the script (measured: an extra “嘘”). When the script or timing must be exact, check the result with `asr` or `--subtitle`.
- Redubbing a video: one `gen` per line, placed locally, beat one timeline take (2026-11-04, 43s clip: per-line takes put every lip-synced line within 0.1s). Keep a character's voice across takes by passing the first take as `--ref` and starting the prompt `In the exact voice of @音频1, …`. genius-sound runs this loop.
- Whispers dropped words ("Easy…", "Grip") until the prompt said "clear, audible stage whisper" and the `[开始s:结束s]` window was about 1.5× the spoken length.
- `gen` output is quiet: speech peaked around −32 dBFS. Normalise before mixing.
- A sound-effect timeline can return a loud sound the prompt never asked for (measured: 37.4–40s of a 16s segment). Check the level over time before using it as a bed.
