#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const root = process.argv[2] ? path.resolve(process.argv[2]) : process.cwd();
const memoryDir = path.join(root, ".agent-memory");

function readText(relativePath) {
  return fs.readFileSync(path.join(memoryDir, relativePath), "utf8");
}

function extractField(text, label) {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = text.match(new RegExp(`^${escaped}:\\s*(.+)$`, "m"));
  return match ? match[1].trim() : null;
}

function extractSnapshotValue(text, key) {
  const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = text.match(new RegExp(`^\\|\\s*${escaped}\\s*\\|\\s*([^|]+?)\\s*\\|`, "m"));
  return match ? match[1].trim() : null;
}

function parseThreadRows(text) {
  return text
    .split(/\r?\n/)
    .filter((line) => line.startsWith("| ") && !line.includes(":--"))
    .map((line) => line.split("|").slice(1, -1).map((cell) => cell.trim()))
    .filter((cells) => cells.length >= 7 && cells[0] !== "Session ID")
    .map((cells) => ({
      id: cells[0],
      parent: cells[1],
      agent: cells[2],
      os: cells[3],
      role: cells[4],
      status: cells[5],
      summary: cells[6],
    }));
}

const errors = [];
function fail(message) {
  errors.push(message);
}

for (const required of [
  "WePlaning.md",
  "CURRENT.md",
  "THREADS.md",
  "CHANGES.md",
  "TOOLS.md",
]) {
  const filePath = path.join(memoryDir, required);
  if (!fs.existsSync(filePath)) {
    fail(`Missing required file: .agent-memory/${required}`);
  }
}

const sessionsDir = path.join(memoryDir, "sessions");
if (!fs.existsSync(sessionsDir) || !fs.statSync(sessionsDir).isDirectory()) {
  fail("Missing required directory: .agent-memory/sessions");
}

if (errors.length === 0) {
  const current = readText("CURRENT.md");
  const threads = readText("THREADS.md");
  const weplaning = readText("WePlaning.md");

  for (const [name, text] of [
    ["WePlaning.md", weplaning],
    ["CURRENT.md", current],
    ["THREADS.md", threads],
    ["CHANGES.md", readText("CHANGES.md")],
    ["TOOLS.md", readText("TOOLS.md")],
  ]) {
    if (!/^Schema version:\s*2\.2$/m.test(text)) {
      fail(`${name} missing "Schema version: 2.2"`);
    }
  }

  const currentMainline = extractField(current, "Mainline session");
  const threadsMainline = extractField(threads, "Mainline session");
  const lastMerged = extractField(threads, "Last merged session");
  const snapshotMainline = extractSnapshotValue(weplaning, "Mainline session");
  const snapshotActive = extractSnapshotValue(weplaning, "Active sessions");
  const threadRows = parseThreadRows(threads);
  const mainlineRow = threadRows.find((row) => row.id === threadsMainline);
  const activeCount = threadRows.filter((row) => row.status === "active").length;

  if (!currentMainline) fail("CURRENT.md missing Mainline session");
  if (!threadsMainline) fail("THREADS.md missing Mainline session");
  if (currentMainline && threadsMainline && currentMainline !== threadsMainline) {
    fail(`Mainline mismatch: CURRENT.md=${currentMainline}, THREADS.md=${threadsMainline}`);
  }
  if (snapshotMainline && threadsMainline && snapshotMainline !== threadsMainline) {
    fail(`Snapshot mainline mismatch: WePlaning.md=${snapshotMainline}, THREADS.md=${threadsMainline}`);
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
  if (threadsMainline) {
    const sessionPath = path.join(sessionsDir, `${threadsMainline}.md`);
    if (!fs.existsSync(sessionPath)) {
      fail(`Mainline session file missing: .agent-memory/sessions/${threadsMainline}.md`);
    } else {
      const sessionText = fs.readFileSync(sessionPath, "utf8");
      if (!/^Schema version:\s*2\.2$/m.test(sessionText)) {
        fail(`Mainline session missing "Schema version: 2.2": ${threadsMainline}`);
      }
      const sessionStatus = extractField(sessionText, "Status");
      if (sessionStatus !== "merged") {
        fail(`Mainline session file must have Status: merged, got ${sessionStatus || "missing"}`);
      }
    }
  }
  if (snapshotActive !== null && Number(snapshotActive) !== activeCount) {
    fail(`Active session count mismatch: WePlaning.md=${snapshotActive}, THREADS.md=${activeCount}`);
  }
}

if (errors.length > 0) {
  console.error("WePlaning memory check failed:");
  for (const error of errors) console.error(`- ${error}`);
  process.exit(1);
}

console.log("WePlaning memory check passed.");
