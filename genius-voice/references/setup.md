# Genius Voice setup, shared output and errors

Shared by all three modules. Module details: `references/asr.md`, `references/tts.md`, `references/gen.md`.

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

On Windows, write `python scripts\voice.py …`; pass long text with `--text-file` rather than shell quoting.

## Output and errors

- Progress goes to stderr as `[genius-voice] …`.

| Code | Exit | Typical cause |
|---|---|---|
| `INPUT_NOT_FOUND` | 3 | audio, reference or text file does not exist |
| `UNSUPPORTED_FORMAT` | 4 | ffmpeg cannot decode the input; empty text; clone reference under 1s, or still over 10MB base64 after re-encoding; `gen` prompt over 3000 chars, timeline past 120s, more than 3 `--ref`, a `--ref` over 30s, `--image` not jpeg/png/webp ≤10MB or combined with `--ref`/`--speaker` |
| `DEPENDENCY_MISSING` | 5 | `ffmpeg` / `ffprobe` not on PATH |
| `PROVIDER_ERROR` | 6 | missing key, HTTP error, ASR status code other than success/processing/silence, content filter, empty audio |
| `TIMEOUT` | 7 | no API response within `VOICE_TIMEOUT`, ASR job unfinished within its wait (`references/asr.md`), or ffmpeg timed out |

Other errors exit 1; `--check` failing exits 2. HTTP 429/5xx and network errors retry after 5s / 15s / 30s.

| Env | Default | Why |
|---|---|---|
| `VOICE_TIMEOUT` | `600` | seconds per API request (ASR jobs may wait longer, `references/asr.md`) |

## Verification

- [ ] `python3 scripts/voice.py --check` → `ok: true`, `asr: ok`, `audio_gen: ok`, three TTS models listed
- [ ] Then each module's own checklist
