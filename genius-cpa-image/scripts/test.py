#!/usr/bin/env python3
import importlib.util
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("cpa_image", HERE / "cpa_image.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

print("=== load ===")
assert "gemini-3.1-flash-image" in mod.MODELS
assert "2K" in mod.MODELS["gemini-3.1-flash-image"]["resolutions"]
assert "1:4" in mod.MODELS["gemini-3.1-flash-image"]["aspects"]
print("  PASS models + imageConfig ranges")

print("=== validate defaults ===")
t = mod.validate_task({"prompt": "cat"})
assert t["aspect"] == "1:1" and t["resolution"] == "1K"
t = mod.validate_task({"prompt": "cat", "aspect": "16:9", "resolution": "2k"})
assert t["resolution"] == "2K"
print("  PASS defaults + case normalize")

print("=== banned params ===")
for banned, val in [("quality", "high"), ("output_format", "png")]:
    try:
        mod.validate_task({"prompt": "x", banned: val})
        raise SystemExit(f"FAIL should reject {banned}")
    except RuntimeError:
        print(f"  PASS rejects {banned}")

print("=== body shape ===")
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
    print("  PASS ref -> inlineData")

print("=== extract images ===")
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
print("  PASS extract")

print("=== batch ===")
with tempfile.TemporaryDirectory() as td:
    batch = Path(td) / "b.json"
    batch.write_text(json.dumps([
        {"prompt": "a", "resolution": "1K"},
        {"prompt": "b", "aspect": "1:4"},
    ]), encoding="utf-8")
    tasks = mod.load_batch(str(batch))
    assert tasks[1]["aspect"] == "1:4"
    print("  PASS batch")

print("=== self-test done ===")
