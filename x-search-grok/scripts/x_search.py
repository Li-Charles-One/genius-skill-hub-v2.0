#!/usr/bin/env python3
"""V1 X search helper for Grok-compatible relays.

Modes:
  keyword  - search posts by query
  account  - recent posts from one handle
  heat     - heat/sentiment briefing

Uses POST {base}/responses with tools=[{type: x_search}].
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "https://ai.0xs.one/v1"
# Prefer 4.3 for speed; 4.5 is automatic fallback only.
DEFAULT_MODEL = "grok-4.3"
DEFAULT_FALLBACK_MODELS = ["grok-4.5"]
DEFAULT_TIMEOUT = 180


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def strip_handle(value: str) -> str:
    value = value.strip()
    if value.startswith("@"):
        value = value[1:]
    return value.strip()


def load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def first_nonempty(*values: str | None) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def parse_model_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    items: list[str] = []
    for part in raw.replace(";", ",").split(","):
        name = part.strip()
        if name and name not in items:
            items.append(name)
    return items


def build_model_chain(primary: str, fallbacks: list[str]) -> list[str]:
    chain: list[str] = []
    for name in [primary, *fallbacks]:
        name = (name or "").strip()
        if name and name not in chain:
            chain.append(name)
    return chain or [DEFAULT_MODEL]


def load_config(cli_base: str, cli_key: str, cli_model: str, cli_timeout: int) -> dict[str, Any]:
    env = dict(os.environ)
    skill_env = load_dotenv(SKILL_DIR / ".env")

    base = first_nonempty(
        cli_base,
        env.get("GROK_API_BASE"),
        env.get("BASE_URL"),
        env.get("XAI_BASE_URL"),
        skill_env.get("GROK_API_BASE"),
        skill_env.get("BASE_URL"),
        skill_env.get("XAI_BASE_URL"),
    )
    key = first_nonempty(
        cli_key,
        skill_env.get("GROK_API_KEY"),
        skill_env.get("API_KEY"),
        skill_env.get("XAI_API_KEY"),
    )
    model = first_nonempty(
        cli_model,
        env.get("GROK_MODEL"),
        env.get("MODEL"),
        env.get("XAI_MODEL"),
        skill_env.get("GROK_MODEL"),
        skill_env.get("MODEL"),
        skill_env.get("XAI_MODEL"),
        DEFAULT_MODEL,
    )
    fallback_raw = first_nonempty(
        env.get("GROK_FALLBACK_MODELS"),
        env.get("GROK_MODEL_FALLBACKS"),
        skill_env.get("GROK_FALLBACK_MODELS"),
        skill_env.get("GROK_MODEL_FALLBACKS"),
        ",".join(DEFAULT_FALLBACK_MODELS),
    )
    fallbacks = parse_model_list(fallback_raw)
    timeout_raw = first_nonempty(
        str(cli_timeout) if cli_timeout else "",
        env.get("GROK_TIMEOUT_SECONDS"),
        skill_env.get("GROK_TIMEOUT_SECONDS"),
        str(DEFAULT_TIMEOUT),
    )

    base = (base or DEFAULT_BASE).rstrip("/")
    if base.endswith("/responses"):
        base = base[: -len("/responses")]
    if not base.endswith("/v1"):
        # Accept either https://host or https://host/v1
        base = base + "/v1"

    try:
        timeout = int(timeout_raw)
    except ValueError:
        timeout = DEFAULT_TIMEOUT

    if not key:
        raise SystemExit(
            "Missing API key. Pass --api-key or set GROK_API_KEY in skill .env"
        )

    primary = model or DEFAULT_MODEL
    return {
        "base": base,
        "key": key,
        "model": primary,
        "models": build_model_chain(primary, fallbacks),
        "timeout": timeout,
    }


def is_model_or_channel_error(result: dict[str, Any]) -> bool:
    """Return True when retrying another model is likely useful."""
    status = result.get("status")
    body = result.get("body")
    text = ""
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            text = " ".join(
                str(err.get(k) or "")
                for k in ("message", "type", "code", "param")
            )
        else:
            text = json.dumps(body, ensure_ascii=False)
    else:
        text = str(body or "")
    lowered = text.lower()
    markers = [
        "get_channel_failed",
        "no available channel",
        "available channel",
        "可用渠道不存在",
        "model_not_found",
        "model not found",
        "do not exist",
        "does not exist",
        "not support",
        "unsupported model",
        "无效的模型",
        "模型不存在",
        "无可用渠道",
    ]
    if any(m.lower() in lowered for m in markers):
        return True
    # Some relays return bare 404/503 for missing model routes.
    if status in (404, 503) and ("model" in lowered or "channel" in lowered or "渠道" in text):
        return True
    return False


def since_to_instruction(since: str | None) -> str:
    if not since:
        return "Prefer the most recent posts available."
    since = since.strip().lower()
    mapping = {
        "1h": "last 1 hour",
        "3h": "last 3 hours",
        "12h": "last 12 hours",
        "1d": "last 1 day",
        "3d": "last 3 days",
        "7d": "last 7 days",
        "30d": "last 30 days",
    }
    label = mapping.get(since, since)
    return f"Focus on posts from the {label}."


def build_prompt(mode: str, query: str, limit: int, since: str | None, lang: str) -> str:
    language = "Simplified Chinese" if lang.startswith("zh") else "English"
    recency = since_to_instruction(since)

    if mode == "keyword":
        return f"""Use X search (x_search). Search X for recent posts about:

