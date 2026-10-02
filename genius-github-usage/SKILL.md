---
name: genius-github-usage
description: "通过 GitHub CLI (gh) 操作 GitHub 远端：管理仓库、Issue、审查 PR、Fork、Release 与检索开源项目。不要用于不涉及 GitHub 远端的纯本地 Git 操作（如本地 status/commit/diff）。"
metadata:
  version: "1.1.1"
---

# Genius GitHub Usage

Use `gh` for GitHub work; prefer it over the website. This skill adds action safety on top of the official agent patterns in [`cli/cli` `skills/gh`](https://github.com/cli/cli/blob/trunk/skills/gh/SKILL.md) (install with `gh skill install cli/cli gh`). For unfamiliar flags, trust `gh <cmd> --help`.

## Bootstrap

Run the `gh` command first. Only diagnose if it fails (`command not found`, auth error, 401/403):

1. `command -v gh` / `Get-Command gh`, then `gh --version`. If missing: `brew install gh` or `winget install --id GitHub.cli`.
2. `gh auth status`. If not logged in: `GH_PROMPT_DISABLED=1 gh auth login --hostname github.com --web --git-protocol https` (PowerShell: set `$env:GH_PROMPT_DISABLED = "1"` first).
3. Confirm: `gh api user --jq '.login'`.

## Must Follow

- Structured data: `--json` fields, then `--jq`. `--json` with no fields lists available fields.
- Lists silently cap (default ~30). Pass `-L N`; use `gh api --paginate` for REST.
- Target another repo with `-R OWNER/REPO`.
- Cross-repo or author/label filters: `gh search`, with each qualifier a bare token. Exclusions starting with `-` need `--`: `gh search issues -- "query -label:bug"`.
- Bots are apps: `--app dependabot`, not `--author dependabot`.
- `gh pr view --comments` is issue comments. Review threads: `gh api repos/{owner}/{repo}/pulls/{n}/comments`.
- Non-interactive `gh pr create` / `gh issue create` need `--title` and `--body`. Do not invent `--no-pager`.
- On 429 or rate errors: `gh api rate_limit --jq '.rate.reset'`.

## Action Safety

- **Read-only** — views, searches, `gh api` GETs, status checks: run directly.
- **Reversible writes** — draft PRs, issues, comments, ordinary branch pushes: show the target and changed scope first.
- **High-risk writes** — ask the user before `gh repo delete`, `gh pr merge` / `gh pr close`, `gh release delete`, changing `gh secret` / `gh variable`, force-push, or remote branch replacement.

Before a push: check `git status --short`, `git diff --check`, `git diff --stat`, the remote, and the current branch; stage only intended files; verify `git status --short` afterward. If push is rejected, stop — do not force-push, reset, or pick merge/rebase automatically.

Local `git status` / `git commit` with no GitHub step is not this skill.

Trigger checks: `evals/evals.json`.
