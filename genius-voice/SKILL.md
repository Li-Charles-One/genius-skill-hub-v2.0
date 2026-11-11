---
name: genius-voice
description: "Genius 语音：用豆包录音文件识别 2.0 做语音转文字（ASR），用小米 MiMo v2.5 做文字转语音（TTS），用豆包音频生成 Seed Audio 1.0 按描述生成音频。录音、播客、会议、采访、音视频素材转成文字，带分句与字级时间戳，多人时可标注说话人；文本朗读、配音、旁白；预设音色加情绪/方言/语气控制；用一段参考录音克隆声音；用文字描述设计新音色；生成音效、环境声、配乐、歌曲与多角色有声剧，可参考音频或图片，可按时间轴卡点配音（单次 ≤120 秒）；视频旁白混着背景音乐、想要干净旁白干声时，转写后克隆原声按原时间轴重配（不装人声分离模型）。不要用于内容总结、声景分析或“这段音视频讲了什么”的理解（用 genius-omni）；不要用于音频剪辑、混音或格式转换；给一段视频做台词、配音、拟音、音效、配乐与混录母带用 genius-sound。"
metadata:
  version: "2.2.3"
---

# Genius Voice（语音）

This skill exists to **turn speech into text** (Doubao ASR), **text into speech** (Xiaomi MiMo v2.5) and **descriptions into audio** (Doubao Seed Audio). Nothing else.

Three independent modules. Before running one, read its file; read only the modules the task uses. Setup, keys, error codes and the `--check` probe: `references/setup.md`. Trigger checks: `evals/evals.json`.

## Pick a module

| User wants | Module | Command | Read |
|---|---|---|---|
| Recording / podcast / footage → text (with timestamps in JSON) | asr 转写 | `asr <file>` | `references/asr.md` |
| Who said what (interview, meeting, multi-person footage) | asr 转写 | `asr <file> --speakers` | `references/asr.md` |
| Read text aloud with a stock voice | tts 朗读 | `tts "<text>" --voice <id>` | `references/tts.md` |
| Speak in the voice of a sample recording | tts 朗读 | `tts "<text>" --clone <ref audio>` | `references/tts.md` |
| Invent a voice from a description | tts 朗读 | `tts "<text>" --design "<description>"` | `references/tts.md` |
| Sound effects, ambience, music, a song, or a multi-role scene with acting directions | gen 生成 | `gen "<prompt>"` | `references/gen.md` |
| Lines that must land at given times (redub, timed narration) | gen 生成 | `gen` with `[start s:end s]` line prefixes | `references/gen.md` |
| Generate guided by sample audio (a voice, a style, a sound) or by an image | gen 生成 | `gen "<prompt with @音频1>" --ref A` / `gen "<text>" --image IMG` | `references/gen.md` |
| Clean narration (旁白干声) from a video whose voice is mixed with music | asr → tts → gen | re-voice recipe | `references/gen.md` § Re-voicing narration |

Plain reading of a given text (any length; stock, cloned or designed voice) is `tts`. Anything that needs sounds, music, several characters in one take, or fixed timing is `gen`; one `gen` call makes at most 120s, so split longer scenes into several calls. Summaries, soundscape or "what happens in this audio/video" belong to genius-omni; a whole clip's soundtrack (lip-synced dialogue, foley, mix) belongs to genius-sound.

Never install vocal-separation models or other heavy packages (Demucs, UVR, audio-separator, torch) to get a dry voice: re-voice it with this skill instead. If the user still wants separation, say what would be downloaded and its size, and wait for a yes.

## Run

```bash
python3 "<skill_dir>/scripts/voice.py" --check
python3 "<skill_dir>/scripts/voice.py" asr <audio_or_video> [--language auto|zh|en] [--speakers] [--output text|json] [--out FILE]
python3 "<skill_dir>/scripts/voice.py" tts "<text>" | --text-file F | -  [--voice ID | --clone REF | --design "..."] [--style "..."] [--out FILE]
python3 "<skill_dir>/scripts/voice.py" gen "<prompt>" | --text-file F | -  [--ref AUDIO]... [--speaker ID] [--image IMG] [--subtitle] [--out FILE]
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe`; no Python packages. Keys (`DOUBAO_API_KEY` for ASR and `gen`, `MIMO_API_KEY` for TTS) live in `scripts/.env`, never in the package.

- Output defaults to `genius-voice-<time>.wav` in the current directory; any other extension (`.mp3`, `.m4a`…) is converted by ffmpeg. `tts` and `gen` print `{"out": ..., "seconds": ...}`.
- Run one job at a time.

## Report

Each module's file says what to report. Never edit or "fix" a transcript.

Failures print `Error [CODE]: …` with a non-zero exit (a missing input is `INPUT_NOT_FOUND`, exit 3). Report the code and message as-is; the code table is in `references/setup.md`.

## Gotchas

Each module's file has its own Gotchas section: `references/asr.md`, `references/tts.md`, `references/gen.md`.

## Resource Map

- `scripts/voice.py`: every command above.
- `references/setup.md`: prerequisites, keys and endpoints, error codes, retries, `--check`.
- `references/asr.md`: transcription, speaker labels, JSON shape, measured speed, gotchas.
- `references/tts.md`: preset voices, style tags, clone and design, chunking, gotchas.
- `references/gen.md`: prompt writing, timing tags, references, measured timing, gotchas.
- `evals/evals.json`: trigger and behaviour checks.
- `agents/openai.yaml`: Codex/UI metadata.
