#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const {
  allowNoCheck,
  defaultAgent,
  detectProjectConfig,
  emitResult,
  extractField,
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
  --force              Create only the files that are missing; never touch existing ones
  --reinit             Discard the existing memory and bootstrap from scratch (destructive)
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
const memoryExists = fs.existsSync(memoryDir);

usage(!(args.force && args.reinit), "Conflicting flags: --force fills gaps, --reinit rewrites everything", help);
if (memoryExists && !args.force && !args.reinit) {
  console.error(
    ".agent-memory already exists. Pick the intent explicitly:\n" +
    "  --force   create only the files that are missing, leaving existing ones untouched\n" +
    "  --reinit  discard the existing memory and bootstrap from scratch (destroys history)",
  );
  process.exit(1);
}

function existingField(file, label) {
  const filePath = path.join(memoryDir, file);
  if (!fs.existsSync(filePath)) return null;
  return extractField(fs.readFileSync(filePath, "utf8"), label);
}

const agent = args.agent || defaultAgent();
const adapter = args.adapter || "unknown";
const os = args.os || process.platform;
const now = args.started || utcNow();
// Filling a gap must adopt the surviving mainline; inventing a second root session
// would leave CURRENT.md and THREADS.md pointing at different sessions.
const inheritedMainline = args.reinit
  ? null
  : existingField("CURRENT.md", "Mainline session") || existingField("THREADS.md", "Mainline session");
const sessionId =
  inheritedMainline ||
  generateSessionId({
    iso: now,
    agent,
    os,
    role: "creator",
    shortId: args["short-id"] || "root",
  });

if (args.reinit && memoryExists) {
  const threadsText = fs.existsSync(path.join(memoryDir, "THREADS.md"))
    ? fs.readFileSync(path.join(memoryDir, "THREADS.md"), "utf8")
    : "";
  const changesText = fs.existsSync(path.join(memoryDir, "CHANGES.md"))
    ? fs.readFileSync(path.join(memoryDir, "CHANGES.md"), "utf8")
    : "";
  console.error(
    `--reinit discards ${(threadsText.match(/^\| \S+ \|/gm) || []).length} session row(s) and ` +
    `${(changesText.match(/^## /gm) || []).length} change block(s). ` +
    `Previous versions remain in .agent-memory/.backups until rotated out.`,
  );
}

fs.mkdirSync(path.join(memoryDir, "sessions"), { recursive: true });

const projectConfig = detectProjectConfig(root, {
  type: args.type,
  "code-vcs": args["code-vcs"],
  sync: args.sync,
});

const created = [];
const kept = [];

/** --force must fill gaps only; overwriting here is what silently destroyed whole memories. */
function put(relativePath, text) {
  if (!args.reinit && fs.existsSync(path.join(memoryDir, relativePath))) {
    kept.push(relativePath);
    return;
  }
  writeMemory(root, relativePath, text);
  created.push(relativePath);
}

const sessionRelativePath = `sessions/${sessionId}.md`;
if (args.reinit || !fs.existsSync(path.join(memoryDir, "sessions", `${sessionId}.md`))) {
  created.push(sessionRelativePath);
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
} else {
  kept.push(sessionRelativePath);
}

put(
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

put(
  "DECISIONS.md",
  `# Decisions
Schema version: 2.3

## ${now} bootstrap
- Session: ${sessionId}
- Decision: Use WePlaning v2.3 project memory
- Rationale: Durable multi-session / multi-Agent state for ${project}
`,
);

put(
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

put(
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

if (kept.length) {
  console.error(`Left ${kept.length} existing file(s) untouched: ${kept.join(", ")}`);
}
if (!args["no-check"]) runCheck(root, __dirname);
emitResult(args, sessionId, {
  sessionId,
  project,
  goal,
  created,
  kept,
  mode: args.reinit ? "reinit" : memoryExists ? "fill-gaps" : "init",
  projectConfig: { type: projectConfig.type, codeVcs: projectConfig.codeVcs, sync: projectConfig.sync },
});
