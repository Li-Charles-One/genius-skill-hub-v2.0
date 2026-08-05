#!/usr/bin/env python3
import importlib.util
import json
import struct
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("cpa_image", HERE / "cpa_image.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

print("=== load ===")
assert "gemini-3.1-flash-image" in mod.MODELS
assert "gpt-image-2" in mod.MODELS
assert mod.MODELS["gemini-3.1-flash-image"]["provider"] == "cpa-jp"
assert mod.MODELS["gpt-image-2"]["provider"] == "cpa-us"
assert "2K" in mod.MODELS["gemini-3.1-flash-image"]["resolutions"]
assert "1:4" in mod.MODELS["gemini-3.1-flash-image"]["aspects"]
assert "16:9" in mod.MODELS["gpt-image-2"]["aspects"]
assert "9:21" in mod.MODELS["gpt-image-2"]["aspects"]
assert "2:1" in mod.MODELS["gpt-image-2"]["aspects"]
assert "1K" in mod.MODELS["gpt-image-2"]["resolutions"]
assert "4K" in mod.MODELS["gpt-image-2"]["resolutions"]  # alias, coerces to 1K
assert mod.MODELS["gpt-image-2"]["flexible_size"] is False
print("  PASS models + providers")

print("=== validate gemini defaults ===")
t = mod.validate_task({"prompt": "cat"})
assert t["model"] == "gemini-3.1-flash-image"
assert t["provider"] == "cpa-jp"
assert t["api"] == "generateContent"
assert t["aspect"] == "1:1" and t["resolution"] == "1K"
t = mod.validate_task({"prompt": "cat", "aspect": "16:9", "resolution": "2k"})
assert t["resolution"] == "2K"
print("  PASS gemini defaults + case normalize")

print("=== validate gpt-image-2 CPA-US 1K matrix ===")
t = mod.validate_task({"prompt": "cat", "model": "gpt-image-2"})
assert t["provider"] == "cpa-us"
assert t["api"] == "images"
assert t["aspect"] == "1:1"
assert t["resolution"] == "1K"
assert t["size"] == "1024x1024"
assert t["quality"] == "auto"
assert t["output_format"] == "png"

# Observed CPA-US 1K presets; 2K/4K aliases coerce to same 1K size
cases = {
    ("1:1", "1K"): "1024x1024",
    ("1:1", "2K"): "1024x1024",
    ("1:1", "4K"): "1024x1024",
    ("3:2", "1K"): "1536x1024",
    ("2:3", "1K"): "1024x1536",
    ("16:9", "1K"): "1672x941",
    ("16:9", "2K"): "1672x941",
    ("16:9", "4K"): "1672x941",
    ("9:16", "1K"): "941x1672",
    ("9:16", "4K"): "941x1672",
    ("4:3", "1K"): "1443x1090",
    ("3:4", "1K"): "1090x1443",
    ("5:4", "1K"): "1408x1120",
    ("4:5", "1K"): "1120x1408",
    ("21:9", "1K"): "1920x832",
    ("9:21", "1K"): "832x1920",
    ("2:1", "1K"): "1792x896",
    ("1:2", "1K"): "896x1792",
}
for (a, r), size in cases.items():
    t = mod.validate_task({
        "prompt": "x", "model": "gpt-image-2", "aspect": a, "resolution": r,
    })
    assert t["size"] == size, (a, r, t["size"], size)
    # resolution field must be real tier after coerce
    if r in ("2K", "4K"):
        assert t["resolution"] == "1K", (a, r, t["resolution"])

t = mod.validate_task({
    "prompt": "wide",
    "model": "gpt-image-2",
    "aspect": "3:2",
    "quality": "low",
    "output_format": "jpg",
})
assert t["size"] == "1536x1024"
assert t["output_format"] == "jpeg"

# resolution 4K must print a visible coerce note (not silent)
import io
import contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    t = mod.validate_task({
        "prompt": "note-check",
        "model": "gpt-image-2",
        "aspect": "16:9",
        "resolution": "4K",
    })
note_out = buf.getvalue()
assert t["size"] == "1672x941" and t["resolution"] == "1K"
assert "coerced to 1K" in note_out, note_out
assert "no 4K resolution" in note_out, note_out

# legacy 4K request coerces to CPA 1K 16:9
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    t = mod.validate_task({
        "prompt": "direct",
        "model": "gpt-image-2",
        "size": "3840x2160",
    })
size_note = buf.getvalue()
assert t["size"] == "1672x941"
assert t["aspect"] == "16:9"
assert t["resolution"] == "1K"
assert "coerced to 1K preset 1672x941" in size_note, size_note

# exact CPA preset passes through
t = mod.validate_task({
    "prompt": "exact",
    "model": "gpt-image-2",
    "size": "1672x941",
})
assert t["size"] == "1672x941"
assert t["aspect"] == "16:9"
assert t["resolution"] == "1K"

# all map entries must be legal CPA presets
for (a, r), size in mod.GPT_IMAGE_SIZE_MAP.items():
    if size == "auto":
        continue
    assert mod.parse_gpt_image_size_string(size) == size, ((a, r), size)
print("  PASS gpt-image-2 CPA-US 1K mapping")

print("=== gpt-image size constraints ===")
for bad in ["1000x1000", "10000x10000", "3840x1000", "16x16", "2560x1441"]:
    try:
        mod.validate_task({"prompt": "x", "model": "gpt-image-2", "size": bad})
        raise SystemExit(f"FAIL should reject {bad}")
    except RuntimeError:
        print(f"  PASS rejects {bad}")

print("=== param ownership ===")
try:
    mod.validate_task({"prompt": "x", "quality": "high"})
    raise SystemExit("FAIL gemini should reject quality")
except RuntimeError:
    print("  PASS gemini rejects quality")
try:
    mod.validate_task({"prompt": "x", "output_format": "png"})
    raise SystemExit("FAIL gemini should reject output_format")
except RuntimeError:
    print("  PASS gemini rejects output_format")
try:
    mod.validate_task({
        "prompt": "x",
        "model": "gpt-image-2",
        "google_search": True,
    })
    raise SystemExit("FAIL gpt-image should reject google_search")
except RuntimeError:
    print("  PASS gpt-image rejects google_search")

print("=== gemini body shape ===")
body = mod.build_generate_content_body(mod.validate_task({
    "prompt": "a cat", "aspect": "16:9", "resolution": "2K", "google_search": True
}))
assert body["generationConfig"]["imageConfig"]["aspectRatio"] == "16:9"
assert body["generationConfig"]["imageConfig"]["imageSize"] == "2K"
assert body["generationConfig"]["responseModalities"] == ["IMAGE"]
assert body.get("tools") == [{"google_search": {}}]
assert body["contents"][0]["parts"][0]["text"] == "a cat"
print("  PASS generateContent body")

print("=== ref local inlineData ===")
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / "a.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n")
    parts = mod.resolve_ref_parts([str(p)])
    assert parts[0]["inlineData"]["mimeType"] == "image/png"
    assert parts[0]["inlineData"]["data"]
    name, mime, raw = mod.load_ref_bytes(str(p))
    assert mime == "image/png" and raw.startswith(b"\x89PNG")
    print("  PASS ref helpers")

