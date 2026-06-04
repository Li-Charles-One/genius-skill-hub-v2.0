#!/usr/bin/env node

const path = require("path");
const {
  allowNoCheck,
  extractField,
  parseArgs,
  readMemory,
  readSession,
  readThreads,
  runCheck,
  usage,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node handoff.cjs <project-root> [options]

Options:
  --session <id>     Current session. Default: first active session, else mainline
  --tools <text>     Tools used summary. Default: unknown
  --commands <text>  Commands/tests run summary. Default: unknown
  --merge <text>     Should merge to mainline. Default: unknown
  --no-check         Internal use only; external callers must run consistency checks
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "handoff.cjs");

const root = path.resolve(args._[0] || process.cwd());
if (!args["no-check"]) runCheck(root, __dirname);

const current = readMemory(root, "CURRENT.md");
const threads = readThreads(root);
const currentRow =
  threads.rows.find((row) => row.id === args.session) ||
  threads.rows.find((row) => row.status === "active") ||
  threads.rows.find((row) => row.id === threads.mainline);
const sessionId = args.session || (currentRow ? currentRow.id : threads.mainline);
const sessionText = readSession(root, sessionId);

const packet = {
  Project: extractField(current, "Mainline session") || threads.mainline || "unknown",
  "Current mainline session": threads.mainline || "unknown",
  "Current session": sessionId || "unknown",
  "Parent session": extractField(sessionText, "Parent session") || "unknown",
  "Current goal": current.match(/## Active Goal\n([\s\S]*?)(\n## |$)/)?.[1]?.trim() || "unknown",
  "Current state": current.match(/## Current State\n([\s\S]*?)(\n## |$)/)?.[1]?.trim() || "unknown",
  "Important files": ".agent-memory/CURRENT.md, .agent-memory/THREADS.md, .agent-memory/CHANGES.md, .agent-memory/TOOLS.md",
  "Tools used": args.tools || "unknown",
  "Commands/tests run": args.commands || "unknown",
  "Open blockers": current.match(/## Open Blockers\n([\s\S]*?)(\n## |$)/)?.[1]?.trim() || "unknown",
  "Session status": extractField(sessionText, "Status") || (currentRow ? currentRow.status : "unknown"),
  "Should merge to mainline": args.merge || "unknown",
  "Exact next step": sessionText.match(/## Exact Next Step\n([\s\S]*?)(\n## |$)/)?.[1]?.trim() || "unknown",
};

for (const [key, value] of Object.entries(packet)) {
  console.log(`${key}:`);
  console.log(value || "unknown");
}
