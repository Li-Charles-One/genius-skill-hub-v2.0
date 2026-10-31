---
name: genius-voice
description: "Genius 语音：用小米 MiMo v2.5 做语音转文字（ASR）和文字转语音（TTS）。录音、播客、会议、语音备忘录转成文字；文本朗读、配音、旁白；预设音色加情绪/方言/语气控制；用一段参考录音克隆声音；用文字描述设计新音色。不要用于需要时间轴、说话人标注、内容总结或声景分析的音视频理解（用 genius-omni）；不要用于音乐创作、音频剪辑或格式转换。"
metadata:
  version: "1.0.0"
---

# Genius Voice（语音）

This skill exists to **turn speech into text** and **text into speech** with Xiaomi MiMo v2.5. Nothing else.

Models: `mimo-v2.5-asr`, `mimo-v2.5-tts`, `mimo-v2.5-tts-voiceclone`, `mimo-v2.5-tts-voicedesign`. Config, voices, style tags and measured limits: `references/usage.md`. Trigger checks: `evals/evals.json`.

## Pick a mode

| User wants | Command |
|---|---|
| Recording / podcast / meeting → text | `asr <file>` |
| Read text aloud with a stock voice | `tts "<text>" --voice <id>` |
| Speak in the voice of a sample recording | `tts "<text>" --clone <ref audio>` |
| Invent a voice from a description | `tts "<text>" --design "<description>"` |

Timestamps, speaker labels, summaries or "what happens in this audio/video" belong to genius-omni, not here.

## Run

```bash
python3 "<skill_dir>/scripts/voice.py" --check
python3 "<skill_dir>/scripts/voice.py" asr <audio_or_video> [--language auto|zh|en] [--output text|json] [--out FILE]
python3 "<skill_dir>/scripts/voice.py" tts "<text>" | --text-file F | -  [--voice ID | --clone REF | --design "..."] [--style "..."] [--out FILE]
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe`; no Python packages. Key and base URL live in `scripts/.env`, never in the package.

- ASR accepts anything ffmpeg decodes (video too: the audio track is used). Do not transcode or split it yourself; the script cuts at silences into ≤120s segments and re-splits a segment that hits the output limit.
- Set `--language zh` or `en` when known; it is more accurate than `auto`.
- TTS splits text into ≤150-char sentence chunks and joins the audio. A leading style tag such as `(温柔)` or `（粤语）` applies to every chunk; inline tags such as `（深呼吸）` stay where they are. `--style` is a natural-language direction (with `--design` it is appended to the description).
- `--clone` sends the whole reference file, so pass a prepared clip: one speaker, no music or overlapping voices, about 5–15s, cut at pauses (`ffmpeg -ss START -to END -i IN -vn -ac 1 ref.wav`). To clone one person from a multi-speaker recording or video, first find their stretches with genius-omni `audio-transcribe` (timestamps + speaker labels), then cut and clone.
- Output defaults to `genius-voice-<time>.wav` in the current directory; any other extension (`.mp3`, `.m4a`…) is converted by ffmpeg. TTS prints `{"out": ..., "seconds": ...}`.
- Run one job at a time.

## Report

- ASR: the transcript as returned, in the source language, unedited. With `--output json`, also report segment count and duration. Pass `NO_SPEECH_DETECTED` through unchanged; never fill in or "fix" words.
- TTS: the output path, duration, and voice used (preset id, clone reference, or design description).

Failures print `Error [CODE]: …` with a non-zero exit. Report the code and message as-is; the code table is in `references/usage.md`.

## Gotchas

- ASR drops whole passages, still answering `finish=stop`, when a segment is long (measured: 180–300s lost content, 120s did not). Do not raise `VOICE_ASR_SEGMENT_SEC` above 120.
- ASR on pure digital silence may return a filler such as `嗯。`; pure tones and noise return `NO_SPEECH_DETECTED`.
- TTS on one long request (≈250+ chars) skips, repeats or garbles sentences. Keep `VOICE_TTS_CHUNK_CHARS` at 150 or below.
- A designed voice has no reusable id. The script designs chunk 1 and clones it for later chunks; to reuse a designed voice later, pass its output file to `--clone`.
- Preset voices, cloning and design are separate models; they cannot be combined in one call. Singing `(唱歌)` works only with preset voices.
