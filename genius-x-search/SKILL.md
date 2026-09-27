---
name: genius-x-search
description: "基于 Grok 代理的 X/Twitter 实时搜索与情报分析：关键词检索、特定账号动态跟踪、全网讨论热度与舆情简报。不要用于发帖点赞等社交互动，或与 X 无关的通用网页搜索。"
metadata:
  version: "2.0.0"
---

# Genius X Search

Real-time X research through a Grok-compatible `POST {base}/responses` relay with `tools: [{"type": "x_search"}]`. Three modes only: **keyword**, **account**, **heat**.

## When To Use

Use for: "search X for …", "what did @handle post recently", X heat/sentiment on a topic, a short sourced briefing from X.

Do not use for: posting, liking, following, DMs, or account management; web research with no X intent; watchlists or full-archive search.

## Setup

- `channels.json` — channel registry: `id`, `priority`, `enabled`, `base`, `models` (tried in order), `key_env`. Default: `cpa-jp` with `grok-4.20-0309-non-reasoning` → `grok-3-mini-fast`.
- `.env` (skill-local, from `.env.example`) — the key named in `key_env`, e.g. `CHANNEL_CPA_JP_KEY`. Environment variables override `.env`. Never print the key.
- Check readiness: `python scripts/x_search.py --list-channels`

## Modes

```bash
python scripts/x_search.py keyword "Grok 4.5 coding agents" --since 3d --limit 8
python scripts/x_search.py account elonmusk --since 7d --limit 8
python scripts/x_search.py heat "Grok 4.5" --since 3d --limit 10 --lang zh
```

Options: `--since 1h|3h|12h|1d|3d|7d|30d` (default `7d`), `--limit 1-20` (default 8), `--lang zh|en`, `--json`, `--model <id>`, `--channel <id>`, `--timeout <s>` (default 90).

Query tips: exact product/version names first, then 1–2 aliases. Handles work with or without `@`. For heat, reaction words help (`love OR hate OR disappointed OR benchmark`). Prefer short windows unless the user asks broader.

## Workflow

1. Pick exactly one mode and build a tight query.
2. Run `scripts/x_search.py`. Use its output, not model memory.
3. Answer concisely with sources.
4. If the script fails (exit code 2), report the error plainly. Do not swap in unrelated queries or invent posts.

Run at most 2–3 searches in parallel; the relay times out or throws SSL errors beyond that. A single call is the most reliable.

## Failover

Channel by priority → model chain inside it. 429/5xx/connection resets get one retry on the same model; timeouts, empty 200 answers, and `model_not_found` go straight to the next model; 401/403 skip the channel; any other 400/422 stops.

## Evidence Rules

Keep original post content, search summaries, and your own inference distinct. Link posts directly whenever possible. Heat and sentiment conclusions state the time window and sample size, and say so when the sample is thin. Merge duplicates of the same post or event; prefer originals.

## Output Contract

Concise Chinese unless the user asks otherwise.

- **keyword** — `## 检索结果`: one-line overview, then 5–10 posts with author, time, and link.
- **account** — `## @handle 最近动态`: posting frequency/themes in one line, then 3–8 posts with links.
- **heat** — `## 热度简报`: 热度判断, 情绪判断, 代表性讨论 (with links), 主要好评, 主要争议/差评.

If nothing useful is found, say so.

## Resources

- `scripts/x_search.py` — relay caller with failover
- `channels.json` — channel registry
- `.env.example` — secrets template
- `evals/evals.json` — trigger / non-trigger checks

## Gotchas

- `chat/completions` does not do X search; only `/responses` with `x_search` works.
- The relay does not strictly enforce `max_tool_calls`; heat mode may make 6–7 X searches and take ~15 s.
- Do not run more than 3 X searches in parallel.
