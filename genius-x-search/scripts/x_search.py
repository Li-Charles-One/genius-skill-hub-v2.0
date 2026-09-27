#!/usr/bin/env python3
"""X search via a Grok-compatible relay: POST {base}/responses with tools=[{type: x_search}].

Modes: keyword | account | heat. Channels come from channels.json, keys from .env.
Failover: channel -> model chain; one retry only for 429/5xx/connection resets.
Timeouts and empty answers move straight to the next model.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parents[1]
CHANNELS_PATH = SKILL_DIR / "channels.json"
DEFAULT_TIMEOUT = 90
RETRY_SLEEP_SECONDS = 1.5
TRANSIENT_STATUS = (429, 500, 502, 503, 504)
TOOL_BUDGET = {"keyword": 2, "account": 2, "heat": 4}
SINCE_LABELS = {"1h": "1 hour", "3h": "3 hours", "12h": "12 hours", "1d": "1 day",
                "3d": "3 days", "7d": "7 days", "30d": "30 days"}


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def load_dotenv(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def load_channels(force: str = "") -> list[dict[str, Any]]:
    """Return channels sorted by priority, each with its resolved key (may be empty)."""
    try:
        data = json.loads(CHANNELS_PATH.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Cannot read {CHANNELS_PATH.name}: {exc}") from exc
    env = {**load_dotenv(SKILL_DIR / ".env"), **os.environ}
    channels = []
    for item in data.get("channels") or []:
        cid = str(item.get("id") or "").strip()
        if not cid or (force and cid != force):
            continue
        # A forced channel may be a disabled slot, for explicit testing.
        if not force and not item.get("enabled", True):
            continue
        key_env = item.get("key_env") or [f"CHANNEL_{cid.upper().replace('-', '_')}_KEY"]
        channels.append({
            "id": cid,
            "priority": int(item.get("priority", 100)),
            "enabled": bool(item.get("enabled", True)),
            "base": str(item.get("base") or "").rstrip("/"),
            "models": list(item.get("models") or []),
            "key_env": key_env,
            "key": next((env[k].strip() for k in key_env if env.get(k, "").strip()), ""),
        })
    if force and not channels:
        raise SystemExit(f"Unknown channel '{force}' in {CHANNELS_PATH.name}")
    return sorted(channels, key=lambda c: (c["priority"], c["id"]))


def list_channels(force: str) -> int:
    channels = load_channels(force)
    print(f"registry={CHANNELS_PATH}")
    for rank, ch in enumerate(channels, start=1):
        status = "ready" if ch["key"] and ch["base"] and ch["models"] else "not-ready"
        print(f"#{rank} id={ch['id']} priority={ch['priority']} enabled={ch['enabled']} status={status}")
        print(f"    base={ch['base'] or '-'}")
        print(f"    models={','.join(ch['models']) or '-'}")
        print(f"    key_env={','.join(ch['key_env'])} key_set={'yes' if ch['key'] else 'no'}")
    return 0 if channels else 1


def build_prompt(mode: str, query: str, limit: int, since: str, lang: str) -> str:
    language = "Simplified Chinese" if lang.startswith("zh") else "English"
    window = SINCE_LABELS.get(since.strip().lower(), since.strip())
    common = f"""- Actually search X. Do not invent posts or URLs.
- Focus on posts from the last {window}.
- Language of the final answer: {language}"""

    if mode == "keyword":
        return f"""Use X search (x_search). Search X for recent posts about:

QUERY: {query}

Requirements:
{common}
- Return up to {limit} useful posts.
- Output: 1) one-line overview 2) bullet list; each bullet has author handle, approximate time, one-line summary, and x.com URL
- Prefer original posts over spam/airdrop noise.
- If nothing useful is found, say so clearly.
"""

    if mode == "account":
        handle = query.strip().lstrip("@").strip()
        return f"""Use X search (x_search). Fetch recent posts from this X account:

HANDLE: @{handle}
Search hint: from:{handle}

Requirements:
{common}
- Return up to {limit} recent posts from this account only.
- Output: 1) one-line summary of what this account has been posting 2) bullet list of posts with time, one-line summary, and x.com URL
- If the account has few or no recent posts, say so clearly.
"""

    return f"""Use X search (x_search). Build a heat/sentiment briefing for:

TOPIC: {query}

Requirements:
{common}
- Cover overall heat, sentiment, and representative discussion. State the time window and roughly how many posts you saw.
- Output format in markdown:
  ## 热度简报
  - 热度判断
  - 情绪判断
  ## 代表性讨论
  - 4 to {limit} posts with author, one-line point, and x.com URL
  ## 主要好评
  - bullets
  ## 主要争议或差评
  - bullets
