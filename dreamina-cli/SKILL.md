---
name: dreamina-cli
description: Use when an agent needs Dreamina（即梦） login, sessions, task history, or image/video generation through the dreamina CLI. Do not use for CPA/gpt-image generation or Seedance shotlists.
---

# Dreamina CLI

Use this skill when you need Dreamina（即梦） image or video generation, login, session management, or task history work through `dreamina`.

即梦 is the Chinese product name of Dreamina. If the user says 即梦, treat it as Dreamina and use this skill.

This skill is intentionally short. Detailed flags and supported values belong to the CLI itself, so always treat `dreamina -h` and `dreamina <subcommand> -h` as the primary reference. Model lists, resolution limits, and duration ranges change over time — never hardcode them from memory.

## Install / update CLI

```bash
curl -fsSL https://jimeng.jianying.com/cli | bash
dreamina version
```

Typical install path: `~/.local/bin/dreamina` (ensure that directory is on `PATH`).

## What this tool is for

`dreamina` is the local CLI entrypoint for currently exposed Dreamina（即梦） image/video workflows, plus account/session operations.

Use it for:

- checking or reusing an existing Dreamina login session
- checking account credit (`user_credit`)
- managing sessions with `dreamina session`
- clearing local OAuth state with `dreamina logout`
- submitting image generation / edit / upscale tasks
- submitting video generation tasks (including Seedance family, e.g. 2.0 / 2.5)
- querying async task results and downloading media
- reviewing saved task history

## Default workflow

When using this CLI as an agent:

1. **Preflight:** run `dreamina -h` (and optionally `dreamina version`). If `command not found`, install/update with `curl -fsSL https://jimeng.jianying.com/cli | bash`, then re-check. Do not invent flags.
2. Before any real command, run `dreamina <subcommand> -h` and follow **that** help for required flags and model constraints.
3. Reuse current login unless the user asks to `login`, `relogin`, `logout`, or finish headless login with `checklogin`.
4. Login uses OAuth Device Flow and prints `verification_uri`, `user_code`, and `device_code`.
5. Default login waits for authorization. With `--headless`, print material and exit; finish later with `dreamina login checklogin --device_code=<device_code>` (optional `--poll=N`).
6. Be explicit whether you are only reading help, submitting a paid task, or querying an existing `submit_id`.
7. Warn before commands that consume credits.
8. Prefer `--poll=N` on generators for a short wait; if still `querying`, continue with `query_result`.

## Login completion: mandatory user-visible confirmation

`dreamina login` / `dreamina relogin` prints OAuth Device Flow instructions and then waits (unless headless). When the command finishes, tell the user explicitly that login succeeded, state was reused, or it failed.

- **Do not** wait for the user to ask “登录好了吗”.
- **Do not** stop after only sending the device code: keep the login command running, read stdout to the end, then confirm.
- **Failure** must include the concrete error and next step.

## Choosing the right command

At a high level:

| Need | Command |
|---|---|
| Budget | `user_credit` |
| Sessions | `session` create/list/search/rename/delete (`--session=<id>`; `0` is default) |
| Query one task | `query_result --submit_id=<id>` (+ `--download_dir` to save media) |
| List tasks | `list_task` (filter by status / type / submit_id) |
| Text → image | `text2image` |
| Image edit | `image2image` |
| Upscale | `image_upscale` |
| Text → video | `text2video` |
| One image → video | `image2video` |
| First+last frame video | `frames2video` |
| Multi-image story video | `multiframe2video` (fixed model; no model picker) |
| Flagship multimodal / 全能参考 | `multimodal2video` (images/video/audio; Seedance family incl. 2.5). Legacy name `ref2video` → trust current `dreamina -h` |

Exact flags always come from each subcommand’s `-h`.

## Critical CLI rules (current generation surface)

These are easy to miss and currently enforced strictly by the CLI:

