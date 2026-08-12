#!/usr/bin/env node

const path = require("path");
const {
  allowNoCheck,
  extractField,
  parseArgs,
  readMemory,
  readSession,
  readThreads,
  replaceField,
  required,
  runCheck,
  section,
  usage,
  utcNow,
  withMemoryLock,
  writeMemory,
  writeSession,
  writeThreads,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node merge-session.cjs <project-root> --session <id> [options]

Options:
  --agent <name>              Defaults to session Agent field
  --time <iso>                Merge timestamp. Default: now
  --allow-branch              Allow merge when parent is not current mainline
  --no-current-update         Do not update CURRENT.md metadata
  --no-check                  Internal use only; external callers must run consistency checks
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "merge-session.cjs");

function updateBasedOn(text, sessionId, sessionText, now) {
  const marker = "## Based On\n";
  const start = text.indexOf(marker);
  if (start === -1) return text;

  const before = text.slice(0, start + marker.length);
  const rest = text.slice(start + marker.length);
  const nextSectionIndex = rest.search(/\n## /);
  let body = nextSectionIndex === -1 ? rest : rest.slice(0, nextSectionIndex);
  const tail = nextSectionIndex === -1 ? "" : rest.slice(nextSectionIndex);
  const resultLine = (section(sessionText, "Result").trim().split(/\r?\n/)[0] || `Merged session ${sessionId}`).trim();
  const lastChange = `${now} ${resultLine}`;

  if (/^- Session:\s*.*$/m.test(body)) {
    body = body.replace(/^- Session:\s*.*$/m, `- Session: ${sessionId}`);
  } else {
    body = `- Session: ${sessionId}\n${body}`;
  }

  if (/^- Last change:\s*.*$/m.test(body)) {
    body = body.replace(/^- Last change:\s*.*$/m, `- Last change: ${lastChange}`);
  } else if (/^Previous based-on:/m.test(body)) {
    body = body.replace(/^Previous based-on:/m, `- Last change: ${lastChange}\n\nPrevious based-on:`);
  } else {
    body = `${body.replace(/\s*$/, "")}\n- Last change: ${lastChange}\n`;
  }

  return `${before}${body}${tail}`;
}

const root = path.resolve(args._[0] || process.cwd());
const sessionId = required(args, "session", help);
const now = args.time || utcNow();
withMemoryLock(root, () => {
  let threads = readThreads(root);
  let sessionText = readSession(root, sessionId);
  const parent = extractField(sessionText, "Parent session") || "unknown";

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
    current = updateBasedOn(current, sessionId, sessionText, now);
    writeMemory(root, "CURRENT.md", current);
  }
});

if (!args["no-check"]) runCheck(root, __dirname);
console.log(sessionId);
