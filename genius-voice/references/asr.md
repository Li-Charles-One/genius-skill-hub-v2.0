# ASR module: speech to text (`asr`)

Model `volc.seedasr.auc` (豆包录音文件识别 2.0). Key: `DOUBAO_API_KEY` (`references/setup.md`).

```bash
python3 "<skill_dir>/scripts/voice.py" asr <audio_or_video> [--language auto|zh|en] [--speakers] [--output text|json] [--out FILE]
```

```bash
python3 scripts/voice.py asr meeting.m4a --language zh
python3 scripts/voice.py asr interview.mp4 --speakers --output json --out interview.json
```

## Running it

- ASR accepts anything ffmpeg decodes (video too: the audio track is used). Do not transcode or split it yourself; the script sends the whole file as one job (up to ~3.5h).
- `--speakers` runs a second recognition pass for speaker labels and maps them onto the first pass by time overlap. Use it for multi-person audio; skip it for single-speaker narration (it doubles the time).
- `--language zh` / `en` fixes the language; leave `auto` for mixed or unknown speech.

## Output

- Text mode prints one utterance per line, prefixed `[S1]`, `[S2]`… with `--speakers`.
- `--output json` prints `{file, model, language, duration, segments, text}`; each segment is one utterance: `{start, end, text, speaker?, emotion?, gender?, speech_rate?, words: [{start, end, text}]}`, times in seconds. `speech_rate` is characters per second; emotion and gender are unreliable where voices overlap.

## Report

The transcript as returned, in the source language, unedited (`[S1]`, `[S2]` prefixes with `--speakers`). With `--output json`, also report segment count, speaker count and duration. Pass `NO_SPEECH_DETECTED` through unchanged; never fill in or "fix" words.

## Measured

- 5 min of speech ≈ 28s, 8 min ≈ 43s per pass; a 216s multi-speaker video took 36s for both passes.
- One ASR job waits the larger of `VOICE_TIMEOUT` and 0.3 × audio duration (≈3× the measured rate, so a 3.5h file gets ~63 min).
- Audio is sent inline as 16 kHz mono 64 kbps mp3; above 100MB base64 (~3.5h) the provider wants `audio.url`, which the script does not use.
- Status `20000003` (no valid speech) maps to `NO_SPEECH_DETECTED`.
- The speaker pass uses `ssd_version: "200"` (it separated 5 speakers where 300 merged them into 3) and changes wording (100 → 一百), so only its labels are kept, plus utterances that pass 1 missed.

## Gotchas

- Without `--speakers`, a second speaker who cuts in with no pause can be dropped entirely (measured: two voices back to back lost the second; a 0.6s gap or the speaker pass kept it). With `--speakers` the script fills such gaps from the speaker pass, so use it whenever more than one person talks.
- Homophones survive (采销 → 彩销, JOVO → Jovi). Report the transcript as returned; do not correct it.
- Silent audio returns `NO_SPEECH_DETECTED`.
- Under music, short words at a line start can vanish: a video's opening "嗨，我是 Leo" came back as "我是 Leo"; the same audio after vocal separation, or its first 4s on their own, gave "嗨"/"Hi". When the transcript becomes a script to re-voice, recheck the first seconds alone and ask the user about greetings. English names in Chinese speech also drift ("放 Gentle" → "放晴").

## Verification

- [ ] A multi-person recording with `--speakers` shows `[S1]`/`[S2]` lines and the last utterance ends near the file duration
- [ ] Silent audio prints `NO_SPEECH_DETECTED`
- [ ] A missing file exits 3 with `INPUT_NOT_FOUND`