1. **`--resolution_type` is required** on common image commands (`text2image`, `image2image`, `image_upscale`) and must match the model’s allowed set.
2. **`--video_resolution` is required** on current video generators (`text2video`, `image2video`, `frames2video`, `multiframe2video`, `multimodal2video`).
3. Image commands support **custom `--width` + `--height` together**, mutually exclusive with `--ratio`; still require `--resolution_type`. Final pixels may be backend-aligned — trust `query_result`.
4. Generators accept **`--poll=N`**: submit then poll up to N seconds (1s interval). `0` disables polling.
5. Defaults (when help says so) may include e.g. image `model_version=5.0`, video `seedance2.0fast` / `seedance2.0_vip` depending on command — **do not override defaults unless the user asked**.
6. **Seedance 2.5** (`seedance2.5`) appears on video commands as a VIP-oriented option with different resolution/duration limits than 2.0 family. Confirm on `-h` before use.
7. Unsupported/legacy values are **rejected**, not silently rewritten.
8. Runtime availability and queues can change even if a model is listed in help.

## Model selection rule

Do not hardcode model support from this skill.

```bash
dreamina <subcommand> -h
```

Confirm:

- whether the command exposes `--model_version`
- whether the requested model is listed
- constraints: duration, ratio, resolution, VIP, input counts

Additional guidance:

- some commands have **no** model selection (`multiframe2video`)
- if the user does not specify a model, keep the subcommand default
- if they care about speed vs quality, pick only when help makes the trade-off clear; do not force Seedance 2.0/2.5 unless asked or quality is the priority
- capacity-constrained / VIP models: set expectations before spending credits

## How to judge submit acceptance vs terminal success

Do **not** rely on shell exit code alone.

| Signal | Meaning |
|---|---|
| `submit_id` present + `gen_status=querying` | **Accepted only** — not finished |
| `gen_status=success` | Terminal success |
| `gen_status=fail` | Terminal failure — report `fail_reason` verbatim |

After `--poll=N`, if still `querying`:

1. Save `submit_id` (e.g. `.dreamina_tasks.txt`: `<timestamp> <command> <submit_id>`)
2. Continue with `query_result --submit_id=<id>` (+ `--download_dir` when needed)
3. Use `list_task` for bulk review

Before re-submitting a paid task, check saved IDs so you do not double-spend.

## Follow-up pattern for async tasks

1. Prefer generator `--poll=N` for a short wait.
2. Persist `submit_id` before long polling or context switches.
3. Finish with `query_result` until `success` or `fail`.
4. For test sweeps, keep machine-readable logs of command, args, `submit_id`, status.

## Common failure handling

| Error / symptom | Action |
|:--|:--|
| `dreamina: command not found` | Install/update: `curl -fsSL https://jimeng.jianying.com/cli \| bash`; ensure `~/.local/bin` on PATH |
| Missing required `--resolution_type` / `--video_resolution` | Re-read `-h`; add the required flag (current CLI rejects omit on many commands) |
| `AigcComplianceConfirmationRequired` | User must complete first-time model use / authorization on Dreamina Web, then retry once |
| Network timeout / connection error | Wait 10–30s, retry once; if fails again, report and stop |
| Rate limit / quota exceeded | Report exact message; do not auto-retry |
| `gen_status: fail` + `fail_reason` | Report `fail_reason` verbatim; do not silent-retry |
| VIP-only model/resolution rejected | Explain VIP requirement; offer a non-VIP alternative from current `-h` |

## Important user-facing rules

- Generation is usually asynchronous: submit ≠ finished.
- Some models need a one-time Dreamina Web confirmation before CLI works.
- Different commands do **not** share the same models / ratios / durations / resolutions.
- Always re-check `-h` after CLI updates (`dreamina version`).

## Good agent behavior

- Relay OAuth Device Flow material clearly enough for the user to finish login.
- Always close the login loop with success/reuse/failure.
- Prefer small, reviewable paid batches.
- Record command, arguments, `submit_id`, and terminal status for every paid run.
- When reporting, separate:
  - help-only inspection
  - submit acceptance (`querying`)
  - terminal result (`success` / `fail`)
  - downloaded file paths (if any)
