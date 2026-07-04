---
name: github-cli
description: "Use when a task needs GitHub CLI (`gh`) on this machine: install or verify `gh`, check or repair authentication, search GitHub with `gh search`, or run GitHub CLI commands for repositories, pull requests, issues, releases, Actions, secrets, variables, projects, organizations, keys, browsing, status, or API requests."
---

# GitHub CLI

## Purpose

Use `gh` directly for GitHub work, but never assume a new session still has the CLI installed or authenticated. Always verify and bootstrap the local environment first.

## Workflow

1. Check whether `gh` exists:

   ```bash
   command -v gh
   gh --version
   ```

   On Windows PowerShell:

   ```powershell
   Get-Command gh -ErrorAction SilentlyContinue
   gh --version
   ```

2. If missing, install it with the platform package manager when available:

   ```bash
   # macOS
   brew install gh
   ```

   ```powershell
   # Windows
   winget install --id GitHub.cli
   ```

3. Check auth every session:

   ```bash
   gh auth status
   ```

4. If not logged in, authenticate with the browser flow and save credentials to the keyring:

   ```bash
   gh auth login --hostname github.com --web --clipboard --git-protocol https
   ```

   If the interactive prompt stalls in this environment, retry with:

   ```bash
   GH_PROMPT_DISABLED=1 gh auth login --hostname github.com --web --clipboard --git-protocol https
   ```

   In PowerShell:

   ```powershell
   $env:GH_PROMPT_DISABLED = "1"
   gh auth login --hostname github.com --web --clipboard --git-protocol https
   ```

5. Confirm the login and active account:

   ```bash
   gh auth status
   gh api user --jq '.login'
   ```

## Use

After the bootstrap checks pass, use `gh` for GitHub commands instead of manual browser navigation when possible. Keep the login state local to the machine and re-check it in every new session.

Use the installed CLI as the source of truth. Before using an unfamiliar command or flag, run one of:

```bash
gh help
gh <command> --help
gh <command> <subcommand> --help
```

## Command Map

Map user intent to real `gh` commands:

- Account/login: `gh auth`, `gh auth status`, `gh config`
- Repositories: `gh repo create|clone|fork|list|view|edit|delete|sync|set-default`
- Pull requests: `gh pr create|list|view|checkout|diff|checks|review|comment|merge|close`
- Issues: `gh issue create|list|view|comment|edit|close|reopen|develop`
- Releases: `gh release create|list|view|download|upload|edit|delete`
- GitHub Actions: `gh workflow list|view|run|enable|disable`, `gh run list|view|watch|download|rerun|cancel`, `gh cache`
- Secrets and variables: `gh secret`, `gh variable`
- Search: `gh search repos|issues|prs|code|commits`
- Organizations, projects, gists, labels, keys, rulesets, codespaces: `gh org`, `gh project`, `gh gist`, `gh label`, `gh ssh-key`, `gh gpg-key`, `gh ruleset`, `gh codespace`
- Current work/status: `gh status`
- API escape hatch: `gh api` for REST and GraphQL when no higher-level `gh` command fits
- Browser handoff: `gh browse` when the user wants to open GitHub UI for a repo, issue, PR, run, or file

For GitHub search tasks, prefer `gh search` before falling back to browser search:

```bash
gh search repos "query"
gh search issues "query"
gh search prs "query"
gh search code "query"
gh search commits "query"
```

When the query uses exclusion qualifiers that start with `-`, pass `--` before the query so the shell does not treat the qualifier as a flag:

```bash
gh search issues -- "query -label:bug"
```

For structured output, prefer `--json`, `--jq`, or `--template` when supported. Use `gh help formatting` if output needs filtering or formatting.

## Rate Limits

GitHub REST API allows 5 000 requests/hour per authenticated user. `gh api` calls count toward this limit.

- Prefer `--paginate` to merge multi-page responses into one call instead of looping.
- When the limit is hit, `gh` returns HTTP 429. Check the reset time with: `gh api rate_limit --jq '.rate.reset'` (Unix timestamp). Wait until that time before retrying.
- `gh search` and GraphQL via `gh api graphql` have separate, lower limits — check `gh api rate_limit` for the full breakdown.
