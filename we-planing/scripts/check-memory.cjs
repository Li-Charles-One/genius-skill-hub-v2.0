#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const {
  extractField,
  parseArgs,
  parseThreads,
  readMemory,
  readSession,
  section,
  usage,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node check-memory.cjs <project-root> [--audit] [--strict]

Checks WePlaning v2.3 structural consistency.
  --audit    Add semantic warnings (placeholders, orphans, soft issues).
  --strict   With --audit: exit 1 when warnings exist (default: warnings exit 0).
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = args._[0] ? path.resolve(args._[0]) : process.cwd();
const memoryDir = path.join(root, ".agent-memory");
const errors = [];
const warnings = [];

function fail(message) {
  errors.push(message);
}

function warn(message) {
  warnings.push(message);
}

function readText(relativePath) {
  return fs.readFileSync(path.join(memoryDir, relativePath), "utf8");
}

function hasSchema(text, name) {
  if (!/^Schema version:\s*2\.(2|3)$/m.test(text)) fail(`${name} missing supported schema version 2.2 or 2.3`);
}

function hasConflictMarkers(text, name) {
  if (/^<<<<<<< /m.test(text) || /^>>>>>>> /m.test(text) || /^=======\s*$/m.test(text)) {
    fail(`${name} contains merge conflict markers`);
  }
}

function hasNoBlockerBullet(text) {
  return /^\s*-\s*(none|no blockers?|unblocked|无阻塞|没有阻塞|暂无阻塞)\s*[。.]?\s*$/im.test(text);
}

function hasRealBlocker(text) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return false;
  return lines.some((line) => !/^-?\s*(none|unknown|unavailable|no blockers?|unblocked|无阻塞|没有阻塞|暂无阻塞)\s*[。.]?$/i.test(line));
}

// Syncthing writes "<name>.sync-conflict-<date>-<time>-<device>.<ext>" when two devices
// edit the same file. Inside .agent-memory that means the mainline silently forked.
const CONFLICT_PATTERN = /\.sync-conflict-\d{8}-\d{6}/i;

function collectConflictCopies(dir, found) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return found;
  }
  for (const entry of entries) {
    if (entry.name === ".backups" || entry.name === ".weplaning.lock") continue;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) collectConflictCopies(fullPath, found);
    else if (CONFLICT_PATTERN.test(entry.name)) {
      found.push(path.relative(memoryDir, fullPath).replace(/\\/g, "/"));
    }
  }
  return found;
}

if (!fs.existsSync(memoryDir) || !fs.statSync(memoryDir).isDirectory()) {
  fail("Missing required directory: .agent-memory");
} else {
  const conflicts = collectConflictCopies(memoryDir, []).sort();
  if (conflicts.length > 0) {
    const shown = conflicts.slice(0, 10).map((name) => `    .agent-memory/${name}`);
    if (conflicts.length > shown.length) shown.push(`    ... and ${conflicts.length - shown.length} more`);
    fail(
      `Sync conflict copies found in .agent-memory (${conflicts.length}). Memory diverged across devices.\n` +
      `${shown.join("\n")}\n` +
      `  Fix: compare each copy against the live file, merge anything worth keeping, then delete the copies.`,
    );
  }
}

for (const required of ["CURRENT.md", "THREADS.md", "CHANGES.md"]) {
  const filePath = path.join(memoryDir, required);
  if (!fs.existsSync(filePath)) fail(`Missing required file: .agent-memory/${required}`);
}

const sessionsDir = path.join(memoryDir, "sessions");
if (!fs.existsSync(sessionsDir) || !fs.statSync(sessionsDir).isDirectory()) {
  fail("Missing required directory: .agent-memory/sessions");
}

