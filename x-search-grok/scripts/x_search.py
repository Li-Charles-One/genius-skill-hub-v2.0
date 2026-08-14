#!/usr/bin/env python3
"""V1 X search helper for Grok-compatible relays.

Modes:
  keyword  - search posts by query
  account  - recent posts from one handle
  heat     - heat/sentiment briefing

Uses POST {base}/responses with tools=[{type: x_search}].

Failover:
  channel (provider) -> model chain -> one transient retry
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
CHANNELS_PATH = SKILL_DIR / "channels.json"
DEFAULT_BASE = "https://cpa.artistic-genius.vip/v1"
DEFAULT_MODEL = "grok-3-mini-fast"
DEFAULT_FALLBACK_MODELS: list[str] = []
DEFAULT_TIMEOUT = 180
DEFAULT_TRANSIENT_RETRIES = 1
DEFAULT_RETRY_SLEEP_SECONDS = 1.5


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


def parse_csv_list(raw: str | None) -> list[str]:
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


def normalize_base(base: str) -> str:
    base = (base or DEFAULT_BASE).rstrip("/")
    if base.endswith("/responses"):
        base = base[: -len("/responses")]
    if not base.endswith("/v1"):
        base = base + "/v1"
    return base


def channel_env_key(name: str, field: str) -> str:
    token = name.strip().upper().replace("-", "_")
    return f"CHANNEL_{token}_{field}"


def lookup_merged(env: dict[str, str], skill_env: dict[str, str], key: str) -> str:
    return first_nonempty(env.get(key), skill_env.get(key))


def as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return parse_csv_list(value)
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in out:
                out.append(text)
        return out
    return []


def load_channel_registry() -> list[dict[str, Any]]:
    """Load swappable channel interface from channels.json."""
    if not CHANNELS_PATH.exists():
        return []
    try:
        data = json.loads(CHANNELS_PATH.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Invalid channels.json: {exc}") from exc

    raw_channels = data.get("channels") if isinstance(data, dict) else data
    if not isinstance(raw_channels, list):
        raise SystemExit("channels.json must contain a top-level 'channels' array")

    registry: list[dict[str, Any]] = []
    for item in raw_channels:
        if not isinstance(item, dict):
            continue
        channel_id = str(item.get("id") or "").strip()
        if not channel_id:
            continue
        try:
            priority = int(item.get("priority", 100))
        except (TypeError, ValueError):
            priority = 100
        registry.append(
            {
                "id": channel_id,
                "priority": priority,
                "enabled": bool(item.get("enabled", True)),
                "base": str(item.get("base") or "").strip(),
                "models": as_str_list(item.get("models")),
                "key_env": as_str_list(item.get("key_env"))
                or [channel_env_key(channel_id, "KEY")],
            }
        )
    return registry


def resolve_key(
    key_env_names: list[str],
    env: dict[str, str],
    skill_env: dict[str, str],
    cli_key: str = "",
) -> str:
    values = [cli_key]
    for name in key_env_names:
        values.append(env.get(name))
        values.append(skill_env.get(name))
    return first_nonempty(*values)


def resolve_base(
    channel_id: str,
    registry_base: str,
    env: dict[str, str],
    skill_env: dict[str, str],
    cli_base: str = "",
) -> str:
    base = first_nonempty(
        cli_base,
        lookup_merged(env, skill_env, channel_env_key(channel_id, "BASE")),
        lookup_merged(env, skill_env, channel_env_key(channel_id, "BASE_URL")),
        registry_base,
    )
    if base:
        return base
    # Legacy base only applies to primary/default, never bleed into backup slots.
    if channel_id in ("primary", "default"):
        return first_nonempty(
            env.get("GROK_API_BASE"),
            env.get("BASE_URL"),
            skill_env.get("GROK_API_BASE"),
            skill_env.get("BASE_URL"),
            DEFAULT_BASE,
        )
    return ""


def sort_registry(
    registry: list[dict[str, Any]],
    env: dict[str, str],
    skill_env: dict[str, str],
) -> list[dict[str, Any]]:
    """Apply optional X_SEARCH_PRIORITY override, else sort by priority asc."""
    order = parse_csv_list(
        first_nonempty(
            env.get("X_SEARCH_PRIORITY"),
            skill_env.get("X_SEARCH_PRIORITY"),
            env.get("X_SEARCH_CHANNELS"),
            skill_env.get("X_SEARCH_CHANNELS"),
        )
    )
    if order:
        rank = {name: idx for idx, name in enumerate(order)}
        selected = [item for item in registry if item["id"] in rank]
        selected.sort(key=lambda item: rank[item["id"]])
        # Keep unspecified registry items after ordered ones, by priority.
        rest = [item for item in registry if item["id"] not in rank]
        rest.sort(key=lambda item: (item["priority"], item["id"]))
        return selected + rest
    return sorted(registry, key=lambda item: (item["priority"], item["id"]))


def materialize_channel(
    item: dict[str, Any],
    env: dict[str, str],
    skill_env: dict[str, str],
    cli_model: str = "",
    cli_base: str = "",
    cli_key: str = "",
    require_enabled: bool = True,
) -> dict[str, Any] | None:
    channel_id = str(item["id"])
    if require_enabled and not item.get("enabled", True):
        return None

    base = resolve_base(channel_id, str(item.get("base") or ""), env, skill_env, cli_base)
    key = resolve_key(as_str_list(item.get("key_env")), env, skill_env, cli_key)
    models = as_str_list(item.get("models"))
    if cli_model:
        models = build_model_chain(cli_model, [])
    if not models:
        models = build_model_chain(DEFAULT_MODEL, DEFAULT_FALLBACK_MODELS)

    if not key:
        eprint(f"Skip channel '{channel_id}': missing API key")
        return None
    if not base:
        eprint(f"Skip channel '{channel_id}': missing base URL")
        return None

    return {
        "name": channel_id,
        "priority": int(item.get("priority", 100)),
        "base": normalize_base(base),
        "key": key,
        "models": models,
    }


def load_legacy_channel(
    env: dict[str, str],
    skill_env: dict[str, str],
    cli_base: str,
    cli_key: str,
    cli_model: str,
) -> dict[str, Any]:
    base = first_nonempty(
        cli_base,
        env.get("GROK_API_BASE"),
        env.get("BASE_URL"),
        env.get("XAI_BASE_URL"),
        skill_env.get("GROK_API_BASE"),
        skill_env.get("BASE_URL"),
        skill_env.get("XAI_BASE_URL"),
        DEFAULT_BASE,
    )
    key = first_nonempty(
        cli_key,
        skill_env.get("GROK_API_KEY"),
        skill_env.get("API_KEY"),
        skill_env.get("XAI_API_KEY"),
        env.get("GROK_API_KEY"),
        env.get("API_KEY"),
        env.get("XAI_API_KEY"),
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
    models = build_model_chain(model, parse_csv_list(fallback_raw))
    return {
        "name": "default",
        "priority": 1,
        "base": normalize_base(base),
        "key": key,
        "models": models,
    }


def load_named_channel(
    name: str,
    env: dict[str, str],
    skill_env: dict[str, str],
    default_models: list[str],
) -> dict[str, Any] | None:
    base = first_nonempty(
        lookup_merged(env, skill_env, channel_env_key(name, "BASE")),
        lookup_merged(env, skill_env, channel_env_key(name, "BASE_URL")),
    )
    key = first_nonempty(
        lookup_merged(env, skill_env, channel_env_key(name, "KEY")),
        lookup_merged(env, skill_env, channel_env_key(name, "API_KEY")),
    )
    models_raw = first_nonempty(
        lookup_merged(env, skill_env, channel_env_key(name, "MODELS")),
        lookup_merged(env, skill_env, channel_env_key(name, "MODEL")),
    )
    models = parse_csv_list(models_raw) or list(default_models)
    if not base or not key:
        eprint(f"Skip channel '{name}': missing BASE or KEY")
        return None
    return {
        "name": name,
        "priority": 100,
        "base": normalize_base(base),
        "key": key,
        "models": models or [DEFAULT_MODEL],
    }


def describe_channels(force_channel: str = "") -> int:
    """Print channel registry status without secrets."""
    env = dict(os.environ)
    skill_env = load_dotenv(SKILL_DIR / ".env")
    registry = load_channel_registry()
    if not registry:
        print("No channels.json found.")
        return 1

    ordered = sort_registry(registry, env, skill_env)
    print(f"registry={CHANNELS_PATH}")
    print("priority order (left = higher):")
    print("  " + " > ".join(item["id"] for item in ordered if item.get("enabled", True)))
    print()
    for rank, item in enumerate(ordered, start=1):
        channel_id = item["id"]
        if force_channel and channel_id != force_channel:
            continue
        key = resolve_key(as_str_list(item.get("key_env")), env, skill_env)
        base = resolve_base(channel_id, str(item.get("base") or ""), env, skill_env)
        status = "ready" if item.get("enabled", True) and key and base else "not-ready"
        if not item.get("enabled", True):
            status = "disabled"
        elif not key:
            status = "missing-key"
        elif not base:
            status = "missing-base"
        print(
            f"#{rank} id={channel_id} priority={item.get('priority')} "
            f"enabled={bool(item.get('enabled', True))} status={status}"
        )
        print(f"    base={base or '-'}")
        print(f"    models={','.join(as_str_list(item.get('models')) or DEFAULT_FALLBACK_MODELS)}")
        print(f"    key_env={','.join(as_str_list(item.get('key_env')))} key_set={'yes' if key else 'no'}")
    return 0


def load_config(
    cli_base: str,
    cli_key: str,
    cli_model: str,
    cli_timeout: int,
    force_channel: str = "",
) -> dict[str, Any]:
    env = dict(os.environ)
    skill_env = load_dotenv(SKILL_DIR / ".env")

    timeout_raw = first_nonempty(
        str(cli_timeout) if cli_timeout else "",
        env.get("GROK_TIMEOUT_SECONDS"),
        skill_env.get("GROK_TIMEOUT_SECONDS"),
        str(DEFAULT_TIMEOUT),
    )
    try:
        timeout = int(timeout_raw)
    except ValueError:
        timeout = DEFAULT_TIMEOUT

    transient_raw = first_nonempty(
        env.get("X_SEARCH_TRANSIENT_RETRIES"),
        skill_env.get("X_SEARCH_TRANSIENT_RETRIES"),
        str(DEFAULT_TRANSIENT_RETRIES),
    )
    try:
        transient_retries = max(0, int(transient_raw))
    except ValueError:
        transient_retries = DEFAULT_TRANSIENT_RETRIES

    # Explicit CLI base/key forces single-channel debug mode.
    if cli_base or cli_key:
        channel = load_legacy_channel(env, skill_env, cli_base, cli_key, cli_model)
        if not channel["key"]:
            raise SystemExit(
                "Missing API key. Pass --api-key or set channel key in skill .env"
            )
        channel["name"] = force_channel or channel["name"]
        return {
            "channels": [channel],
            "timeout": timeout,
            "transient_retries": transient_retries,
        }

    registry = load_channel_registry()
    channels: list[dict[str, Any]] = []

    if registry:
        ordered = sort_registry(registry, env, skill_env)
        if force_channel:
            ordered = [item for item in ordered if item["id"] == force_channel]
            if not ordered:
                known = ", ".join(item["id"] for item in registry)
                raise SystemExit(
                    f"Unknown channel '{force_channel}'. Known: {known}"
                )
        for item in ordered:
            # force_channel may target a disabled slot for explicit testing
            channel = materialize_channel(
                item,
                env,
                skill_env,
                cli_model=cli_model,
                require_enabled=not bool(force_channel),
            )
            if channel:
                channels.append(channel)
    else:
        # Fallback path without channels.json
        names = parse_csv_list(
            first_nonempty(
                env.get("X_SEARCH_CHANNELS"),
                skill_env.get("X_SEARCH_CHANNELS"),
            )
        )
        default_models = build_model_chain(
            first_nonempty(
                cli_model,
                env.get("GROK_MODEL"),
                env.get("MODEL"),
                skill_env.get("GROK_MODEL"),
                skill_env.get("MODEL"),
                DEFAULT_MODEL,
            ),
            parse_csv_list(
                first_nonempty(
                    env.get("GROK_FALLBACK_MODELS"),
                    skill_env.get("GROK_FALLBACK_MODELS"),
                    ",".join(DEFAULT_FALLBACK_MODELS),
                )
            ),
        )
        if names:
            for name in names:
                channel = load_named_channel(name, env, skill_env, default_models)
                if channel:
                    if cli_model:
                        channel["models"] = build_model_chain(cli_model, [])
                    channels.append(channel)
        else:
            channel = load_legacy_channel(env, skill_env, "", "", cli_model)
            if channel["key"]:
                channels.append(channel)

    if not channels:
        raise SystemExit(
            "No usable channels. Edit channels.json (enabled/priority/base) "
            "and set keys in .env, or use legacy GROK_API_KEY."
        )

    return {
        "channels": channels,
        "timeout": timeout,
        "transient_retries": transient_retries,
    }


def body_text(body: Any) -> str:
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            return " ".join(
                str(err.get(k) or "")
                for k in ("message", "type", "code", "param")
            )
        return json.dumps(body, ensure_ascii=False)
    return str(body or "")


def is_auth_error(result: dict[str, Any]) -> bool:
    return result.get("status") in (401, 403)


def is_bad_request(result: dict[str, Any]) -> bool:
    return result.get("status") == 400


def is_model_or_channel_error(result: dict[str, Any]) -> bool:
    """Return True when retrying another model/channel is likely useful."""
    status = result.get("status")
    text = body_text(result.get("body"))
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
    if status in (404, 503) and ("model" in lowered or "channel" in lowered or "渠道" in text):
        return True
    return False


def is_transient_error(result: dict[str, Any]) -> bool:
    status = result.get("status")
    if status in (408, 429, 500, 502, 503, 504):
        return True
    text = body_text(result.get("body")).lower()
    markers = [
        "timeout",
        "timed out",
        "ssl",
        "connection reset",
        "connection aborted",
        "temporarily unavailable",
        "try again",
        "rate limit",
        "too many requests",
        "eof occurred",
        "remote end closed",
    ]
    return any(m in text for m in markers)


def should_try_next_model_or_channel(result: dict[str, Any]) -> bool:
    if is_auth_error(result) or is_bad_request(result):
        return False
    return (
        is_model_or_channel_error(result)
        or is_transient_error(result)
        or result.get("status") in (404, 408, 429, 500, 502, 503, 504)
        or result.get("status") is None
    )


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


def request_responses(
    base: str,
    key: str,
    model: str,
    timeout: int,
    prompt: str,
    max_tool_calls: int,
) -> dict[str, Any]:
    url = base.rstrip("/") + "/responses"
    payload = {
        "model": model,
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
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "x-search-grok-skill/1.1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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


def run_with_failover(
    cfg: dict[str, Any],
    prompt: str,
    max_tool_calls: int,
) -> tuple[dict[str, Any], str, str, list[dict[str, Any]]]:
    """Try channels -> models -> transient retries. Return result + metadata."""
    attempts: list[dict[str, Any]] = []
    last_result: dict[str, Any] = {
        "ok": False,
        "status": None,
        "body": "No channel/model attempts were made.",
    }
    used_channel = ""
    used_model = ""
    transient_retries = int(cfg.get("transient_retries") or 0)
    timeout = int(cfg["timeout"])

    for channel in cfg["channels"]:
        channel_name = str(channel["name"])
        for model_name in channel["models"]:
            model_name = str(model_name)
            move_to_next_channel = False
            stop_all = False

            for attempt_idx in range(transient_retries + 1):
                one = request_responses(
                    channel["base"],
                    channel["key"],
                    model_name,
                    timeout,
                    prompt,
                    max_tool_calls,
                )
                last_result = one
                used_channel = channel_name
                used_model = model_name
                attempts.append(
                    {
                        "channel": channel_name,
                        "model": model_name,
                        "attempt": attempt_idx + 1,
                        "ok": one.get("ok"),
                        "status": one.get("status"),
                    }
                )

                if one.get("ok"):
                    if len(attempts) > 1:
                        eprint(
                            f"Succeeded via channel={channel_name} model={model_name}"
                        )
                    return one, channel_name, model_name, attempts

                if is_auth_error(one):
                    eprint(
                        f"Channel {channel_name} auth failed "
                        f"(status={one.get('status')}); skipping channel"
                    )
                    move_to_next_channel = True
                    break

                if is_bad_request(one):
                    eprint(
                        f"Bad request on channel={channel_name} model={model_name}; stop"
                    )
                    return one, channel_name, model_name, attempts

                if is_transient_error(one) and attempt_idx < transient_retries:
                    eprint(
                        f"Transient error channel={channel_name} model={model_name} "
                        f"status={one.get('status')}; retrying once"
                    )
                    time.sleep(DEFAULT_RETRY_SLEEP_SECONDS)
                    continue

                if should_try_next_model_or_channel(one):
                    eprint(
                        f"channel={channel_name} model={model_name} failed "
                        f"(status={one.get('status')}); trying next"
                    )
                    break

                eprint(
                    f"Non-retriable error on channel={channel_name} "
                    f"model={model_name}; stop"
                )
                stop_all = True
                break

            if stop_all:
                return last_result, used_channel, used_model, attempts
            if move_to_next_channel:
                break

    return last_result, used_channel, used_model, attempts


def main() -> int:
    parser = argparse.ArgumentParser(description="V1 X search via Grok-compatible x_search")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["keyword", "account", "heat"],
        help="V1 mode",
    )
    parser.add_argument("query", nargs="?", help="Search query or account handle")
    parser.add_argument("--limit", type=int, default=8, help="Max items to request")
    parser.add_argument("--since", default="7d", help="Recency window, e.g. 1d/3d/7d")
    parser.add_argument("--lang", default="zh", help="zh or en")
    parser.add_argument("--base-url", default="", help="Override API base URL (single-channel mode)")
    parser.add_argument("--api-key", default="", help="Override API key (single-channel mode)")
    parser.add_argument("--model", default="", help="Override model")
    parser.add_argument("--timeout", type=int, default=0, help="Timeout seconds")
    parser.add_argument(
        "--channel",
        default="",
        help="Force one channel id from channels.json (skip others)",
    )
    parser.add_argument(
        "--list-channels",
        action="store_true",
        help="Show channel registry, priority order, and readiness",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--raw", action="store_true", help="Include raw response body in JSON mode")
    args = parser.parse_args()

    if args.list_channels:
        return describe_channels(force_channel=args.channel.strip())

    if not args.mode or not args.query:
        parser.error("mode and query are required unless --list-channels is set")

    if args.limit < 1:
        args.limit = 1
    if args.limit > 20:
        args.limit = 20

    cfg = load_config(
        args.base_url,
        args.api_key,
        args.model,
        args.timeout,
        force_channel=args.channel.strip(),
    )
    prompt = build_prompt(args.mode, args.query, args.limit, args.since, args.lang)
    started = datetime.now(timezone.utc)

    result, used_channel, used_model, attempts = run_with_failover(
        cfg, prompt, mode_tool_budget(args.mode)
    )
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()

    channels_tried: list[str] = []
    models_tried: list[str] = []
    for item in attempts:
        channel_name = str(item.get("channel") or "")
        model_name = str(item.get("model") or "")
        if channel_name and channel_name not in channels_tried:
            channels_tried.append(channel_name)
        label = f"{channel_name}:{model_name}"
        if label not in models_tried:
            models_tried.append(label)

    fell_back = bool(attempts) and not (
        attempts[0].get("channel") == used_channel
        and attempts[0].get("model") == used_model
        and attempts[0].get("ok")
    )

    if not result.get("ok"):
        payload = {
            "ok": False,
            "mode": args.mode,
            "query": args.query,
            "status": result.get("status"),
            "elapsed_seconds": round(elapsed, 2),
            "channel": used_channel,
            "model": used_model,
            "channels_tried": channels_tried,
            "models_tried": models_tried,
            "attempts": attempts,
            "error": result.get("body"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            eprint("X search failed.")
            eprint(
                f"status={result.get('status')} channel={used_channel} "
                f"model={used_model} tried={','.join(models_tried)}"
            )
            body = result.get("body")
            print(
                json.dumps(body, ensure_ascii=False, indent=2)
                if isinstance(body, (dict, list))
                else body
            )
        return 2

    body = result.get("body")
    text = extract_text(body if isinstance(body, dict) else {})
    stats = extract_tool_stats(body if isinstance(body, dict) else {})

    if args.json:
        payload = {
            "ok": True,
            "mode": args.mode,
            "query": args.query,
            "status": result.get("status"),
            "elapsed_seconds": round(elapsed, 2),
            "channel": used_channel,
            "model": used_model,
            "fell_back": fell_back,
            "channels_tried": channels_tried,
            "models_tried": models_tried,
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
            f"channel={used_channel}",
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