QUERY: {query}

Requirements:
- Actually search X. Do not invent posts.
- {recency}
- Return up to {limit} useful posts.
- Language of the final answer: {language}
- Output format:
  1) one-line overview
  2) bullet list of posts
  Each bullet: author handle, approximate time if available, one-line summary, and x.com URL
- Prefer original posts over pure spam/airdrop noise.
- If nothing useful is found, say so clearly.
"""

    if mode == "account":
        handle = strip_handle(query)
        return f"""Use X search (x_search). Fetch recent posts from this X account:

HANDLE: @{handle}
Search hint: from:{handle}

Requirements:
- Actually search X. Do not invent posts.
- {recency}
- Return up to {limit} recent posts from this account only.
- Language of the final answer: {language}
- Output format:
  1) one-line summary of what this account has been posting
  2) bullet list of recent posts with time, one-line summary, and x.com URL
- If the account has few/no recent posts, say so clearly.
"""

    # heat
    return f"""Use X search (x_search). Build a heat/sentiment briefing for:

TOPIC: {query}

Requirements:
- Actually search X. Do not invent posts.
- {recency}
- Cover overall heat, sentiment, and representative discussion.
- Language of the final answer: {language}
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
- Prefer high-signal posts and official/source posts when available.
- If evidence is thin, say the confidence is low.
"""


def request_responses(cfg: dict[str, Any], prompt: str, max_tool_calls: int) -> dict[str, Any]:
    url = cfg["base"].rstrip("/") + "/responses"
    payload = {
        "model": cfg["model"],
        "input": [{"role": "user", "content": prompt}],
        "tools": [{"type": "x_search"}],
        "max_tool_calls": max_tool_calls,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {cfg['key']}",
            "Content-Type": "application/json",
            "User-Agent": "x-search-grok-skill/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
            body = resp.read().decode("utf-8", "replace")
            return {
                "ok": True,
                "status": resp.status,
                "body": json.loads(body),
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            parsed: Any = json.loads(raw)
        except Exception:
            parsed = raw
        return {
            "ok": False,
            "status": exc.code,
            "body": parsed,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": None,
            "body": f"{type(exc).__name__}: {exc}",
        }


def extract_text(response_body: dict[str, Any]) -> str:
    chunks: list[str] = []
    for item in response_body.get("output") or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if content.get("type") in ("output_text", "text"):
                text = content.get("text")
                if text:
                    chunks.append(text)
    if chunks:
        return "\n".join(chunks).strip()

    # Some relays may flatten text.
    for key in ("output_text", "content", "result"):
        value = response_body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def extract_tool_stats(response_body: dict[str, Any]) -> dict[str, Any]:
    usage = response_body.get("usage") or {}
    details = usage.get("server_side_tool_usage_details") or {}
    tool_names: list[str] = []
    for item in response_body.get("output") or []:
        if item.get("type") in ("custom_tool_call", "x_search_call", "web_search_call", "function_call"):
            name = item.get("name") or item.get("type")
            if name:
                tool_names.append(str(name))
    return {
        "x_search_calls": details.get("x_search_calls"),
        "web_search_calls": details.get("web_search_calls"),
        "num_server_side_tools_used": usage.get("num_server_side_tools_used"),
        "tool_names": tool_names,
        "usage": usage,
    }


def mode_tool_budget(mode: str) -> int:
    if mode == "heat":
        return 4
    if mode == "account":
        return 2
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="V1 X search via Grok-compatible x_search")
    parser.add_argument("mode", choices=["keyword", "account", "heat"], help="V1 mode")
    parser.add_argument("query", help="Search query or account handle")
    parser.add_argument("--limit", type=int, default=8, help="Max items to request")
    parser.add_argument("--since", default="7d", help="Recency window, e.g. 1d/3d/7d")
    parser.add_argument("--lang", default="zh", help="zh or en")
    parser.add_argument("--base-url", default="", help="Override API base URL")
    parser.add_argument("--api-key", default="", help="Override API key")
    parser.add_argument("--model", default="", help="Override model")
    parser.add_argument("--timeout", type=int, default=0, help="Timeout seconds")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--raw", action="store_true", help="Include raw response body in JSON mode")
    args = parser.parse_args()

    if args.limit < 1:
        args.limit = 1
    if args.limit > 20:
        args.limit = 20

    cfg = load_config(args.base_url, args.api_key, args.model, args.timeout)
    prompt = build_prompt(args.mode, args.query, args.limit, args.since, args.lang)
    started = datetime.now(timezone.utc)
    models = list(cfg.get("models") or [cfg["model"]])
    attempts: list[dict[str, Any]] = []
    result: dict[str, Any] | None = None
    used_model = cfg["model"]

    for index, model_name in enumerate(models):
        cfg["model"] = model_name
        used_model = model_name
        one = request_responses(cfg, prompt, mode_tool_budget(args.mode))
        attempts.append(
            {
                "model": model_name,
                "ok": one.get("ok"),
                "status": one.get("status"),
            }
        )
        if one.get("ok"):
            result = one
            if index > 0:
                eprint(f"Primary model unavailable; fell back to {model_name}")
            break
        # Retry only for model/channel style failures.
        if index < len(models) - 1 and is_model_or_channel_error(one):
            eprint(
                f"Model {model_name} failed (status={one.get('status')}); "
                f"trying fallback {models[index + 1]}"
            )
            continue
        result = one
        break

    if result is None:
        result = {
            "ok": False,
            "status": None,
            "body": "No model attempts were made.",
        }

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    cfg["model"] = used_model

    if not result["ok"]:
        payload = {
            "ok": False,
            "mode": args.mode,
            "query": args.query,
            "status": result["status"],
            "elapsed_seconds": round(elapsed, 2),
            "base": cfg["base"],
            "model": used_model,
            "models_tried": [a.get("model") for a in attempts],
            "attempts": attempts,
            "error": result["body"],
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            eprint("X search failed.")
            eprint(
                f"status={result['status']} base={cfg['base']} "
                f"model={used_model} tried={','.join(a.get('model','') for a in attempts)}"
            )
            print(
                json.dumps(result["body"], ensure_ascii=False, indent=2)
                if isinstance(result["body"], (dict, list))
                else result["body"]
            )
        return 2

    body = result["body"]
    text = extract_text(body if isinstance(body, dict) else {})
    stats = extract_tool_stats(body if isinstance(body, dict) else {})
    fell_back = len(attempts) > 1 and attempts[0].get("model") != used_model

    if args.json:
        payload = {
            "ok": True,
            "mode": args.mode,
            "query": args.query,
            "status": result["status"],
            "elapsed_seconds": round(elapsed, 2),
            "base": cfg["base"],
            "model": used_model,
            "fell_back": fell_back,
            "models_tried": [a.get("model") for a in attempts],
            "attempts": attempts,
            "text": text,
            "stats": stats,
        }
        if args.raw:
            payload["raw"] = body
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        header = [
            f"mode={args.mode}",
            f"model={used_model}",
            f"elapsed={elapsed:.1f}s",
        ]
        if fell_back:
            header.append("fell_back=1")
        if stats.get("x_search_calls") is not None:
            header.append(f"x_search_calls={stats['x_search_calls']}")
        print(" | ".join(header))
        print()
        print(text or "No text returned by the relay.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