- Prefer high-signal and official/source posts.
- If evidence is thin, say the confidence is low.
"""


def request_responses(ch: dict[str, Any], model: str, timeout: int, prompt: str, tool_budget: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "input": [{"role": "user", "content": prompt}],
        "tools": [{"type": "x_search"}],
        "max_tool_calls": tool_budget,
    }
    req = urllib.request.Request(
        ch["base"] + "/responses",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {ch['key']}",
            "Content-Type": "application/json",
            "User-Agent": "genius-x-search-skill/2.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": True, "status": resp.status, "body": json.loads(resp.read().decode("utf-8", "replace"))}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            body: Any = json.loads(raw)
        except ValueError:
            body = raw
        return {"ok": False, "status": exc.code, "body": body}
    except Exception as exc:  # noqa: BLE001
        reason = getattr(exc, "reason", exc)
        timed_out = isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason)
        return {"ok": False, "status": None, "timeout": timed_out, "body": f"{type(exc).__name__}: {exc}"}


def extract_text(body: dict[str, Any]) -> str:
    chunks = [
        c["text"]
        for item in body.get("output") or []
        if item.get("type") == "message"
        for c in item.get("content") or []
        if c.get("type") in ("output_text", "text") and c.get("text")
    ]
    if chunks:
        return "\n".join(chunks).strip()
    value = body.get("output_text")
    return value.strip() if isinstance(value, str) else ""


def run_with_failover(channels: list[dict[str, Any]], timeout: int, prompt: str, tool_budget: int):
    attempts: list[dict[str, Any]] = []
    last: dict[str, Any] = {"ok": False, "status": None, "body": "No usable channel (missing key, base, or models)."}
    for ch in channels:
        if not (ch["key"] and ch["base"] and ch["models"]):
            eprint(f"Skip channel '{ch['id']}': missing key, base, or models")
            continue
        skip_channel = False
        for model in ch["models"]:
            for attempt in (1, 2):
                started = time.monotonic()
                result = request_responses(ch, model, timeout, prompt, tool_budget)
                text = extract_text(result["body"]) if result["ok"] and isinstance(result["body"], dict) else ""
                if result["ok"] and not text:
                    result = {**result, "ok": False, "body": "Relay returned 200 with no answer text."}
                result.update(channel=ch["id"], model=model, text=text)
                attempts.append({"channel": ch["id"], "model": model, "attempt": attempt, "ok": result["ok"],
                                 "status": result["status"], "seconds": round(time.monotonic() - started, 2)})
                last = result
                status = result["status"]
                if result["ok"]:
                    return result, attempts
                error = result["body"].get("error") if isinstance(result["body"], dict) else None
                model_missing = isinstance(error, dict) and (
                    error.get("code") == "model_not_found" or error.get("param") == "model")
                if status in (400, 422) and not model_missing:
                    eprint(f"Bad request on {ch['id']}:{model}; stop")
                    return result, attempts
                if status in (401, 403):
                    eprint(f"Auth failed on {ch['id']} (status={status}); skipping channel")
                    skip_channel = True
                    break
                transient = status in TRANSIENT_STATUS or (status is None and not result.get("timeout"))
                if transient and attempt == 1:
                    eprint(f"Transient error on {ch['id']}:{model} (status={status}); retrying once")
                    time.sleep(RETRY_SLEEP_SECONDS)
                    continue
                eprint(f"{ch['id']}:{model} failed (status={status}); trying next model")
                break
            if skip_channel:
                break
    return last, attempts


def main() -> int:
    parser = argparse.ArgumentParser(description="X search via Grok-compatible x_search")
    parser.add_argument("mode", nargs="?", choices=["keyword", "account", "heat"])
    parser.add_argument("query", nargs="?", help="Search query or account handle")
    parser.add_argument("--limit", type=int, default=8, help="Max posts to request (1-20)")
    parser.add_argument("--since", default="7d", help="Recency window: 1h/3h/12h/1d/3d/7d/30d")
    parser.add_argument("--lang", default="zh", help="zh or en")
    parser.add_argument("--model", default="", help="Use only this model")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Per-request timeout seconds")
    parser.add_argument("--channel", default="", help="Use only this channel id from channels.json")
    parser.add_argument("--list-channels", action="store_true", help="Show channels and readiness")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--raw", action="store_true", help="Include raw response body in JSON mode")
    args = parser.parse_args()

    if args.list_channels:
        return list_channels(args.channel.strip())
    if not args.mode or not args.query:
        parser.error("mode and query are required unless --list-channels is set")

    channels = load_channels(args.channel.strip())
    if args.model:
        for ch in channels:
            ch["models"] = [args.model]
    limit = min(max(args.limit, 1), 20)
    prompt = build_prompt(args.mode, args.query, limit, args.since, args.lang)

    started = time.monotonic()
    result, attempts = run_with_failover(channels, args.timeout, prompt, TOOL_BUDGET[args.mode])
    elapsed = round(time.monotonic() - started, 2)
    body = result.get("body")
    usage = (body.get("usage") or {}) if isinstance(body, dict) else {}
    x_calls = (usage.get("server_side_tool_usage_details") or {}).get("x_search_calls")
    fell_back = len(attempts) > 1

    if args.json:
        payload = {
            "ok": result["ok"], "mode": args.mode, "query": args.query, "status": result.get("status"),
            "elapsed_seconds": elapsed, "channel": result.get("channel", ""), "model": result.get("model", ""),
            "fell_back": fell_back, "attempts": attempts,
        }
        if result["ok"]:
            payload.update(text=result["text"], stats={"x_search_calls": x_calls, "usage": usage})
            if args.raw:
                payload["raw"] = body
        else:
            payload["error"] = body
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 2

    if not result["ok"]:
        tried = ",".join(f"{a['channel']}:{a['model']}" for a in attempts) or "-"
        eprint(f"X search failed. status={result.get('status')} tried={tried}")
        print(json.dumps(body, ensure_ascii=False, indent=2) if isinstance(body, (dict, list)) else body)
        return 2

    header = [f"mode={args.mode}", f"channel={result['channel']}", f"model={result['model']}", f"elapsed={elapsed:.1f}s"]
    if fell_back:
        header.append("fell_back=1")
    if x_calls is not None:
        header.append(f"x_search_calls={x_calls}")
    print(" | ".join(header))
    print()
    print(result["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
