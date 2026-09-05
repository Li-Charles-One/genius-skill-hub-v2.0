---
name: genius-github-usage
description: "Genius GitHub usage via the GitHub CLI (`gh`). Use when the user wants to look up a repo, open or review a PR, check issues, fork, search GitHub, manage Actions/releases, or push/work on GitHub.com. Triggers: 查仓库, 提PR, 看issue, fork, 搜GitHub, 推远端, gh, GitHub. Do not use for non-GitHub remotes or local-only git (status/commit/diff) that never touches GitHub."
---

# Genius GitHub Usage

Use `gh` for GitHub work. Follow official agent patterns in `references/official-gh-patterns.md`.

## Bootstrap

Run the `gh` command first. Only diagnose if it fails (`command not found`, auth error, 401/403).

Then:

1. Find `gh`: `Get-Command gh` / `command -v gh` and `gh --version`.
2. If missing: `brew install gh` or `winget install --id GitHub.cli`.
3. `gh auth status`. If not logged in:

```powershell
$env:GH_PROMPT_DISABLED = "1"
gh auth login --hostname github.com --web --clipboard --git-protocol https
```

```bash
GH_PROMPT_DISABLED=1 gh auth login --hostname github.com --web --clipboard --git-protocol https
```

4. Confirm: `gh api user --jq '.login'`.

Unfamiliar flags: `gh <cmd> --help`.

## After bootstrap

Prefer `gh` over clicking around the website. Map intent:

- Auth: `gh auth`, `gh auth status --json`, `gh config`
- Repos: `gh repo create|clone|fork|list|view|edit|delete|sync|set-default`
- Read without clone: `gh repo read-file`, `gh repo read-dir`
- PRs: `gh pr create|list|view|checkout|diff|checks|review|comment|merge|close`
- Issues: `gh issue create|list|view|comment|edit|close|reopen|develop`
- Discussions: `gh discussion list|view|create|edit|comment`
- Releases: `gh release ...`
- Actions: `gh workflow ...`, `gh run ...`, `gh cache`
- Secrets/vars: `gh secret`, `gh variable`
- Search: `gh search repos|issues|prs|code|commits|users`
- Org/project/gist/keys: `gh org`, `gh project`, `gh gist`, `gh label`, `gh ssh-key`, `gh codespace`
- Status: `gh status`
- Escape hatch: `gh api` / `gh api graphql`
- Browser: `gh browse`

Cross-repo or author/label filters: `gh search`, not `gh issue list`. Exclusion queries that start with `-` need `--`:

```bash
gh search issues -- "query -label:bug"
```

Qualifiers must be bare tokens, not one quoted blob. Details: `references/official-gh-patterns.md`.

## Must follow (from official `gh` skill)

- Structured data: `--json` fields, then `--jq`. `--json` with no fields lists available fields.
- Lists silently cap (default ~30). Pass `-L N`. `gh api --paginate` for REST.
- Target another repo with `-R OWNER/REPO`.
- Dependabot: `--app dependabot`, not `--author dependabot`.
- `gh pr view --comments` is issue comments. Review threads: `gh api repos/{owner}/{repo}/pulls/{n}/comments`.
- Non-interactive `gh pr create` / `gh issue create` need `--title` and `--body`.
- Do not invent `--no-pager`.

## Action safety

- **Read-only:** views, searches, `gh api` GETs, and status checks may run directly.
- **Reversible writes:** draft PRs, issues, comments, and ordinary branch pushes should show the target and changed scope before execution.
- **High-risk writes:** merge/close/delete, release deletion, secret or variable changes, force-push, and remote branch replacement require confirmation.

For a commit/push, check `git status --short`, `git diff --check`, `git diff --stat`, the remote, and the current branch first; stage only the intended files, then verify `git status --short` after pushing. If push is rejected, stop: do not force-push, reset, or choose merge/rebase automatically.

## Confirm first

Ask the user before:

- `gh repo delete`
- `gh pr merge` / `gh pr close`
- changing `gh secret` or `gh variable`
- `gh release delete`
- force-push or other irreversible GitHub writes

Reads, search, `gh pr create` drafts, and `gh api` GETs do not need a confirm.

## Rate limits

REST: 5000/hour per user. `gh api` counts. On 429: `gh api rate_limit --jq '.rate.reset'`. Search and GraphQL have separate, lower limits.

## Gotchas

- This skill is GitHub via `gh`. Local `git status` / `git commit` with no GitHub step is not this skill.
- Official usage details live in `references/official-gh-patterns.md`. Do not guess flags that skill already documents.

## Resource Map

- `references/official-gh-patterns.md` — upstream `cli/cli` skills/gh
