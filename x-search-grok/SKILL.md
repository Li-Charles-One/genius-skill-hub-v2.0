---
name: x-search-grok
description: >
  Search X/Twitter in real time through a Grok-compatible relay using the
  server-side x_search tool. Use when the user asks to search X/Twitter, check
  what someone posted recently, review discussion heat or sentiment on X, or
  produce a sourced X briefing. Supports only three V1 modes: keyword search,
  account updates, and heat/sentiment briefing. Not for posting, liking,
  following, DMs, or web-only research without an X focus.
---

# X Search Grok

Real-time X research via a Grok-compatible `/v1/responses` endpoint with
`tools: [{ "type": "x_search" }]`.

This skill is intentionally V1-only:

1. **keyword** — search X by query
2. **account** — recent posts from a handle
3. **heat** — discussion heat, sentiment, and representative posts

## Requirements

Read config in this order:

1. Environment variables
2. Skill-local `.env`
3. Workspace fallbacks:
   - `probe_key.txt` / `probe_env.txt`
   - `.probe_runtime_key` / `.probe_runtime_env`

Supported variables:

- `GROK_API_BASE` or `BASE_URL` — e.g. `https://ai.0xs.one/v1`
- `GROK_API_KEY` or `API_KEY` or `XAI_API_KEY`
- `GROK_MODEL` or `MODEL` — default `grok-4.5`
- `GROK_FALLBACK_MODELS` — comma-separated backups, default `grok-4.3`
- `GROK_TIMEOUT_SECONDS` — default `180`

Model selection:

- Primary model is `GROK_MODEL` (default `grok-4.5`)
- If the primary model/channel is unavailable, automatically try
  `GROK_FALLBACK_MODELS` in order (default includes `grok-4.3`)
- CLI `--model` still forces a single model and skips the default primary,
  but fallbacks still apply unless you only want one model listed

Never print the API key.

## When To Use

Use this skill when the user wants:

- "search X for ..."
- "what did @handle post recently"
- "X discussion / heat / sentiment about ..."
- a short sourced briefing from X

Do **not** use it for:

- posting or account management
- pure web research with no X intent
- long-term watchlists, archival search, or engagement automation

## Modes

### 1) keyword

Goal: find recent relevant posts for a topic.

```bash
python scripts/x_search.py keyword "Grok 4.5 coding agents" --limit 8
```

Useful options:

- `--since 1d|3d|7d`
- `--limit 5-12`
- `--lang zh|en`
- `--json`

### 2) account

Goal: summarize what one account posted recently.

```bash
python scripts/x_search.py account elonmusk --limit 8
python scripts/x_search.py account @realDonaldTrump --since 7d
```

Handle may be with or without `@`.

### 3) heat

Goal: produce a sourced heat/sentiment briefing.

```bash
python scripts/x_search.py heat "Grok 4.5" --limit 10 --lang zh
```

Heat mode should return:

- overall heat
- sentiment split
- 4-8 representative posts with links
- main praise points and main complaints

## Agent Workflow

1. Choose exactly one V1 mode.
2. Build a tight query.
3. Run `scripts/x_search.py`.
4. Prefer script output over freeform model memory.
5. Return a concise sourced answer.
6. If the script fails, report the error plainly. Do not invent posts.

### Query tips

- Keyword: exact product/version names first, then 1-2 aliases
- Account: always use `from:handle`
- Heat: include product name + reaction words when useful
  (`love OR hate OR impressed OR disappointed OR benchmark`)
- Prefer recent windows (`1d`, `3d`, `7d`) unless user asks broader

## Output Contract

Default to concise Chinese unless the user asks for another language.

### keyword

```text
## 检索结果
- 一句话总览
- 5-10 条要点，每条尽量带作者、时间和链接
```

### account

```text
## @handle 最近动态
- 更新频率/主题一句话
- 3-8 条最近帖子要点 + 链接
```

### heat

```text
## 热度简报
- 热度判断
- 情绪判断
- 代表性讨论（带链接）
- 主要好评
- 主要争议/差评
```

If no useful posts are found, say so explicitly.

## Notes

- The reliable path is `POST {BASE}/responses` with `x_search`.
- Do not rely on `chat/completions` for X search.
- This skill does not implement posting, watchlists, or full-archive search.

## Resources

- `references/v1-modes.md` — mode selection examples and non-goals
- `evals/evals.json` — trigger / non-trigger checks
- `scripts/x_search.py` — deterministic relay caller
- `.env.example` — config template