print("=== extract gemini images ===")
fake = {
    "candidates": [{
        "content": {
            "parts": [
                {"inlineData": {"mimeType": "image/jpeg", "data": "aGVsbG8="}},
                {"text": "caption"},
            ]
        }
    }]
}
imgs, texts = mod.extract_images_from_generate_content(fake)
assert imgs[0]["data"] == b"hello" and texts == ["caption"]
print("  PASS extract gemini")

print("=== extract openai images ===")
import base64
fake = {
    "created": 1,
    "data": [{"b64_json": base64.b64encode(b"pngbytes").decode()}],
}
imgs, texts = mod.extract_images_from_openai_images(fake)
assert imgs[0]["data"] == b"pngbytes"
print("  PASS extract openai images")

print("=== image_dimensions ===")
# minimal PNG with IHDR 2048x1152
png = bytearray(b"\x89PNG\r\n\x1a\n")
ihdr_data = struct.pack(">II", 2048, 1152) + bytes([8, 2, 0, 0, 0])
png += struct.pack(">I", 13) + b"IHDR" + ihdr_data + b"\x00\x00\x00\x00"
w, h = mod.image_dimensions(bytes(png))
assert (w, h) == (2048, 1152)
print("  PASS image_dimensions PNG")

print("=== batch mixed models ===")
with tempfile.TemporaryDirectory() as td:
    batch = Path(td) / "b.json"
    batch.write_text(json.dumps([
        {"prompt": "a", "resolution": "1K"},
        {"prompt": "b", "model": "gpt-image-2", "aspect": "16:9", "resolution": "2K", "quality": "low"},
        {"prompt": "c", "model": "gpt-image-2", "size": "2160x3840"},
    ]), encoding="utf-8")
    tasks = mod.load_batch(str(batch))
    assert tasks[0]["provider"] == "cpa-jp"
    assert tasks[1]["model"] == "gpt-image-2"
    # 2K alias and legacy 4K size both coerce to CPA-US 1K
    assert tasks[1]["size"] == "1672x941"
    assert tasks[1]["resolution"] == "1K"
    assert tasks[2]["size"] == "941x1672"
    assert tasks[2]["resolution"] == "1K"
    print("  PASS batch multi-model")

