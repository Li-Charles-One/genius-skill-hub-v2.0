"""
Speech for genius-footage: Doubao file ASR 2.0 (volc.seedasr.auc) with word timestamps and speaker labels.
Copied from genius-voice 2.1.0 voice.py so footage runs on its own. Config from the environment or scripts/.env:

    DOUBAO_API_KEY   required (without it the transcript is skipped); falls back to genius-voice's scripts/.env
"""

from __future__ import annotations

import base64
import http.client
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from client import RETRY_DELAYS, RETRY_HTTP, _dotenv, _env

ASR_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/"
ASR_MODEL = "volc.seedasr.auc"
# Speaker diarization changes the text (fewer, merged utterances; 100 → 一百), so it runs as a second pass.
ASR_PASS_TEXT = {"enable_itn": True, "enable_punc": True, "show_speech_rate": True,
                 "enable_emotion_detection": True, "enable_gender_detection": True}
ASR_PASS_SPEAKER = {"enable_itn": True, "enable_punc": True, "enable_speaker_info": True,
                    "ssd_version": "200"}  # 200 separated 5 speakers where 300 merged them into 3
ASR_MAX_B64_BYTES = 100 * 1000 * 1000  # above this the provider wants audio.url instead of inline data
ASR_POLL_SEC = 2
ASR_WAIT_PER_AUDIO_SEC = 0.3  # measured ≈0.09s per audio second; 3× margin for queueing
REQUEST_TIMEOUT = 600


class SpeechError(RuntimeError):
    pass


def log(msg: str) -> None:
    print(f"[genius-footage] {msg}", file=sys.stderr, flush=True)


def find_key() -> str:
    """The environment or this skill's scripts/.env, else the genius-voice skill's scripts/.env
    (next to this skill, or GENIUS_VOICE_DIR), so one Doubao key serves both skills."""
    key = _env("DOUBAO_API_KEY")
    for d in (os.environ.get("GENIUS_VOICE_DIR"), Path(__file__).parents[2] / "genius-voice",
              Path(__file__).resolve().parents[2] / "genius-voice"):
        if key:
            break
        if d:
            key = _dotenv(Path(d) / "scripts" / ".env").get("DOUBAO_API_KEY", "").strip()
    return key


def doubao_key() -> str:
    key = find_key()
    if not key:
        raise SpeechError("DOUBAO_API_KEY is not set (environment, scripts/.env or genius-voice's scripts/.env); "
                          "transcript skipped")
    return key


def _doubao(path: str, body: dict, request_id: str) -> tuple[str, str, dict]:
    """Doubao ASR call with retries on 429/5xx/network errors. Returns (X-Api-Status-Code, X-Api-Message, body)."""
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Api-Key": doubao_key(), "X-Api-Resource-Id": ASR_MODEL,
               "X-Api-Request-Id": request_id, "X-Api-Sequence": "-1"}
    for attempt, delay in enumerate((*RETRY_DELAYS, None), 1):
        req = urllib.request.Request(ASR_URL + path, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")
                return (resp.headers.get("X-Api-Status-Code", ""), resp.headers.get("X-Api-Message", ""),
                        json.loads(raw) if raw.strip() else {})
        except urllib.error.HTTPError as e:
            error = SpeechError(f"ASR API error {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}")
            transient = e.code in RETRY_HTTP
        except (socket.timeout, TimeoutError) as e:
            raise SpeechError(f"ASR: no response within {REQUEST_TIMEOUT}s") from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise SpeechError(f"ASR: no response within {REQUEST_TIMEOUT}s") from e
            error = SpeechError(f"ASR network error: {e.reason}")
            transient = True
        except (http.client.HTTPException, ConnectionError) as e:  # getresponse() bypasses URLError
            error = SpeechError(f"ASR network error: {e}")
            transient = True
        if delay is None or not transient:
            raise error
        log(f"{error} — retry {attempt}/{len(RETRY_DELAYS)} in {delay}s…")
        time.sleep(delay)
    raise AssertionError("unreachable")


def _run(cmd: list, timeout: float) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout)
    except FileNotFoundError as e:
        raise SpeechError(f"{cmd[0]} not found on PATH (install ffmpeg)") from e
    except subprocess.TimeoutExpired as e:
        raise SpeechError(f"{cmd[0]} exceeded {timeout:g}s") from e


