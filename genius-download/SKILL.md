---
name: genius-download
description: "Genius 视频下载：把视频链接下载成本地 mp4，支持 B 站、抖音、小红书、YouTube 以及其他 yt-dlp 能下的网站；整段分享文案（「复制打开抖音… https://v.douyin.com/… 复制此链接」）可以直接当输入，多条链接并行，已下过的不重复下。用户说「把这个视频下下来」「这几个抖音链接帮我下载」「下载这条小红书笔记的视频」「把 B 站这个视频存到本地」「先把这些链接的视频都下好」时使用。不要用于分析或总结视频内容（用 genius-omni），不要用于给视频做素材说明书或拉片（用 genius-footage，它收到链接会自己调用本 skill），不要用于语音转文字（用 genius-voice），不要用于网盘上传下载（用 quarkclouddrive），也不要用于抓取网页文字（用 firecrawl）。"
metadata:
  version: "1.0.0"
---

# Genius Download（视频下载）

This skill exists to **turn video links into local mp4 files**. Nothing else: no analysis, no transcoding, no audio extraction.

## Run

```bash
python3 "<skill_dir>/scripts/download.py" --check
python3 "<skill_dir>/scripts/download.py" <link|share message> [<link> …] [--dir DIR] [--jobs 4] [--cookies-from-browser chrome] [--output text|json]
```

`<skill_dir>` is this skill folder; on Windows use `python`. Stdlib only. Needs `yt-dlp` for B 站, YouTube and other sites; 抖音 / 小红书 also work without it through RedFox or the ego browser.

- Pass every link to one command; they download `--jobs` (default 4) at a time. A whole share message is one argument: quote it.
- Files go to `--dir` (default `~/Downloads/genius-download/`), named `<title ≤60 bytes> [<id>].mp4`; a link already there is not downloaded again.
- B 站 and other sites: `yt-dlp` (≤1080p); add `--cookies-from-browser chrome` when the site needs a login. Without `yt-dlp` those links fail with `DEPENDENCY_MISSING`: ask before installing it (`brew install yt-dlp`).
- 抖音 / 小红书: RedFox first, a paid API (about ¥0.03 a call; the link leaves this machine). Its key lives in `scripts/.env` as `REDFOX_API_KEY`: the user writes it, never ask for it in chat. Without it, or when it fails, the script falls back by itself to yt-dlp (小红书) and the logged-in ego browser.
- A 小红书 link must carry `xsec_token` (copied from search results or the share button); without it the site shows nothing and the script refuses.

Routes per site, measurements and why the simpler routes do not work: `references/routes.md`.

## Report

Each saved path as printed (`已下载：…`), and every failure as `Error [CODE]: …`. `--output json` prints a list of `{"input", "path"}` or `{"input", "error": {"code", "message"}}`. One link failing does not stop the others; the exit code is the first failure's: `INPUT_NOT_FOUND` 3 (no link in the text), `UNSUPPORTED_FORMAT` 4, `DEPENDENCY_MISSING` 5, `PROVIDER_ERROR` 6, `TIMEOUT` 7. Report the code and message as-is.

## Gotchas

- A login or verification wall in the ego browser fails with a hint: ask the user to log in to that site in ego, then rerun.
- 抖音 in a fresh browser tab can land on a different video; the script checks the video ID it landed on and fails instead of saving the wrong one.
- Files downloaded before genius-download 1.0.0 sit in `~/Downloads/genius-footage/`; they are not found again, so a link is downloaded once more unless `--dir` points there.

## Resource Map

- `scripts/download.py`: links → local mp4 (RedFox, yt-dlp, ego browser), several at once; `--check`.
- `references/routes.md`: routes per site, measurements, the RedFox API, and why yt-dlp or a fresh browser tab alone do not work.
- `evals/evals.json`, `agents/openai.yaml`.
