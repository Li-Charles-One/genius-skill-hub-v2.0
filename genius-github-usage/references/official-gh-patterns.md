# Official `gh` agent patterns

Copied from [`cli/cli` `skills/gh`](https://github.com/cli/cli/blob/trunk/skills/gh/SKILL.md) (MIT), synced 2026-08-15. If a flag disagrees with `gh <cmd> --help`, trust `--help`. Read this when using `--json`, search, discussions, `read-file`, or `gh api`.

## Interactivity policy

`gh` already does the right thing in non-TTY contexts: it skips the pager, strips ANSI color, and errors out fast instead of prompting (e.g. `must provide --title and --body when not running interactively`). Do not set `GH_PAGER` or pass `--no-pager` (no such flag exists).

## Parsing JSON

- Add `--json field1,field2,...` for structured output.
- Run a command with `--json` and **no field list** to print available fields, then pick what you need.
- Use `--jq '<expr>'` for filtering without a separate `jq`.
- Use `--template '<go-template>'` with `--json` for shaped text. `--template`/`-T` collides with a body-template flag on `gh pr create -T` and `gh issue create -T`. Check `--help`.

## Pagination and silent truncation

- `gh issue list`, `gh pr list`, `gh search ...`: pass `-L N`. Default is usually 30.
- `gh issue list` / `gh pr list` do not expose `totalCount` via `--json`. For a true total, use `gh api graphql`. Otherwise treat `-L` as the cap.
- Raw API: `gh api --paginate <path>`. Combine with `--jq` and optionally `--slurp`.

## Repo targeting

`gh` infers the repo from cwd remotes. Pass `--repo OWNER/REPO` (`-R`) to override.

## Search vs list

- `gh search issues|prs|code|repos|commits|users` uses the search index. Pass each qualifier as its own bare token, not one quoted string:
  - Good: `gh search issues repo:cli/cli is:open author:monalisa`
  - Bad: `gh search issues "repo:cli/cli is:open"` (parsed as one keyword)
- Quote only multi-word free text: `gh search issues "broken feature"`.
- Prefer dedicated flags (`--repo`, `--author`, `--label`) when they exist.
- `gh issue list --search "..."` / `gh pr list --search "..."` take one quoted string and stay in one repo.
- Bots are GitHub Apps. `--author dependabot` matches nothing. Use `--app dependabot` or `--author "dependabot[bot]"`.
- `gh search issues --search-type lexical|semantic|hybrid` (github.com issues only). Use `semantic` for natural-language problem descriptions.

## Issue types, sub-issues, and relationships

- `gh issue create`: `--type`, `--parent`, `--blocked-by`, `--blocking`.
- `gh issue edit`: `--type` / `--remove-type`, `--parent` / `--remove-parent`, `--add-sub-issue` / `--remove-sub-issue`, `--add-blocked-by` / `--remove-blocked-by`, `--add-blocking` / `--remove-blocking`.
- `--json` fields: `issueType`, `parent`, `subIssues`, `subIssuesSummary`, `blockedBy`, `blocking`. Those relationship fields are `{nodes, totalCount}`, not flat arrays. Compare node count to `totalCount` for truncation.
- GHES: types/sub-issues need 3.17+; blocked-by needs 3.19+.

## Discussions (`gh discussion`)

Preview command set. `list`, `view`, `create`, `edit`, `comment`. Non-interactive create needs `--title`, a body, and `--category`. `--json` is on `list` and `view` only.

## Reading files without cloning

- `gh repo read-file <path> [--ref] [--output] [--json]`
- `gh repo read-dir [<path>] [--ref] [--json]`
- Honor `-R OWNER/REPO`. Binary on a TTY is refused. `--output` and `--json` are mutually exclusive.

## Fall back to `gh api`

- PR review-thread comments: `gh api repos/{owner}/{repo}/pulls/{n}/comments` (`gh pr view --comments` is issue-level only).
- GraphQL: `gh api graphql -f query='...' -F var=value`.
- `{owner}/{repo}` in `gh api` paths is filled from remotes when present.

## Other notes

- `gh pr checkout <n>` switches branches. Use `gh pr diff` / `gh pr view` to only read.
- `gh pr checkout <n> --worktree <path>` uses a worktree instead.
- Leave `GH_FORCE_TTY` unset unless you need TTY-style output inside an agent harness.
