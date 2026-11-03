---
name: genius-voice
description: "Genius 语音：用豆包录音文件识别 2.0 做语音转文字（ASR），用小米 MiMo v2.5 做文字转语音（TTS）。录音、播客、会议、采访、音视频素材转成文字，带分句与字级时间戳，多人时可标注说话人；文本朗读、配音、旁白；预设音色加情绪/方言/语气控制；用一段参考录音克隆声音；用文字描述设计新音色。不要用于内容总结、声景分析或“这段音视频讲了什么”的理解（用 genius-omni）；不要用于音乐创作、音频剪辑或格式转换。"
metadata:
  version: "2.0.0"
---

# Genius Voice（语音）

This skill exists to **turn speech into text** (Doubao) and **text into speech** (Xiaomi MiMo v2.5). Nothing else.

Models: ASR `volc.seedasr.auc` (豆包录音文件识别 2.0); TTS `mimo-v2.5-tts`, `mimo-v2.5-tts-voiceclone`, `mimo-v2.5-tts-voicedesign`. Config, voices, style tags and measured limits: `references/usage.md`. Trigger checks: `evals/evals.json`.

## Pick a mode

| User wants | Command |
|---|---|
| Recording / podcast / footage → text (with timestamps in JSON) | `asr <file>` |
| Who said what (interview, meeting, multi-person footage) | `asr <file> --speakers` |
| Read text aloud with a stock voice | `tts "<text>" --voice <id>` |
| Speak in the voice of a sample recording | `tts "<text>" --clone <ref audio>` |
| Invent a voice from a description | `tts "<text>" --design "<description>"` |

Summaries, soundscape or "what happens in this audio/video" belong to genius-omni, not here.

## Run

```bash
python3 "<skill_dir>/scripts/voice.py" --check
python3 "<skill_dir>/scripts/voice.py" asr <audio_or_video> [--language auto|zh|en] [--speakers] [--output text|json] [--out FILE]
python3 "<skill_dir>/scripts/voice.py" tts "<text>" | --text-file F | -  [--voice ID | --clone REF | --design "..."] [--style "..."] [--out FILE]
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe`; no Python packages. Keys (`DOUBAO_API_KEY` for ASR, `MIMO_API_KEY` for TTS) live in `scripts/.env`, never in the package.

- ASR accepts anything ffmpeg decodes (video too: the audio track is used). Do not transcode or split it yourself; the script sends the whole file as one job (up to ~3.5h).
- `--speakers` runs a second recognition pass for speaker labels and maps them onto the first pass by time overlap. Use it for multi-person audio; skip it for single-speaker narration (it doubles the time).
- `--language zh` / `en` fixes the language; leave `auto` for mixed or unknown speech.
- TTS splits text into ≤150-char sentence chunks and joins the audio. A leading style tag such as `(温柔)` or `（粤语）` applies to every chunk; inline tags such as `（深呼吸）` stay where they are. `--style` is a natural-language direction (with `--design` it is appended to the description).
- `--clone` sends the whole reference file, so pass a prepared clip: one speaker, no music or overlapping voices, about 5–15s, cut at pauses (`ffmpeg -ss START -to END -i IN -vn -ac 1 ref.wav`). To clone one person from a multi-speaker recording or video, first find their stretches with `asr --speakers --output json` (utterance times + speaker labels), then cut and clone.
- Output defaults to `genius-voice-<time>.wav` in the current directory; any other extension (`.mp3`, `.m4a`…) is converted by ffmpeg. TTS prints `{"out": ..., "seconds": ...}`.
- Run one job at a time.

## Report

- ASR: the transcript as returned, in the source language, unedited (`[S1]`, `[S2]` prefixes with `--speakers`). With `--output json`, also report segment count, speaker count and duration. Pass `NO_SPEECH_DETECTED` through unchanged; never fill in or "fix" words.
- TTS: the output path, duration, and voice used (preset id, clone reference, or design description).

Failures print `Error [CODE]: …` with a non-zero exit. Report the code and message as-is; the code table is in `references/usage.md`.

## Gotchas

- Without `--speakers`, a second speaker who cuts in with no pause can be dropped entirely (measured: two voices back to back lost the second; a 0.6s gap or the speaker pass kept it). With `--speakers` the script fills such gaps from the speaker pass, so use it whenever more than one person talks.
- Homophones survive (采销 → 彩销, JOVO → Jovi). Report the transcript as returned; do not correct it.
- Silent audio returns `NO_SPEECH_DETECTED`.
- TTS on one long request (≈250+ chars) skips, repeats or garbles sentences. Keep `VOICE_TTS_CHUNK_CHARS` at 150 or below.
- A designed voice has no reusable id. The script designs chunk 1 and clones it for later chunks; to reuse a designed voice later, pass its output file to `--clone`.
- Preset voices, cloning and design are separate models; they cannot be combined in one call. Singing `(唱歌)` works only with preset voices.