def probe_duration(path: str) -> float:
    proc = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path], 60)
    try:
        return float(json.loads(proc.stdout or b"{}")["format"]["duration"])
    except (KeyError, TypeError, ValueError):
        raise SpeechError(f"ffprobe cannot read an audio duration from {path}")


def encode_mp3(path: str, duration: float) -> bytes:
    proc = _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", "0", "-t", f"{duration:.3f}",
                 "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "64k",
                 "-f", "mp3", "pipe:1"], 900)
    if proc.returncode != 0 or not proc.stdout:
        raise SpeechError(f"ffmpeg could not decode audio: {proc.stderr.decode(errors='replace')[:300]}")
    return proc.stdout


def _asr_pass(b64: str, options: dict, duration: float) -> list[dict]:
    """Submit one recognition job and poll until done. Returns raw utterances ([] for silence)."""
    request_id = str(uuid.uuid4())  # doubles as the task id for polling
    code, msg, _ = _doubao("submit", {"audio": {"data": b64, "format": "mp3"}, "request": {
        "model_name": "bigmodel", "show_utterances": True, **options}}, request_id)
    if code != "20000000":
        raise SpeechError(f"ASR submit failed [{code}]: {msg}")
    wait = max(REQUEST_TIMEOUT, duration * ASR_WAIT_PER_AUDIO_SEC)
    deadline = time.monotonic() + wait
    while True:
        time.sleep(ASR_POLL_SEC)
        code, msg, data = _doubao("query", {}, request_id)
        if code == "20000000":
            return (data.get("result") or {}).get("utterances") or []
        if code == "20000003":  # no valid speech in audio
            return []
        if code not in ("20000001", "20000002"):  # queued / processing
            raise SpeechError(f"ASR failed [{code}]: {msg}")
        if time.monotonic() > deadline:
            raise SpeechError(f"ASR job not finished within {wait:.0f}s")


def _utterance(u: dict) -> dict:
    extra = u.get("additions") or {}
    out = {"start": u["start_time"] / 1000, "end": u["end_time"] / 1000, "text": u.get("text", "").strip()}
    if extra.get("speaker"):
        out["speaker"] = extra["speaker"]
    for k in ("emotion", "gender"):
        if extra.get(k):
            out[k] = extra[k]
    if extra.get("speech_rate"):
        out["speech_rate"] = round(float(extra["speech_rate"]), 2)
    # start_time -1 marks placeholder spaces between Chinese and Latin words.
    out["words"] = [{"start": w["start_time"] / 1000, "end": w["end_time"] / 1000, "text": w["text"]}
                    for w in u.get("words") or [] if w.get("start_time", -1) >= 0]
    return out


def _overlap(a: dict, b: dict) -> float:
    return max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))


def transcribe(path: str) -> dict:
    """Two passes: text + word times, then speaker labels mapped on by time overlap."""
    doubao_key()
    duration = probe_duration(path)
    b64 = base64.b64encode(encode_mp3(path, duration)).decode("ascii")
    if len(b64) > ASR_MAX_B64_BYTES:
        raise SpeechError("Audio exceeds 100MB base64 (~3.5h at 64 kbps); transcript skipped")
    log(f"asr pass 1/2: text + word timestamps ({duration:.0f}s)…")
    utts = [_utterance(u) for u in _asr_pass(b64, ASR_PASS_TEXT, duration)]
    log("asr pass 2/2: speaker labels…")
    labelled = [_utterance(u) for u in _asr_pass(b64, ASR_PASS_SPEAKER, duration)]
    for u in utts:
        best = max(labelled, key=lambda s: _overlap(u, s), default=None)
        if best and _overlap(u, best) > 0:
            u["speaker"] = best["speaker"]
    # Pass 1 can drop a speaker who cuts in without a pause; pass 2 keeps them, so fill the gaps from it.
    utts += [s for s in labelled if not any(_overlap(s, u) > 0 for u in utts)]
    utts.sort(key=lambda u: u["start"])
    return {"model": ASR_MODEL, "duration": round(duration, 2), "segments": utts}
