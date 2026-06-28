# Command Patterns

Use these patterns after routing to the right domain. The examples use POSIX shell syntax; on Windows, run the same `lark-cli` commands from PowerShell and adapt quoting for JSON payloads.

## Discover Commands

```bash
lark-cli skills list
lark-cli skills read <skill-name>
lark-cli <domain> --help
lark-cli <domain> <command> --help
lark-cli schema <service.resource.method>
```

Read the official embedded skill for the domain before using unfamiliar commands. The embedded skill is version-matched to the installed `lark-cli` binary.

## Prefer Structured Output

When downstream parsing is needed:

```bash
lark-cli <domain> <command> --format json
lark-cli <domain> <command> --format table
lark-cli <domain> <command> --page-all
```

Use JSON for agent reasoning and tables for user-facing inspection. Avoid dumping huge JSON into the final answer; summarize counts, names, URLs, and relevant IDs.

## Raw API Fallback

If no shortcut or domain command covers the task:

```bash
lark-cli skills read lark-openapi-explorer
lark-cli schema <service.resource.method>
lark-cli api GET /open-apis/<path>
lark-cli api POST /open-apis/<path> --params '<json>' --data '<json>'
```

Only use raw API after checking command help or schema. Prefer `lark-cli api` over direct HTTP requests because it uses configured auth and CLI safety behavior.

## Common Shortcuts

Examples to inspect, not blind templates:

```bash
lark-cli calendar +agenda
lark-cli docs +create --help
lark-cli docs +fetch --help
lark-cli docs +update --help
lark-cli drive +search --help
lark-cli im +messages-send --help
```

For any write command, check `references/safety.md` before execution.

## Error Handling

When a command fails:

1. Preserve the exact concise error message.
2. If auth or scope related, read `lark-shared` and inspect `lark-cli auth status`.
3. If parameter related, run command help or `lark-cli schema`.
4. If URL/token parsing is uncertain, re-route using `references/routing.md` URL hints.
5. Do not retry a write command repeatedly. Fix the cause first and reconfirm if the target or payload changes.
