# Health Check

Use this reference when a `lark-cli` command fails (command not found, auth, profile, scope) or when the user asks whether the CLI works. A working command needs no health check first.

## Minimal Checks

Run these when the user asks whether Lark CLI is available, or to locate the cause of a failure:

```bash
command -v lark-cli
lark-cli --version
lark-cli doctor
lark-cli auth status
```

Interpretation:

- `command -v lark-cli` fails: report that the CLI is not installed or not in `PATH`. Do not install unless the user asks.
- `lark-cli --version` succeeds: include the version when status is the user's goal.
- `lark-cli doctor` fails: report the failing section and recommended CLI-provided fix.
- `lark-cli auth status` fails or shows missing login: ask the user whether to start login. Do not start OAuth login silently.

## Profile Checks

If the machine uses multiple Lark apps, tenants, or identities, inspect profiles before changing anything:

```bash
lark-cli profile list
lark-cli config list
lark-cli auth list
```

Use `--profile <name>` only when the user has selected a profile or the current project clearly documents the right profile.

## Scope Checks

When a command fails with permission, scope, or `_notice` output:

```bash
lark-cli skills read lark-shared
lark-cli auth status
lark-cli auth scopes
lark-cli auth check <scope>
```

If a specific command's schema lists required scopes, check those scopes before retrying.

## Login and Config Boundaries

Do not run these without explicit user approval because they may open browser auth flows, create app configuration, or change the active identity:

```bash
lark-cli config init
lark-cli config init --new
lark-cli auth login
lark-cli auth login --recommend
lark-cli auth logout
lark-cli update
```
