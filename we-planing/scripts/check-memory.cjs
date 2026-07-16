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

if (!fs.existsSync(memoryDir) || !fs.statSync(memoryDir).isDirectory()) {
  fail("Missing required directory: .agent-memory");
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
    if (parent && !["root", "unknown"].includes(parent) && !rowIds.has(parent)) {
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