print("=== local job store ===")
with tempfile.TemporaryDirectory() as td:
    out = Path(td)
    mod.OUT_DIR = out
    mod.JOBS_DIR = out / "Jobs"
    mod.LOG_DIR = out / "Logs"
    mod.LOG_FILE = mod.LOG_DIR / "cpa_image_log.jsonl"
    job_id = mod.new_job_id("test")
    job = {
        "job_id": job_id,
        "kind": "single",
        "status": "queued",
        "created_at": mod.now_iso(),
        "payload": {"task": {"prompt": "x"}, "name": "n"},
        "result": None,
        "error": None,
    }
    path = mod.write_job(job)
    assert path.is_file()
    loaded = mod.read_job(job_id)
    assert loaded["status"] == "queued"
    mod.update_job(job_id, status="running", pid=123)
    assert mod.read_job(job_id)["status"] == "running"
    assert mod.is_terminal_status("success")
    assert not mod.is_terminal_status("running")
    print("  PASS job store")

print("=== cooldown fail-fast ===")
body = json.dumps({
    "error": {
        "code": "model_cooldown",
        "message": "All credentials cooling down",
        "model": "gemini-3.1-flash-image",
        "provider": "antigravity",
        "reset_seconds": 100,
        "reset_time": "1h40m",
    }
})
msg = mod.format_http_error(429, body)
assert "model_cooldown" in msg
assert "reset_time=1h40m" in msg
assert "reset_seconds=100" in msg
assert mod.is_non_retryable_error(RuntimeError(msg))
assert mod.is_non_retryable_error(RuntimeError("HTTP 400: bad aspect"))
assert mod.is_non_retryable_error(RuntimeError("auth_unavailable"))
assert not mod.is_non_retryable_error(RuntimeError("request failed 3 times: timeout"))
print("  PASS cooldown formatting + no-retry policy")


print("=== log rotation ===")
import os
import time
with tempfile.TemporaryDirectory() as td:
    out = Path(td)
    mod.OUT_DIR = out
    mod.LOG_DIR = out / "Logs"
    mod.JOBS_DIR = out / "Jobs"
    mod.LOG_FILE = mod.LOG_DIR / "cpa_image_log.jsonl"
    mod.LOG_DIR.mkdir(parents=True)
    mod.JOBS_DIR.mkdir(parents=True)

    # size rotate main log
    mod.LOG_FILE.write_bytes(b"x" * 2048)
    os.environ["CPA_IMAGE_LOG_MAX_BYTES"] = "1000"
    # clear mb override if any
    os.environ.pop("CPA_IMAGE_LOG_MAX_MB", None)
    # reload file keys not needed; env preferred
    arch = mod.rotate_file_by_size(mod.LOG_FILE, 1000, archive_name="cpa_image_log_testarch.jsonl", label="log")
    assert arch is not None and arch.exists()
    assert not mod.LOG_FILE.exists()
    # recreate active and write_log should work
    mod.write_log({"hello": 1})
    assert mod.LOG_FILE.exists()

    # age prune archives
    old = mod.LOG_DIR / "cpa_image_log_old.jsonl"
    old.write_text("old\n")
    old_mtime = time.time() - 10 * 86400
    os.utime(old, (old_mtime, old_mtime))
    os.environ["CPA_IMAGE_LOG_KEEP_DAYS"] = "7"
    os.environ["CPA_IMAGE_LOG_MAX_ARCHIVES"] = "20"
    os.environ["CPA_IMAGE_JOB_KEEP_DAYS"] = "7"
    os.environ["CPA_IMAGE_JOB_MAX_FILES"] = "2"
    os.environ["CPA_IMAGE_JOB_LOG_MAX_BYTES"] = "500"
    mod.clean_old_logs()
    assert not old.exists(), "old archive should be removed by age"

    # job log rotate + prune excess status
    for i in range(4):
        jid = f"cpa-20260805_12000{i}-abcd{i:04d}"
        (mod.JOBS_DIR / f"{jid}.json").write_text("{\"job_id\":\"%s\"}" % jid)
        lp = mod.JOBS_DIR / f"{jid}.log"
        lp.write_bytes(b"y" * 2000)
    # rotate active oversized
    mod.clean_old_logs()
    # after prune max status files=2, only 2 json remain
    jsons = list(mod.JOBS_DIR.glob("*.json"))
    assert len(jsons) <= 2, jsons
    # oversized active logs should have been rotated (original gone or archived)
    # at least some rotated logs exist or sizes capped
    logs = list(mod.JOBS_DIR.glob("*.log"))
    assert logs, "job logs should remain/rotated"
    print("  PASS log/job rotation + prune")

# cleanup env overrides so later imports in same process are clean
for k in [
    "CPA_IMAGE_LOG_MAX_BYTES", "CPA_IMAGE_LOG_MAX_MB", "CPA_IMAGE_LOG_KEEP_DAYS",
    "CPA_IMAGE_LOG_MAX_ARCHIVES", "CPA_IMAGE_JOB_KEEP_DAYS", "CPA_IMAGE_JOB_MAX_FILES",
    "CPA_IMAGE_JOB_LOG_MAX_BYTES", "CPA_IMAGE_JOB_LOG_MAX_MB",
]:
    os.environ.pop(k, None)


print("=== self-test done ===")
