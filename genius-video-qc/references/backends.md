# Backends, Prerequisites, Outputs

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

Python 3.9+, standard library only. On macOS the default OCR needs the Swift toolchain (`xcode-select --install`). The default ASR needs the sibling skill `genius-voice` with its key configured.

Tested: macOS 26 (Apple Silicon). Windows and Linux are unverified; there the OCR default is "none" (strip sheets).

## Choosing a backend

Order of precedence for each engine: command-line flag > environment variable > built-in default.

| Engine | Flag | Environment | Default |
|---|---|---|---|
| OCR | `--ocr-cmd` | `QC_OCR_CMD` | macOS: `swift scripts/ocr_vision.swift {dir} {lang}`; elsewhere: none |
| ASR | `--asr-cmd` | `QC_ASR_CMD` | `genius-voice/scripts/voice.py asr {input} --language {lang} --output json` (path override: `QC_VOICE_SCRIPT`) |

The value `none` disables an engine. Templates are split like a shell command line (no shell is run) and placeholders are substituted per argument: quote paths that contain spaces.

## OCR contract

Command: `<your command> ... {dir} ... {lang}`

- `{dir}`: a folder of PNG files named so that sorting gives time order.
- `{lang}`: the `--lang` value (`zh`, `en`, …). The built-in Vision backend maps it to Vision codes; a custom backend receives it as is.
- stdout: one JSON object per line, one line per image:

```json
{"file": "s_00001.png", "lines": [{"t": "过风的这个PVC它是用平面的结构", "c": 1.0, "cx": 0.50, "cy": 0.46, "h": 0.42}]}
```

`t` text as read, without correction; `c` confidence 0–1; `cx`, `cy` line centre and `h` line height, normalized 0–1 with `cy` measured from the top. Lines with `c` < 0.5, off-centre lines, and lines far from the median subtitle height are discarded when building cues, so report real confidences.

Example wrapper call (PaddleOCR, cloud OCR, anything else):

```bash
python3 scripts/qc.py run film.mp4 --ocr-cmd "python3 /path/to/paddle_ocr_dir.py {dir} {lang}"
```

```powershell
python scripts\qc.py run film.mp4 --ocr-cmd "python C:\tools\paddle_ocr_dir.py {dir} {lang}"
```

## ASR contract

Command: `<your command> ... {input} ... {lang}`

- `{input}`: a 16 kHz mono MP3 of the whole film.
- stdout: either `{"segments": [{"start": s, "end": s, "text": "..."}], "text": "..."}` or plain text.

Only the text is used for the subtitle comparison; segment times are kept in `report.json`.

## Outputs (`--out`, default `./<video-stem>-qc/`)

| File | Content |
|---|---|
| `report.md` | Measured findings for review |
| `report.json` | Everything, including low-level diffs, cue variants, flash runs |
| `subs.srt` | Subtitles as read by OCR (one cue per subtitle) |
| `transcript.txt`, `asr.json`, `audio.mp3` | ASR result (reused on re-run) and its input |
| `sheets/overview_*.png` | 4×4 thumbnails across the film |
| `sheets/subs_*.png` | Only without OCR: subtitle strips, one per second |

`zoom` writes one PNG (default `./zoom_<sec>.png`) and prints the time of every cell. `recheck` prints the transcript of a short range.

## Error codes

`Error [CODE]: message` on stderr. `INPUT_NOT_FOUND` 3, `DEPENDENCY_MISSING` 5, `BACKEND_FAILED` 6, `BAD_ARGUMENT` 2.
