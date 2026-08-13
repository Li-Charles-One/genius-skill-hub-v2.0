#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const {
  allowNoCheck,
  emitResult,
  parseArgs,
  required,
  runCheck,
  usage,
  utcNow,
  withMemoryLock,
  writeMemory,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node append-decision.cjs <project-root> --decision <text> [options]

Appends an entry to .agent-memory/DECISIONS.md (creates file if missing).

Options:
  --rationale <text>   Why this decision was made
  --session <id>       Related session id
  --agent <name>       Agent name
  --time <iso>         Entry timestamp. Default: now
  --json               Machine-readable JSON on stdout
  --no-check           Internal use only; external callers must run consistency checks
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "append-decision.cjs");

const root = path.resolve(args._[0] || process.cwd());
const decision = required(args, "decision", help);
const rationale = args.rationale ? String(args.rationale) : "none";
const session = args.session ? String(args.session) : "unknown";
const agent = args.agent ? String(args.agent) : "unknown";
const now = args.time || utcNow();
const filePath = path.join(root, ".agent-memory", "DECISIONS.md");

withMemoryLock(root, () => {
  if (!fs.existsSync(path.join(root, ".agent-memory"))) {
    console.error("Missing .agent-memory — init memory first.");
    process.exit(1);
  }
  let text = "";
  if (fs.existsSync(filePath)) {
    text = fs.readFileSync(filePath, "utf8").replace(/\s*$/, "");
  } else {
    text = `# Decisions\nSchema version: 3.0`;
  }
  const entry = `
## ${now} decision
- Session: ${session}
- Agent: ${agent}
- Decision: ${decision}
- Rationale: ${rationale}
`;
  writeMemory(root, "DECISIONS.md", `${text}\n${entry}`);
});

if (!args["no-check"]) runCheck(root, __dirname);

emitResult(args, `decision recorded`, {
  decision,
  rationale,
  session,
  path: ".agent-memory/DECISIONS.md",
});
