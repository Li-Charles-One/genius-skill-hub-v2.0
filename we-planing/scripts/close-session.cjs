#!/usr/bin/env node

const path = require("path");
const {
  activeCount,
  allowNoCheck,
  extractField,
  parseArgs,
  readSession,
  readThreads,
  replaceField,
  required,
  runCheck,
  updateWePlaning,
  usage,
  utcNow,
  withMemoryLock,
  writeSession,
  writeThreads,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node close-session.cjs <project-root> --session <id> --status <paused|abandoned|merged> [options]

Options:
  --agent <name>    Defaults to session Agent field
  --no-check        Internal use only; external callers must run consistency checks
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "close-session.cjs");

const root = path.resolve(args._[0] || process.cwd());
const sessionId = required(args, "session", help);
const status = required(args, "status", help);
if (!["paused", "abandoned", "merged"].includes(status)) {
  console.error("--status must be paused, abandoned, or merged");
  process.exit(1);
}

const now = args.time || utcNow();
withMemoryLock(root, () => {
  let sessionText = readSession(root, sessionId);
  const agent = args.agent || extractField(sessionText, "Agent") || "unknown";
  const threads = readThreads(root);
  const row = threads.rows.find((item) => item.id === sessionId);
  if (!row) {
    console.error(`Session is not listed in THREADS.md: ${sessionId}`);
    process.exit(1);
  }

  if (threads.mainline === sessionId && status !== "merged") {
    console.error("Cannot close the mainline session as paused or abandoned. Merge another session first.");
    process.exit(1);
  }

  row.status = status;
  if (status === "merged") {
    threads.mainline = sessionId;
    threads.lastMerged = sessionId;
  }
  writeThreads(root, threads, now);

  sessionText = replaceField(sessionText, "Status", status);
  const closed = extractField(sessionText, "Closed");
  if (!closed || closed === "unknown" || closed === "(open)") {
    sessionText = replaceField(sessionText, "Closed", now);
  }
  writeSession(root, sessionId, sessionText);

  updateWePlaning(root, {
    updated: now,
    updatedBy: agent,
    mainline: threads.mainline,
    lastClosed: sessionId,
    activeSessions: activeCount(threads.rows),
  });
});

if (!args["no-check"]) runCheck(root, __dirname);
console.log(sessionId);
