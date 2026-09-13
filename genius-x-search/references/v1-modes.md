# V1 Modes

This skill only supports three modes.

## keyword

Use when the user wants posts about a topic.

Examples:
- Search X for Grok 4.5
- What are people saying about Claude Code on X?
- Find recent posts about OpenClaw

Command:

```bash
python scripts/x_search.py keyword "Grok 4.5" --limit 8 --since 3d
```

## account

Use when the user wants one account's recent activity.

Examples:
- What did Elon post recently?
- Check @realDonaldTrump latest posts
- Summarize @OpenAI recent posts

Command:

```bash
python scripts/x_search.py account elonmusk --limit 8 --since 7d
```

## heat

Use when the user wants heat, sentiment, and representative discussion.

Examples:
- How hot is Grok 4.5 discussion?
- Sentiment around Grok 4.5 on X
- Brief me on the X reaction to ...

Command:

```bash
python scripts/x_search.py heat "Grok 4.5" --limit 10 --since 3d --lang zh
```

## Non-goals

Do not expand V1 into:
- posting / liking / following
- watchlists
- full-archive historical research systems
- multi-backend routing beyond the configured Grok-compatible relay