if (errors.length === 0) {
  const current = readText("CURRENT.md");
  const threads = readText("THREADS.md");
  const changes = readText("CHANGES.md");

  hasSchema(current, "CURRENT.md");
  hasSchema(threads, "THREADS.md");
  hasSchema(changes, "CHANGES.md");
  hasConflictMarkers(current, "CURRENT.md");
  hasConflictMarkers(threads, "THREADS.md");
  hasConflictMarkers(changes, "CHANGES.md");

  const currentMainline = extractField(current, "Mainline session");
  const parsedThreads = parseThreads(threads);
  const threadsMainline = parsedThreads.mainline;
  const lastMerged = parsedThreads.lastMerged;
  const mainlineRow = parsedThreads.rows.find((row) => row.id === threadsMainline);
  const rowIds = new Set(parsedThreads.rows.map((row) => row.id));
  // Rows moved out by archive-threads stay valid ancestors of the rows still live.
  const archivedIds = new Set();
  const archiveDir = path.join(memoryDir, "archive");
  if (fs.existsSync(archiveDir)) {
    for (const name of fs.readdirSync(archiveDir)) {
      if (!name.startsWith("THREADS-") || !name.endsWith(".md")) continue;
      const text = fs.readFileSync(path.join(archiveDir, name), "utf8");
      for (const line of text.split(/\r?\n/)) {
        if (!line.startsWith("| ") || line.includes(":--")) continue;
        const id = line.split("|")[1].trim();
        if (id && id !== "Session ID") archivedIds.add(id);
      }
    }
  }

  if (!currentMainline) fail("CURRENT.md missing Mainline session");
  if (!threadsMainline) fail("THREADS.md missing Mainline session");
  if (currentMainline && threadsMainline && currentMainline !== threadsMainline) {
    fail(`Mainline mismatch: CURRENT.md=${currentMainline}, THREADS.md=${threadsMainline}`);
  }
  if (lastMerged && threadsMainline && lastMerged !== threadsMainline) {
    fail(`Last merged session mismatch: Last merged=${lastMerged}, Mainline=${threadsMainline}`);
  }
  if (!mainlineRow && threadsMainline) {
    fail(`Mainline session is not listed in THREADS.md: ${threadsMainline}`);
  }
  if (mainlineRow && mainlineRow.status !== "merged") {
    fail(`Mainline session must be merged, got ${mainlineRow.status}: ${threadsMainline}`);
  }

  for (const row of parsedThreads.rows) {
    const sessionFile = path.join(sessionsDir, `${row.id}.md`);
    if (!fs.existsSync(sessionFile)) {
      fail(`THREADS.md lists missing session file: .agent-memory/sessions/${row.id}.md`);
      continue;
    }
    const sessionText = fs.readFileSync(sessionFile, "utf8");
    hasConflictMarkers(sessionText, `sessions/${row.id}.md`);
    const parent = extractField(sessionText, "Parent session") || row.parent || "unknown";
    if (parent && !["root", "unknown"].includes(parent) && !rowIds.has(parent) && !archivedIds.has(parent)) {
      fail(`Session ${row.id} has unknown parent: ${parent}`);
    }
  }

  if (threadsMainline) {
    const sessionPath = path.join(sessionsDir, `${threadsMainline}.md`);
    if (!fs.existsSync(sessionPath)) {
      fail(`Mainline session file missing: .agent-memory/sessions/${threadsMainline}.md`);
    } else {
      const sessionText = fs.readFileSync(sessionPath, "utf8");
      hasSchema(sessionText, `sessions/${threadsMainline}.md`);
      const sessionStatus = extractField(sessionText, "Status");
      if (sessionStatus !== "merged") {
        fail(`Mainline session file must have Status: merged, got ${sessionStatus || "missing"}`);
      }
    }
  }

  // Orphans and soft issues: always collect when --audit, else skip.
  if (args.audit && errors.length === 0) {
    const sessionFiles = fs
      .readdirSync(sessionsDir, { withFileTypes: true })
      .filter((entry) => entry.isFile() && entry.name.endsWith(".md"))
      .map((entry) => entry.name.replace(/\.md$/, ""));

    for (const id of sessionFiles) {
      if (!rowIds.has(id)) {
        warn(`Orphan session file not listed in THREADS.md: sessions/${id}.md`);
      }
    }

    const openBlockers = section(current, "Open Blockers") || "";
    if (hasRealBlocker(openBlockers) && hasNoBlockerBullet(openBlockers)) {
      warn("CURRENT.md Open Blockers mixes a real blocker with a no-blocker bullet.");
    }

    const basedOnSession = (section(current, "Based On").match(/^- Session:\s*(.+)$/m) || [])[1]?.trim();
    if (basedOnSession && basedOnSession !== threadsMainline) {
      warn(`CURRENT.md Based On session (${basedOnSession}) differs from mainline (${threadsMainline}).`);
    }

    const mainlineSessionText = readSession(root, threadsMainline);
    const result = section(mainlineSessionText, "Result").trim();
    const nextStep = section(mainlineSessionText, "Exact Next Step").trim();
    if (/^(Session opened\.?|unknown)$/i.test(result)) {
      warn(`Mainline session ${threadsMainline} has placeholder Result: ${result || "empty"}.`);
    }
    if (/^unknown$/i.test(nextStep)) {
      warn(`Mainline session ${threadsMainline} has placeholder Exact Next Step.`);
    }
  }
}

if (errors.length > 0) {
  console.error("WePlaning memory check failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

for (const warning of warnings) console.error(`[audit] ${warning}`);

if (warnings.length > 0 && args.audit) {
  console.error(`WePlaning memory check passed with ${warnings.length} audit warning(s).`);
  if (args.strict) process.exit(1);
  process.exit(0);
}

console.log("WePlaning memory check passed.");
