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

### Channel interface (swappable)

Control plane: `channels.json`  
Secrets: skill-local `.env`

Built-in slot:

| id | priority | role | key env |
|---|---|---|---|
| `cpa` | 1 | `cpa.charles-ai.space` Grok relay | `CHANNEL_CPA_KEY` / `CPA_API_KEY` / `GROK_API_KEY` |

Default model: `grok-4.5` (via `cpa.charles-ai.space`).

**Swap / extend without code changes:**

1. Edit `channels.json` (`base` / `models` / add more channels)
2. Or set env override: `X_SEARCH_PRIORITY=cpa`
3. Put keys only in `.env` (`CHANNEL_CPA_KEY`)

```bash
# inspect registry
python scripts/x_search.py --list-channels

# force CPA
python scripts/x_search.py keyword "Grok 4.5" --channel cpa
```

Config precedence:

1. CLI (`--api-key` / `--base-url` / `--model` / `--channel`)
2. `channels.json` + `.env` keys
3. Optional `X_SEARCH_PRIORITY` order override
4. Legacy `GROK_API_*` (points at CPA)

Failover order:

1. channel by priority
2. model chain inside that channel
3. one transient retry on timeout / SSL / 429 / 5xx

Error policy:

- `401/403` → skip current channel, try next provider
- `400` → stop (bad request, not a channel issue)
- model/channel unavailable, timeout, SSL, 429/5xx → next model, then next channel

### Supported variables

| 变量 | 作用 | 读取来源 |
|---|---|---|
| `channels.json` | 渠道注册表：id / priority / enabled / base / models | 文件 |
| `X_SEARCH_PRIORITY` | 临时改优先级顺序 | 环境变量 → `.env` |
| `CHANNEL_CPA_KEY` / `CPA_API_KEY` | CPA API Key | `.env` |
| `CHANNEL_<ID>_BASE` | 可选覆盖 base | 环境变量 → `.env` |
| `X_SEARCH_TRANSIENT_RETRIES` | 瞬时错误重试次数（默认 1） | 环境变量 → `.env` |
| `GROK_API_KEY` | 兼容别名（同 CPA key） | CLI / `.env` |
| `GROK_TIMEOUT_SECONDS` | 超时秒数 | 环境变量 → `.env` |

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
7. **并发控制**：一次最多并行跑 2-3 个搜索任务。复杂搜索（需多方对比、多角度信息）跑 3 个；
   简单搜索（查一个账号、一个关键词）跑 1-2 个。并发过多会导致 SSL 报错或超时。
   若脚本报错，不得换用无关查询蒙混过关，必须如实报错。

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
- **渠道**：默认仅自建 CPA；可用 `channels.json` 再加备用。瞬时错误会同模型重试 1 次，再换 model / 下一渠道。
- **并发限制**：该 API 端并发能力有限。2 个并发可能导致部分请求 SSL 报错，
  4 个并发几乎必超时。单次调用稳定。任何时候并行搜索不得超过 3 个。

## Resources

- `references/v1-modes.md` — mode selection examples and non-goals
- `evals/evals.json` — trigger / non-trigger checks
- `scripts/x_search.py` — deterministic relay caller
- `channels.json` — channel registry (default: cpa)
- `.env.example` — secrets template
