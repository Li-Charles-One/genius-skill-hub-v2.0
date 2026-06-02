#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const {
  generateSessionId,
  parseArgs,
  renderCurrentMd,
  renderSessionMd,
  runCheck,
  usage,
  utcNow,
  writeMemory,
  writeSession,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node init-memory.cjs <project-root> --project <name> --goal <text> [options]

Options:
  --agent <name>       Agent name. Default: Codex
  --adapter <name>     Adapter name. Default: unknown
  --os <name>          OS name. Default: process platform
  --short-id <id>      Short suffix for root session. Default: root
  --force              Allow initializing when .agent-memory already exists
  --no-check           Skip consistency check
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const project = args.project;
const goal = args.goal;
usage(project, "Missing required argument: --project", help);
usage(goal, "Missing required argument: --goal", help);

const memoryDir = path.join(root, ".agent-memory");
if (fs.existsSync(memoryDir) && !args.force) {
  console.error(".agent-memory already exists. Use --force only if you intend to create missing files.");
  process.exit(1);
}

const agent = args.agent || "Codex";
const adapter = args.adapter || "unknown";
const os = args.os || process.platform;
const now = args.started || utcNow();
const sessionId = generateSessionId({
  iso: now,
  agent,
  os,
  role: "creator",
  shortId: args["short-id"] || "root",
});

fs.mkdirSync(path.join(memoryDir, "sessions"), { recursive: true });

writeSession(
  root,
  sessionId,
  renderSessionMd({
    sessionId,
    agent,
    adapter,
    os,
    role: "creator",
    parentSession: "root",
    status: "merged",
    started: now,
    closed: now,
    goal: `Bootstrap WePlaning v2.2 memory for ${project}.`,
    contextRead: "- Initial project context",
    workNotes: "- Initialized WePlaning Minimal Mode.",
    filesTouched: `- .agent-memory/WePlaning.md
- .agent-memory/CURRENT.md
- .agent-memory/THREADS.md
- .agent-memory/CHANGES.md
- .agent-memory/TOOLS.md
- .agent-memory/sessions/${sessionId}.md`,
    decisions: "- Use WePlaning v2.2 Minimal Mode.",
    result: "Memory initialized.",
    exactNextStep: goal,
  }),
);

writeMemory(
  root,
  "WePlaning.md",
  `# WePlaning
Schema version: 2.2
Last updated: ${now}
Last updated by: ${agent}

## Read First
| Need | Read | Why |
|:--|:--|:--|
| Current accepted state | CURRENT.md | Mainline |
| Session tree | THREADS.md | Parent/mainline |
| Recent changes | CHANGES.md | Audit trail |
| Tool capabilities | TOOLS.md | Available tools |

## Snapshot
| Key | Value |
|:--|:--|
| Mainline session | ${sessionId} |
| Last closed session | ${sessionId} |
| Active sessions | 0 |
| Blocker | none |

## Human Concerns
- unknown

## Repeat Patterns
| Pattern | Count | Agent workload | Last seen | Suggested action |
|:--|:--|:--|:--|:--|
| — | — | — | — | — |
`,
);

writeMemory(
  root,
  "CURRENT.md",
  renderCurrentMd({
    lastUpdated: now,
    mainlineSession: sessionId,
    activeGoal: goal,
    currentUnderstanding: `${project} memory has been initialized. Accepted project facts should live here, while in-progress work should live in session files.`,
    currentState: "- WePlaning v2.2 memory is active.\n- Minimal Mode files exist.",
    acceptedNextSteps: "1. Continue from the active goal.\n2. Open a new session for durable work.",
    openBlockers: "none",
    basedOn: `- Session: ${sessionId}\n- Last change: ${now} init`,
  }),
);

writeMemory(
  root,
  "THREADS.md",
  `# Threads
Schema version: 2.2
Last updated: ${now}

Mainline session: ${sessionId}
Last merged session: ${sessionId}

## Session Tree

| Session ID | Parent | Agent | OS | Role | Status | Summary |
|:--|:--|:--|:--|:--|:--|:--|
| ${sessionId} | root | ${agent} | ${os} | creator | merged | Bootstrap WePlaning memory for ${project} |
`,
);

writeMemory(
  root,
  "CHANGES.md",
  `# Changes
Schema version: 2.2

## ${now} init
- Session: ${sessionId}
- Agent: ${agent}
- Role: creator
- Based on: root
- Change ID: ${now} init
- Changed:
  - Bootstrapped WePlaning v2.2 Minimal Mode
- Files touched:
  - .agent-memory/WePlaning.md
  - .agent-memory/CURRENT.md
  - .agent-memory/THREADS.md
  - .agent-memory/CHANGES.md
  - .agent-memory/TOOLS.md
  - .agent-memory/sessions/${sessionId}.md
- Verification:
  - Minimal Mode files created
- Notes:
  - Project: ${project}
`,
);

writeMemory(
  root,
  "TOOLS.md",
  `# Tools
Schema version: 2.2
Last updated: ${now}

## Agent Sessions

| Session ID | Agent | OS | Adapter | Tools | MCP | Skills | Notes |
|:--|:--|:--|:--|:--|:--|:--|:--|
| ${sessionId} | ${agent} | ${os} | ${adapter} | unknown | unknown | we-planing | Bootstrapped WePlaning |

## Skills

| Skill | Session ID | Version | Purpose | Location | Trigger |
|:--|:--|:--|:--|:--|:--|
| we-planing | ${sessionId} | 2.2+scripts | Maintain project collaboration memory | unknown | memory/resume/handoff requests |

## Constraints
- Secrets, API keys, tokens, private MCP credentials, cookies, and passwords MUST NOT be recorded.
- Tool capability SHOULD be recorded even when exact configuration is private.
- If a tool is not available, write \`unavailable\`.
- If a tool's availability is unknown, write \`unknown\`.
- Local absolute paths MUST be marked \`local-only\` and include OS when necessary.
`,
);

if (!args["no-check"]) runCheck(root, __dirname);
console.log(sessionId);
