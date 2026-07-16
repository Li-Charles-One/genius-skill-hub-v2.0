#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const {
  allowNoCheck,
  defaultAgent,
  detectProjectConfig,
  emitResult,
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
  --agent <name>       Agent name. Default: $WEPLANING_AGENT or "Agent"
  --adapter <name>     Adapter name. Default: unknown
  --os <name>          OS name. Default: process platform
  --short-id <id>      Short suffix for root session. Default: root
  --type <code|ops-doc> Project type (default: auto-detect)
  --code-vcs <text>    Code versioning tool (default: auto-detect)
  --sync <text>        Sync strategy note (default: auto-detect)
  --force              Allow initializing when .agent-memory already exists
  --json               Print machine-readable JSON result on stdout
  --no-check           Internal use only; external callers must run consistency checks
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "init-memory.cjs");

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

const agent = args.agent || defaultAgent();
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

const projectConfig = detectProjectConfig(root, {
  type: args.type,
  "code-vcs": args["code-vcs"],
  sync: args.sync,
});

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
    goal: `Bootstrap WePlaning v2.3 memory for ${project}.`,
    contextRead: "- Initial project context",
    workNotes: "- Initialized WePlaning memory.",
    filesTouched: `- .agent-memory/CURRENT.md
- .agent-memory/THREADS.md
- .agent-memory/CHANGES.md
- .agent-memory/sessions/${sessionId}.md`,
    decisions: "- Use WePlaning v2.3 memory.",
    result: "Memory initialized.",
    exactNextStep: goal,
  }),
);

writeMemory(
  root,
  "CURRENT.md",
  renderCurrentMd({
    lastUpdated: now,
    mainlineSession: sessionId,
    activeGoal: goal,
    currentUnderstanding: `${project} memory has been initialized. Accepted project facts should live here, while in-progress work should live in session files.`,
    currentState: "- WePlaning v2.3 memory is active.\n- Required memory files exist.",
    acceptedNextSteps: "1. Continue from the active goal.\n2. Open a new session for durable work.",
    openBlockers: "none",
    projectConfig: projectConfig.text,
    basedOn: `- Session: ${sessionId}\n- Last change: ${now} init`,
  }),
);

writeMemory(
  root,
  "DECISIONS.md",
  `# Decisions
Schema version: 2.3

## ${now} bootstrap
- Session: ${sessionId}
- Decision: Use WePlaning v2.3 project memory
- Rationale: Durable multi-session / multi-Agent state for ${project}
`,
);

writeMemory(
  root,
  "THREADS.md",
  `# Threads
Schema version: 2.3
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
Schema version: 2.3

## ${now} init
- Session: ${sessionId}
- Agent: ${agent}
- Role: creator
- Based on: root
- Change ID: ${now} init
- Changed:
  - Bootstrapped WePlaning v2.3 memory
- Files touched:
  - .agent-memory/CURRENT.md
  - .agent-memory/THREADS.md
  - .agent-memory/CHANGES.md
  - .agent-memory/sessions/${sessionId}.md
- Verification:
  - Required memory files created
- Notes:
  - Project: ${project}
`,
);

if (!args["no-check"]) runCheck(root, __dirname);
emitResult(args, sessionId, {
  sessionId,
  project,
  goal,
  projectConfig: { type: projectConfig.type, codeVcs: projectConfig.codeVcs, sync: projectConfig.sync },
});
