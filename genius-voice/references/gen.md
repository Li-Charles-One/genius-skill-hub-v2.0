# Gen module: audio from a description (`gen`)

Model `seed-audio-1.0` (豆包音频生成 1.0). Key: `DOUBAO_API_KEY` (`references/setup.md`).

```bash
python3 "<skill_dir>/scripts/voice.py" gen "<prompt>" | --text-file F | -  [--ref AUDIO]... [--speaker ID] [--image IMG] [--subtitle] [--out FILE]
```

```bash
python3 scripts/voice.py gen "[0s:15s] 雨夜的老街，持续的中雨打在铁皮屋檐上，远处偶尔一声闷雷。" --out rain.wav
python3 scripts/voice.py gen "一首 30 秒的中文儿歌，木琴和尤克里里伴奏，童声欢快地唱：“小星星，眨眼睛……”" --out song.mp3
python3 scripts/voice.py gen --text-file timed-lines.txt --subtitle --out redub.wav
python3 scripts/voice.py gen "用@音频1的声音，惊讶地说：“你怎么来了？”" --ref voice.wav --out line.wav
python3 scripts/voice.py gen "开心地说：“今天天气真好。”" --speaker zh_female_cancan_uranus_bigtts --out sunny.wav
```

## Running it

- `gen` makes one scene per call: at most 120s of audio from a prompt of at most 3000 chars. For anything longer, split the scene and run several calls; the script refuses a timeline that runs past 120s and warns when the output hits the cap.
- `gen --ref` (up to 3 clips, each ≤30s) maps in order to `@音频1`…`@音频3` in the prompt. `--speaker` takes a Doubao TTS 2.0 voice id (e.g. `zh_female_cancan_uranus_bigtts`) or a Doubao cloned-voice id, not the MiMo preset names. `--image` (jpeg/png/webp) cannot be combined with `--ref` or `--speaker`.

## Writing the prompt

One prompt describes the whole take. The model reads it in order, so write it as a script:

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

## Output

Gen writes 48 kHz stereo 16-bit audio (non-wav outputs at 192 kbps) and prints `{"out", "seconds"}`; with `--subtitle` also `segments: [{start, end, text, words: [{start, end, text}]}]`, times in seconds (the same shape as `asr --output json`).

## Report

The output path, duration, and the references used (`--ref` files, `--speaker` id, `--image`). Pass on the 120s-cap warning if it was printed.

## Measured (2026-11-04)

A 10s, 3-line timeline matched the total length exactly, line ends within 0.1s, line starts 0.2–0.4s late. A 43s, 17-line redub landed starts between 0.28s early and 0.38s late; moving every start 0.3s earlier did not reliably help, and the model added a “嘘” not in the script. A free-text "3秒钟" sound came back 0.54s long. A 6s, 3-line check with `--subtitle` came back exactly 6.0s, but put line 1 (tagged 0–2.5s, a whisper) at 1.72–2.68s and line 3 (tagged 4.2–6s) at 4.48–5.84s. `--ref` with `--speaker` in one request is accepted by the API; which voice wins has not been checked by ear. A 320×240 `--image` was rejected (`402 InvalidPayload:ImageSizeOutOfRange`); 512×512 and 1024×1024 worked. One request was dropped by the server without a response (retried as a network error); typical short requests return in 5–20s. To check male vs female per line, cut each line into its own clip and read `asr --output json` `gender` (on the whole clip ASR merged two lines under one label).

## Gotchas

- A length written in plain words is only a hint (measured: "3秒钟" gave 0.54s). Use `[开始s:结束s]` tags when length or timing matters.
- Timing is close, not exact (measured: total length exact, line ends within 0.1s, line starts usually 0.2–0.4s late but once 1.7s late on a whispered opening line; shifting starts earlier did not reliably help). It can also add words that are not in the script (measured: an extra “嘘”). When the script or timing must be exact, check the result with `asr` or `--subtitle`.
- Keep a character's voice across takes by passing the first take as `--ref` and starting the prompt `In the exact voice of @音频1, …`. Redubbing a video to the lips (one `gen` per line, placed locally) is genius-sound's job.
- Whispers dropped words ("Easy…", "Grip") until the prompt said "clear, audible stage whisper" and the `[开始s:结束s]` window was about 1.5× the spoken length.
- Output is quiet: speech peaked around −32 dBFS. Normalise before mixing.
- A sound-effect timeline can return a loud sound the prompt never asked for (measured: 37.4–40s of a 16s segment). Check the level over time before using it as a bed.

## Verification

- [ ] `gen` with a 3-line `[开始s:结束s]` prompt and `--subtitle` produces a playable file whose `segments` start near the tagged times
- [ ] `gen` with a tag ending past 120s exits 4 before any request is sent
