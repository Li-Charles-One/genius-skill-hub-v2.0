#!/usr/bin/env node

const path = require("path");
const {
  activeCount,
  extractField,
  parseArgs,
  readMemory,
  readSession,
  readThreads,
  replaceField,
  required,
  runCheck,
  updateWePlaning,
  usage,
  utcNow,
  writeMemory,
  writeSession,
  writeThreads,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node merge-session.cjs <project-root> --session <id> [options]

Options:
  --agent <name>              Defaults to session Agent field
  --allow-branch              Allow merge when parent is not current mainline
  --no-current-update         Do not update CURRENT.md metadata
  --no-check                  Skip consistency check
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const sessionId = required(args, "session", help);
const now = args.time || utcNow();
let threads = readThreads(root);
let sessionText = readSession(root, sessionId);
const parent = extractField(sessionText, "Parent session") || "unknown";
const agent = args.agent || extractField(sessionText, "Agent") || "unknown";

if (
  !args["allow-branch"] &&
  threads.mainline !== sessionId &&
  parent !== threads.mainline
) {
  console.error(
    `Refusing to merge branch session. Parent=${parent}, current mainline=${threads.mainline}. Use --allow-branch to override.`,
  );
  process.exit(1);
}

const row = threads.rows.find((item) => item.id === sessionId);
if (!row) {
  console.error(`Session is not listed in THREADS.md: ${sessionId}`);
  process.exit(1);
}

row.status = "merged";
threads = { ...threads, mainline: sessionId, lastMerged: sessionId };
writeThreads(root, threads, now);

sessionText = replaceField(sessionText, "Status", "merged");
const closed = extractField(sessionText, "Closed");
if (!closed || closed === "unknown" || closed === "(open)") {
  sessionText = replaceField(sessionText, "Closed", now);
}
writeSession(root, sessionId, sessionText);

if (!args["no-current-update"]) {
  let current = readMemory(root, "CURRENT.md");
  current = replaceField(current, "Last updated", now);
  current = replaceField(current, "Mainline session", sessionId);
  writeMemory(root, "CURRENT.md", current);
}

updateWePlaning(root, {
  updated: now,
  updatedBy: agent,
  mainline: sessionId,
  lastClosed: sessionId,
  activeSessions: activeCount(threads.rows),
});

if (!args["no-check"]) runCheck(root, __dirname);
console.log(sessionId);
