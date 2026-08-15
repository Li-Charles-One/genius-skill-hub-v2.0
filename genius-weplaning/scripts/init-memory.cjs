#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const {
  allowNoCheck,
  defaultAgent,
  detectProjectConfig,
  emitResult,
  parseArgs,
  renderCurrentMd,
  runCheck,
  SCHEMA_VERSION,
  usage,
  utcNow,
  writeMemory,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node init-memory.cjs <project-root> --project <name> --goal <text> [options]

Options:
  --agent <name>       Agent name. Default: $WEPLANING_AGENT or "Agent"
  --type <code|ops-doc> Project type (default: auto-detect)
  --code-vcs <text>    Code versioning tool (default: auto-detect)
  --sync <text>        Sync strategy note (default: auto-detect)
  --force              Create only the files that are missing; never touch existing ones
  --reinit             Discard CURRENT/CHANGES/DECISIONS and bootstrap from scratch
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
      "  --reinit  discard CURRENT/CHANGES/DECISIONS and bootstrap from scratch (destroys history)",
  );
  process.exit(1);
}

const agent = args.agent || defaultAgent();
const now = args.started || utcNow();

if (args.reinit && memoryExists) {
  const changesText = fs.existsSync(path.join(memoryDir, "CHANGES.md"))
    ? fs.readFileSync(path.join(memoryDir, "CHANGES.md"), "utf8")
    : "";
  console.error(
    `--reinit discards ${(changesText.match(/^## /gm) || []).length} change block(s). ` +
      `Previous versions remain in .agent-memory/.backups until rotated out.`,
  );
}

fs.mkdirSync(memoryDir, { recursive: true });

const projectConfig = detectProjectConfig(root, {
  type: args.type,
  "code-vcs": args["code-vcs"],
  sync: args.sync,
});

const created = [];
const kept = [];

function put(relativePath, text) {
  if (!args.reinit && fs.existsSync(path.join(memoryDir, relativePath))) {
    kept.push(relativePath);
    return;
  }
  writeMemory(root, relativePath, text);
  created.push(relativePath);
}

put(
  "CURRENT.md",
  renderCurrentMd({
    lastUpdated: now,
    activeGoal: goal,
    currentUnderstanding: `${project} memory has been initialized. Accepted project facts live here.`,
    currentState: `- WePlaning ${SCHEMA_VERSION} memory is active.\n- Required memory files exist.`,
    acceptedNextSteps: "1. Continue from the active goal.",
    openBlockers: "none",
    projectConfig: projectConfig.text,
    basedOn: `- Last change: ${now} init`,
  }),
);

put(
  "DECISIONS.md",
  `# Decisions
Schema version: ${SCHEMA_VERSION}

## ${now} bootstrap
- Agent: ${agent}
- Decision: Use WePlaning ${SCHEMA_VERSION} project memory
- Rationale: Durable accepted state for ${project}
`,
);

put(
  "CHANGES.md",
  `# Changes
Schema version: ${SCHEMA_VERSION}

## ${now} init
- Agent: ${agent}
- Change ID: ${now} init
- Changed:
  - Bootstrapped WePlaning ${SCHEMA_VERSION} memory
- Files touched:
  - .agent-memory/CURRENT.md
  - .agent-memory/CHANGES.md
  - .agent-memory/DECISIONS.md
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
emitResult(args, "initialized", {
  project,
  goal,
  created,
  kept,
  schema: SCHEMA_VERSION,
  mode: args.reinit ? "reinit" : memoryExists ? "fill-gaps" : "init",
  projectConfig: { type: projectConfig.type, codeVcs: projectConfig.codeVcs, sync: projectConfig.sync },
});
