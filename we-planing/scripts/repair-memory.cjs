#!/usr/bin/env node

const path = require("path");
const fs = require("fs");
const {
  allowNoCheck,
  emitResult,
  extractField,
  parseArgs,
  readMemory,
  readSession,
  readThreads,
  renderSessionMd,
  replaceField,
  runCheck,
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
  - marks mainline thread row and session file as merged
  - aligns Last merged session with mainline
  - rebuilds missing mainline THREADS row or session file with minimal data
  - rebuilds any other session file listed in THREADS.md but missing on disk,
    carrying over the row's summary as the session goal and result

When CURRENT.md and THREADS.md mainline disagree, repair refuses to guess.
Pass --prefer current|threads to choose the authority.

Options:
  --prefer current|threads   Authority when mainline pointers disagree
  --dry-run                  Print intended repairs without writing
  --json                     Print machine-readable JSON result on stdout
  --no-check                 Internal use only; external callers must run consistency checks
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "repair-memory.cjs");

const prefer = args.prefer;
if (prefer && prefer !== "current" && prefer !== "threads") {
  usage(false, "--prefer must be 'current' or 'threads'", help);
}

const root = path.resolve(args._[0] || process.cwd());
const now = args.time || utcNow();
let repairs = [];
let targetMainline = null;

const SESSION_STATUSES = new Set(["active", "merged", "paused", "abandoned", "closed"]);

/** A THREADS row keeps the summary, so a lost session file can be rebuilt without inventing content. */
function reconstructFromRow(row, forcedStatus) {
  const stamp = row.id.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/);
  const started = stamp ? `${stamp[1]}-${stamp[2]}-${stamp[3]}T${stamp[4]}:${stamp[5]}:00Z` : "unknown";
  const summary = row.summary && row.summary !== "unknown"
    ? row.summary
    : "No summary was recorded in THREADS.md.";
  const status = forcedStatus || (SESSION_STATUSES.has(row.status) ? row.status : "closed");
  const open = status === "active" || status === "paused";
  return renderSessionMd({
    sessionId: row.id,
    agent: row.agent || "unknown",
    adapter: "unknown",
    os: row.os || "unknown",
    role: row.role || "unknown",
    parentSession: row.parent || "unknown",
    status,
    started,
    closed: open ? "unknown" : started,
    goal: summary,
    contextRead: "- Reconstructed by repair-memory.cjs from the THREADS.md row; the original session file was lost.",
    workNotes: `- ${summary}`,
    filesTouched: "- unknown (original session file was lost)",
    decisions: "- none recorded",
    result: summary,
    exactNextStep: "See CURRENT.md Accepted Next Steps.",
  });
}

withMemoryLock(root, () => {
  const current = readMemory(root, "CURRENT.md");
  const currentMainline = extractField(current, "Mainline session");
  if (!currentMainline) {
    console.error("CURRENT.md missing Mainline session; cannot repair automatically.");
    process.exit(1);
  }

  let threads = readThreads(root);
  const threadsMainline = threads.mainline;

  targetMainline = currentMainline;
  if (threadsMainline && threadsMainline !== currentMainline) {
    if (!prefer) {
      console.error(
        `Mainline mismatch: CURRENT.md=${currentMainline}, THREADS.md=${threadsMainline}\n` +
          "Refuse automatic repair (would risk inventing authority).\n" +
          "Re-run with --prefer current  (trust CURRENT.md, rewrite THREADS/session)\n" +
          "         or --prefer threads  (trust THREADS.md, rewrite CURRENT mainline).",
      );
      process.exit(1);
    }
    targetMainline = prefer === "threads" ? threadsMainline : currentMainline;
    repairs.push(`authority: prefer ${prefer} -> ${targetMainline}`);
  }

  if (prefer === "threads" && currentMainline !== targetMainline) {
    repairs.push(`CURRENT.md Mainline session: ${currentMainline} -> ${targetMainline}`);
    if (!args["dry-run"]) {
      let nextCurrent = replaceField(current, "Mainline session", targetMainline);
      nextCurrent = replaceField(nextCurrent, "Last updated", now);
      writeMemory(root, "CURRENT.md", nextCurrent);
    }
  }

  let row = threads.rows.find((item) => item.id === targetMainline);
  if (!row) {
    repairs.push(`THREADS.md add missing mainline row: ${targetMainline}`);
    row = {
      id: targetMainline,
      parent: "unknown",
      agent: "unknown",
      os: "unknown",
      role: "unknown",
      status: "merged",
      summary: "Reconstructed mainline session",
    };
    threads.rows.push(row);
  }

  if (threads.mainline !== targetMainline) {
    repairs.push(`THREADS.md Mainline session: ${threads.mainline} -> ${targetMainline}`);
    threads.mainline = targetMainline;
  }
  if (threads.lastMerged !== targetMainline) {
    repairs.push(`THREADS.md Last merged session: ${threads.lastMerged} -> ${targetMainline}`);
    threads.lastMerged = targetMainline;
  }
  if (row.status !== "merged") {
    repairs.push(`THREADS.md ${targetMainline} status: ${row.status} -> merged`);
    row.status = "merged";
  }

  let sessionText;
  const mainlineSessionPath = sessionPath(root, targetMainline);
  if (!fs.existsSync(mainlineSessionPath)) {
    repairs.push(`session ${targetMainline} rebuild missing mainline session file`);
    sessionText = reconstructFromRow(row, "merged");
  } else {
    sessionText = readSession(root, targetMainline);
  }
  const sessionStatus = extractField(sessionText, "Status");
  if (sessionStatus !== "merged") {
    repairs.push(`session ${targetMainline} Status: ${sessionStatus || "missing"} -> merged`);
    if (sessionStatus) {
      sessionText = replaceField(sessionText, "Status", "merged");
    } else {
      const parsed = {
        sessionId: targetMainline,
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
        filesTouched: `- .agent-memory/sessions/${targetMainline}.md`,
        decisions: "- unknown",
        result: "Session status repaired.",
        exactNextStep: "Review session metadata.",
      };
      sessionText = renderSessionMd(parsed);
    }
  }

  const orphanedRows = threads.rows.filter(
    (item) => item.id !== targetMainline && !fs.existsSync(sessionPath(root, item.id)),
  );
  for (const item of orphanedRows) {
    repairs.push(`session ${item.id} rebuild missing session file (${item.status || "unknown"})`);
  }

  if (args["dry-run"]) return;

  if (repairs.length > 0) {
    writeThreads(root, threads, now);
    writeSession(root, targetMainline, sessionText);
    for (const item of orphanedRows) {
      writeSession(root, item.id, reconstructFromRow(item));
    }
  }
});

if (args["dry-run"]) {
  if (args.json) {
    console.log(JSON.stringify({ ok: true, dryRun: true, repairs, mainline: targetMainline }));
  } else if (repairs.length === 0) {
    console.log("No repairs needed.");
  } else {
    repairs.forEach((item) => console.log(item));
  }
  process.exit(0);
}

if (!args["no-check"]) runCheck(root, __dirname);

if (args.json) {
  emitResult(args, repairs.length ? repairs.join("; ") : "No repairs needed.", {
    repairs,
    mainline: targetMainline,
    message: repairs.length ? `Applied ${repairs.length} repair(s).` : "No repairs needed.",
  });
} else if (repairs.length === 0) {
  console.log("No repairs needed.");
} else {
  repairs.forEach((item) => console.log(item));
}
