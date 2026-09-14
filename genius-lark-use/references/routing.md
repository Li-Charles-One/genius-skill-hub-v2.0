# Routing

Use this table to choose which official embedded skill and `lark-cli` domain to inspect.

| User intent | Read official skill | CLI domain |
| --- | --- | --- |
| Auth, login, profile, scopes, `_notice`, permission errors | `lark-shared` | `auth`, `config`, `profile`, `doctor` |
| Feishu Docs / Docx / Wiki document content, create or edit docs, document media | `lark-doc` | `docs` |
| Cloud Drive files, folders, upload/download, import local files, permissions, comments, versions | `lark-drive` | `drive` |
| Drive-native Markdown file read/create/patch/overwrite | `lark-markdown` | `markdown` |
| Wiki spaces, nodes, node tree, space members | `lark-wiki` | `wiki` |
| Base / Bitable / multi-dimensional tables, records, fields, views, dashboards, forms, workflows, BaseApp / AppMode, template center | `lark-base` | `base` |
| Sheets / spreadsheet cells, worksheets, formulas, charts, filters, pivots, financial modeling (DCF, 3-statement) | `lark-sheets` | `sheets` |
| Slides / presentations, pages, slide content | `lark-slides` | `slides` |
| Whiteboard content, export image, edit board nodes | `lark-whiteboard` | `whiteboard` |
| IM messages, groups, chat search, reactions, interactive cards, urgent messages | `lark-im` | `im` |
| Mail, drafts, send/reply/forward, mailbox search, folders, labels | `lark-mail` | `mail` |
| Calendar agenda, events, attendees, free/busy, meeting rooms | `lark-calendar` | `calendar` |
| Tasks, task lists, subtasks, assignment, reminders, task attachments | `lark-task` | `task` |
| Contacts, user lookup by name/email/open_id, profile details | `lark-contact` | `contact` |
| Approval tasks, instances, approve/reject/transfer/cancel/CC | `lark-approval` | `approval` |
| Video meetings, meeting records, summaries, minutes (妙记), notes, transcripts, live meeting participation & Q&A | `lark-meeting` | `vc`, `minutes`, `note` |
| OKR objectives, key results, alignments, progress | `lark-okr` | `okr` |
| Personal attendance check-in records | `lark-attendance` | `attendance` |
| Spark/Miaoda apps, full-stack local/cloud dev, interactive prototype / mockup / deck, deploy, monitoring | `lark-apps` | `apps` |
| Real-time events, websocket subscriptions, bounded event consumption | `lark-event` | `event` |
| API not covered by existing CLI domain or skill | `lark-openapi-explorer` | `api`, `schema` |
| Build a reusable custom Lark skill | `lark-skill-maker` | varies |
| Meeting summary workflow across a date range | `lark-workflow-meeting-summary` | `vc`, `minutes`, `docs` |
| Standup/day plan from calendar plus tasks | `lark-workflow-standup-report` | `calendar`, `task` |

## URL and Token Hints

- `/docx/`, `/docs/`, document token, or Wiki document content: start with `lark-doc`.
- `/drive/`, file token, folder token, upload/download intent: start with `lark-drive`.
- `/base/`, `bitable`, app token, table ID, field ID, record ID: start with `lark-base`.
- `/sheets/` or spreadsheet token: start with `lark-sheets`.
- `/wiki/` plus space or node management: start with `lark-wiki`; if the user wants document body content inside a wiki node, use `lark-doc` after resolving the node.
- `/slides/`: start with `lark-slides`.
- Chat ID, open ID, message ID, group, robot, card callback: start with `lark-im`.

Do not route by domain name alone. Some `doubao.com` URLs may still represent Lark-compatible doc, wiki, sheet, or slide resources; route by path pattern and token type.
