#!/usr/bin/env node

const path = require("path");
const fs = require("fs");
const {
  activeCount,
  allowNoCheck,
  extractField,
  parseArgs,
  readMemory,
  readSession,
  readThreads,
  renderSessionMd,
  replaceField,
  runCheck,
  updateWePlaning,
  usage,
  utcNow,
  withMemoryLock,
  writeMemory,
  writeSession,
  writeThreads,
  sessionPath,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node repair-memory.cjs <project-root> [options]

Repairs common WePlaning drift:
  - aligns THREADS.md mainline with CURRENT.md mainline
  - marks mainline thread row and session file as merged
  - aligns Last merged session with mainline
  - refreshes WePlaning.md snapshot mainline and active count
  - rebuilds missing mainline THREADS row or session file with minimal data

Options:
  --agent <name>    Agent name for WePlaning.md Last updated by. Default: Codex
  --dry-run         Print intended repairs without writing
  --no-check        Internal use only; external callers must run consistency checks
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "repair-memory.cjs");

const root = path.resolve(args._[0] || process.cwd());
const now = args.time || utcNow();
const agent = args.agent || "Codex";
let repairs = [];
withMemoryLock(root, () => {
  const current = readMemory(root, "CURRENT.md");
  const currentMainline = extractField(current, "Mainline session");
  if (!currentMainline) {
    console.error("CURRENT.md missing Mainline session; cannot repair automatically.");
    process.exit(1);
  }

  let threads = readThreads(root);
  let row = threads.rows.find((item) => item.id === currentMainline);
  if (!row) {
    repairs.push(`THREADS.md add missing mainline row: ${currentMainline}`);
    row = {
      id: currentMainline,
      parent: "unknown",
      agent: "unknown",
      os: "unknown",
      role: "unknown",
      status: "merged",
      summary: "Reconstructed mainline session",
    };
    threads.rows.push(row);
  }

  if (threads.mainline !== currentMainline) {
    repairs.push(`THREADS.md Mainline session: ${threads.mainline} -> ${currentMainline}`);
    threads.mainline = currentMainline;
  }
  if (threads.lastMerged !== currentMainline) {
    repairs.push(`THREADS.md Last merged session: ${threads.lastMerged} -> ${currentMainline}`);
    threads.lastMerged = currentMainline;
  }
  if (row.status !== "merged") {
    repairs.push(`THREADS.md ${currentMainline} status: ${row.status} -> merged`);
    row.status = "merged";
  }

  let sessionText;
  const mainlineSessionPath = sessionPath(root, currentMainline);
  if (!fs.existsSync(mainlineSessionPath)) {
    console.error(`Mainline session file missing: .agent-memory/sessions/${currentMainline}.md`);
    console.error("Refusing automatic repair because CURRENT.md may point at a ghost session. Restore the session file or choose the correct mainline manually.");
    process.exit(1);
  } else {
    sessionText = readSession(root, currentMainline);
  }
  const sessionStatus = extractField(sessionText, "Status");
  if (sessionStatus !== "merged") {
    repairs.push(`session ${currentMainline} Status: ${sessionStatus || "missing"} -> merged`);
    if (sessionStatus) {
      sessionText = replaceField(sessionText, "Status", "merged");
    } else {
      const parsed = {
        sessionId: currentMainline,
        agent: row.agent || "unknown",
        adapter: "unknown",
        os: row.os || "unknown",
        role: row.role || "unknown",
        parentSession: row.parent || "unknown",
        status: "merged",
        started: "unknown",
        closed: now,
        goal: "Reconstructed missing mainline session status.",
        contextRead: "- unknown",
        workNotes: "- Repaired by repair-memory.cjs.",
        filesTouched: `- .agent-memory/sessions/${currentMainline}.md`,
        decisions: "- unknown",
        result: "Session status repaired.",
        exactNextStep: "Review session metadata.",
      };
      sessionText = renderSessionMd(parsed);
    }
  }

  if (args["dry-run"]) return;

  if (repairs.length > 0) {
    writeThreads(root, threads, now);
    writeSession(root, currentMainline, sessionText);
  }

  updateWePlaning(root, {
    updated: now,
    updatedBy: agent,
    mainline: threads.mainline,
    lastClosed: threads.lastMerged,
    activeSessions: activeCount(threads.rows),
  });
});

if (args["dry-run"]) {
  if (repairs.length === 0) console.log("No repairs needed.");
  else repairs.forEach((item) => console.log(item));
  process.exit(0);
}

if (!args["no-check"]) runCheck(root, __dirname);
if (repairs.length === 0) console.log("No repairs needed.");
else repairs.forEach((item) => console.log(item));
