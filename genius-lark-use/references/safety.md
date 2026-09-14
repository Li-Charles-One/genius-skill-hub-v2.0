# Safety Rules

Lark/Feishu operations can affect other people, publish data, or modify shared resources. Confirm before hard-to-reverse or outward-facing actions.

## Always Confirm First

Ask for explicit confirmation before running commands that do any of the following:

- Send IM messages, interactive cards, urgent notifications, SMS, phone reminders, or emails.
- Create public or externally accessible links.
- Change sharing, permissions, ownership, members, or visibility.
- Delete, move, archive, overwrite, replace, or restore files, folders, docs, wiki nodes, slides, sheets, Base records, tasks, calendar events, or messages.
- Batch update Base records, Sheets cells, task lists, approvals, calendar attendees, or permissions.
- Approve, reject, transfer, cancel, or CC approval instances.
- Upload local sensitive files or import local files into a shared Lark/Feishu space.
- Start, change, or revoke auth/config/profile for the user's Lark account.

Confirmation should name the target and action, for example: "Confirm sending this message to chat `Sales Ops`?" or "Confirm overwriting document `<title>`?".

## Usually Safe Without Confirmation

These actions are normally safe:

- CLI discovery: `command -v lark-cli`, `lark-cli --version`, `lark-cli --help`.
- Health checks: `lark-cli doctor`, `lark-cli auth status`.
- Reading command help, schemas, or embedded skills.
- Read-only queries such as listing calendars, reading document content, viewing file metadata, searching tasks, or inspecting Base records.
- Dry runs that do not modify remote state.

## Use Dry Run When Available

For supported write commands, run with `--dry-run` first when the target or payload is complex. Show the user the relevant target and high-level payload, not secrets or raw OAuth data.

## Sensitive Output Handling

Do not expose:

- App secrets, OAuth tokens, refresh tokens, cookies, or keychain values.
- Full private message/email bodies unless the user specifically asked to read them.
- Raw bulk exports of personal data when a summary is enough.

If a command returns sensitive JSON, summarize the fields needed for the task and omit credentials or private identifiers unless they are needed for a follow-up command.
