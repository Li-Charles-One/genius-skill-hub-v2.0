const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

function parseArgs(argv) {
  const args = { _: [] };
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (!item.startsWith("--")) {
      args._.push(item);
      continue;
    }
    const eq = item.indexOf("=");
    const key = item.slice(2, eq === -1 ? undefined : eq);
    let value = eq === -1 ? undefined : item.slice(eq + 1);
    if (value === undefined) {
      const next = argv[index + 1];
      if (next && !next.startsWith("--")) {
        value = next;
        index += 1;
      } else {
        value = true;
      }
    }
    if (args[key] === undefined) args[key] = value;
    else if (Array.isArray(args[key])) args[key].push(value);
    else args[key] = [args[key], value];
  }
  return args;
}

function usage(condition, message, text) {
  if (condition) return;
  if (message) console.error(message);
  console.error(text.trim());
  process.exit(message ? 1 : 0);
}

function required(args, key, help) {
  const value = args[key];
  if (value === undefined || value === true || value === "") {
    console.error(`Missing required argument: --${key}`);
    console.error(help.trim());
    process.exit(1);
  }
  return value;
}

function toList(value) {
  if (value === undefined || value === true || value === "") return [];
  const values = Array.isArray(value) ? value : [value];
  return values.flatMap((entry) =>
    String(entry)
      .split(";;")
      .map((item) => item.trim())
      .filter(Boolean),
  );
}

function normalizeNewlines(text) {
  return text.replace(/\r?\n/g, "\n");
}

function readFile(filePath) {
  return fs.readFileSync(filePath, "utf8");
}

function writeFile(filePath, text) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const normalized = normalizeNewlines(text);
  const dir = path.dirname(filePath);
  const base = path.basename(filePath);
  const stamp = uniqueStamp();
  const tempPath = path.join(dir, `.${base}.${stamp}.tmp`);

  if (fs.existsSync(filePath)) {
    const backupDir = path.join(dir, ".backups");
    fs.mkdirSync(backupDir, { recursive: true });
    fs.copyFileSync(filePath, path.join(backupDir, `${base}.${stamp}.bak`));
  }

  try {
    fs.writeFileSync(tempPath, normalized, "utf8");
    fs.renameSync(tempPath, filePath);
  } catch (error) {
    if (fs.existsSync(tempPath)) fs.rmSync(tempPath, { force: true });
    throw error;
  }
}

function memoryDir(root) {
  return path.join(root, ".agent-memory");
}

function memoryPath(root, relativePath) {
  return path.join(memoryDir(root), relativePath);
}

function readMemory(root, relativePath) {
  return readFile(memoryPath(root, relativePath));
}

function writeMemory(root, relativePath, text) {
  validateKnownMarkdown(relativePath, text);
  writeFile(memoryPath(root, relativePath), text);
}

function utcNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function compactTimestamp(iso) {
  return iso.replace(/[-:]/g, "").replace(".000", "");
}

function uniqueStamp() {
  return `${compactTimestamp(utcNow())}-${process.pid}-${Math.random().toString(36).slice(2, 8)}`;
}

function osToken(value) {
  const raw = String(value || process.platform).toLowerCase();
  if (raw.startsWith("win")) return "win";
  if (raw.includes("darwin") || raw.includes("mac")) return "mac";
  if (raw.includes("linux")) return "linux";
  return slug(raw) || "os";
}

function slug(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 32);
}

function randomShortId() {
  return Math.random().toString(36).slice(2, 6);
}

function generateSessionId({ iso, agent, os, role, shortId }) {
  return [
    compactTimestamp(iso),
    slug(agent) || "agent",
    osToken(os),
    slug(role) || "other",
    slug(shortId) || randomShortId(),
  ].join("-");
}

function section(text, heading) {
  const escaped = heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = normalizeNewlines(text).match(new RegExp(`^## ${escaped}\\n([\\s\\S]*?)(?=\\n## |$)`, "m"));
  return match ? match[1].trimEnd() : "";
}

function parseCurrentMd(text) {
  return {
    lastUpdated: extractField(text, "Last updated") || "unknown",
    mainlineSession: extractField(text, "Mainline session") || "unknown",
    activeGoal: section(text, "Active Goal") || "unknown",
    currentUnderstanding: section(text, "Current Understanding") || "unknown",
    currentState: section(text, "Current State") || "- unknown",
    acceptedNextSteps: section(text, "Accepted Next Steps") || "1. unknown",
    openBlockers: section(text, "Open Blockers") || "unknown",
    basedOn: section(text, "Based On") || "- Session: unknown",
  };
}

function renderCurrentMd(state) {
  return `# Current Mainline
Schema version: 2.2
Last updated: ${state.lastUpdated}
Mainline session: ${state.mainlineSession}

## Active Goal
${state.activeGoal}

## Current Understanding
${state.currentUnderstanding}

## Current State
${state.currentState}

## Accepted Next Steps
${state.acceptedNextSteps}

## Open Blockers
${state.openBlockers}

## Based On
${state.basedOn}
`;
}

function parseSessionMd(text) {
  return {
    sessionId: extractField(text, "Session ID") || "unknown",
    agent: extractField(text, "Agent") || "unknown",
    adapter: extractField(text, "Adapter") || "unknown",
    os: extractField(text, "OS") || "unknown",
    role: extractField(text, "Role") || "unknown",
    parentSession: extractField(text, "Parent session") || "unknown",
    status: extractField(text, "Status") || "unknown",
    started: extractField(text, "Started") || "unknown",
    closed: extractField(text, "Closed") || "unknown",
    goal: section(text, "Goal") || "unknown",
    contextRead: section(text, "Context Read") || "- unknown",
    workNotes: section(text, "Work Notes") || "- unknown",
    filesTouched: section(text, "Files Touched") || "- unknown",
    decisions: section(text, "Decisions") || "- none yet",
    result: section(text, "Result") || "unknown",
    exactNextStep: section(text, "Exact Next Step") || "unknown",
  };
}

function renderSessionMd(state) {
  return `# Session ${state.sessionId}

Schema version: 2.2
Session ID: ${state.sessionId}
Agent: ${state.agent}
Adapter: ${state.adapter}
OS: ${state.os}
Role: ${state.role}
Parent session: ${state.parentSession}
Status: ${state.status}
Started: ${state.started}
Closed: ${state.closed}

## Goal
${state.goal}

## Context Read
${state.contextRead}

## Work Notes
${state.workNotes}

## Files Touched
${state.filesTouched}

## Decisions
${state.decisions}

## Result
${state.result}

## Exact Next Step
${state.exactNextStep}
`;
}

function validateKnownMarkdown(relativePath, text) {
  try {
    if (relativePath === "CURRENT.md") {
      const before = parseCurrentMd(text);
      const after = parseCurrentMd(renderCurrentMd(before));
      for (const key of ["lastUpdated", "mainlineSession", "activeGoal"]) {
        if (before[key] !== after[key]) throw new Error(`CURRENT.md round-trip changed ${key}`);
      }
    } else if (relativePath.replace(/\\/g, "/").startsWith("sessions/")) {
      const before = parseSessionMd(text);
      const after = parseSessionMd(renderSessionMd(before));
      for (const key of ["sessionId", "agent", "role", "parentSession", "status"]) {
        if (before[key] !== after[key]) throw new Error(`${relativePath} round-trip changed ${key}`);
      }
    }
  } catch (error) {
    throw new Error(`${relativePath} round-trip validation failed: ${error.message}`);
  }
}

function allowNoCheck(args, scriptName) {
  if (!args["no-check"]) return;
  if (process.env.WEPLANING_INTERNAL_NO_CHECK === "1") return;
  console.error(`${scriptName}: --no-check is internal-only. Run check-memory.cjs after writes instead.`);
  process.exit(1);
}

function sleepSync(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function readJsonIfExists(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function withMemoryLock(root, callback, options = {}) {
  const lockKey = path.resolve(memoryDir(root));
  if (process.env.WEPLANING_LOCK_HELD === lockKey) return callback();

  const dir = path.join(memoryDir(root), ".weplaning.lock");
  const ownerPath = path.join(dir, "owner.json");
  const timeoutMs = Number(options.timeoutMs || process.env.WEPLANING_LOCK_TIMEOUT_MS || 30_000);
  const staleMs = Number(options.staleMs || process.env.WEPLANING_LOCK_STALE_MS || 120_000);
  const started = Date.now();
  const owner = {
    pid: process.pid,
    command: path.basename(process.argv[1] || "node"),
    started: utcNow(),
  };

  while (true) {
    try {
      fs.mkdirSync(dir);
      fs.writeFileSync(ownerPath, `${JSON.stringify(owner, null, 2)}\n`, "utf8");
      break;
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      let age = 0;
      try {
        age = Date.now() - fs.statSync(dir).mtimeMs;
      } catch {
        age = staleMs + 1;
      }
      if (age > staleMs) {
        const staleOwner = readJsonIfExists(ownerPath);
        try {
          fs.rmSync(dir, { recursive: true, force: true });
          console.error(`Removed stale WePlaning lock${staleOwner?.pid ? ` from pid ${staleOwner.pid}` : ""}.`);
          continue;
        } catch {
          // Another process may have removed it. Retry until timeout.
        }
      }
      if (Date.now() - started > timeoutMs) {
        const currentOwner = readJsonIfExists(ownerPath);
        throw new Error(`Timed out waiting for WePlaning lock${currentOwner?.pid ? ` held by pid ${currentOwner.pid}` : ""}.`);
      }
      sleepSync(50 + Math.floor(Math.random() * 75));
    }
  }

  const previousLock = process.env.WEPLANING_LOCK_HELD;
  process.env.WEPLANING_LOCK_HELD = lockKey;
  try {
    return callback();
  } finally {
    if (previousLock === undefined) delete process.env.WEPLANING_LOCK_HELD;
    else process.env.WEPLANING_LOCK_HELD = previousLock;
    try {
      fs.rmSync(dir, { recursive: true, force: true });
    } catch {
      // Lock cleanup failure should not mask the original write result.
    }
  }
}

function extractField(text, label) {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = text.match(new RegExp(`^${escaped}:\\s*(.+)$`, "m"));
  return match ? match[1].trim() : null;
}

function replaceField(text, label, value) {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(`^${escaped}:\\s*.*$`, "m");
  if (!pattern.test(text)) {
    throw new Error(`Missing field "${label}"`);
  }
  return text.replace(pattern, `${label}: ${value}`);
}

function replaceSnapshotValue(text, key, value) {
  const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(`^(\\|\\s*${escaped}\\s*\\|\\s*)[^|]+?(\\s*\\|)$`, "m");
  if (!pattern.test(text)) {
    throw new Error(`Missing snapshot key "${key}"`);
  }
  return text.replace(pattern, `$1${value}$2`);
}

function sanitizeCell(value) {
  return String(value || "unknown").replace(/\|/g, "/").replace(/\r?\n/g, " ").trim();
}

function appendTableRow(text, heading, rowCells) {
  const lines = normalizeNewlines(text).split("\n");
  const headingIndex = lines.findIndex((line) => line.trim() === heading);
  if (headingIndex === -1) {
    throw new Error(`Missing heading: ${heading}`);
  }
  let insertIndex = headingIndex + 1;
  while (insertIndex < lines.length && lines[insertIndex].trim() === "") {
    insertIndex += 1;
  }
  while (insertIndex < lines.length && lines[insertIndex].startsWith("|")) {
    insertIndex += 1;
  }
  lines.splice(insertIndex, 0, `| ${rowCells.map(sanitizeCell).join(" | ")} |`);
  return `${lines.join("\n").replace(/\n+$/, "")}\n`;
}

function replaceOrAppendTableRow(text, heading, keyValue, rowCells) {
  const lines = normalizeNewlines(text).split("\n");
  const headingIndex = lines.findIndex((line) => line.trim() === heading);
  if (headingIndex === -1) {
    throw new Error(`Missing heading: ${heading}`);
  }
  let index = headingIndex + 1;
  while (index < lines.length && lines[index].trim() === "") index += 1;
  while (index < lines.length && lines[index].startsWith("|")) {
    const cells = lines[index].split("|").slice(1, -1).map((cell) => cell.trim());
    if (cells[0] === keyValue) {
      lines[index] = `| ${rowCells.map(sanitizeCell).join(" | ")} |`;
      return `${lines.join("\n").replace(/\n+$/, "")}\n`;
    }
    index += 1;
  }
  lines.splice(index, 0, `| ${rowCells.map(sanitizeCell).join(" | ")} |`);
  return `${lines.join("\n").replace(/\n+$/, "")}\n`;
}

function parseThreads(text) {
  const mainline = extractField(text, "Mainline session");
  const lastMerged = extractField(text, "Last merged session");
  const rows = text
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
  return { mainline, lastMerged, rows };
}

function renderThreads({ updated, mainline, lastMerged, rows }) {
  const lines = [
    "# Threads",
    "Schema version: 2.2",
    `Last updated: ${updated}`,
    "",
    `Mainline session: ${mainline}`,
    `Last merged session: ${lastMerged}`,
    "",
    "## Session Tree",
    "",
    "| Session ID | Parent | Agent | OS | Role | Status | Summary |",
    "|:--|:--|:--|:--|:--|:--|:--|",
  ];
  for (const row of rows) {
    lines.push(
      `| ${sanitizeCell(row.id)} | ${sanitizeCell(row.parent)} | ${sanitizeCell(row.agent)} | ${sanitizeCell(row.os)} | ${sanitizeCell(row.role)} | ${sanitizeCell(row.status)} | ${sanitizeCell(row.summary)} |`,
    );
  }
  return `${lines.join("\n")}\n`;
}

function readThreads(root) {
  return parseThreads(readMemory(root, "THREADS.md"));
}

function writeThreads(root, threads, updated) {
  writeMemory(root, "THREADS.md", renderThreads({ ...threads, updated }));
}

function activeCount(rows) {
  return rows.filter((row) => row.status === "active").length;
}

function updateWePlaning(root, values) {
  let text = readMemory(root, "WePlaning.md");
  if (values.updated) text = replaceField(text, "Last updated", values.updated);
  if (values.updatedBy) text = replaceField(text, "Last updated by", values.updatedBy);
  if (values.mainline) text = replaceSnapshotValue(text, "Mainline session", values.mainline);
  if (values.lastClosed) text = replaceSnapshotValue(text, "Last closed session", values.lastClosed);
  if (values.activeSessions !== undefined) {
    text = replaceSnapshotValue(text, "Active sessions", String(values.activeSessions));
  }
  if (values.blocker !== undefined) text = replaceSnapshotValue(text, "Blocker", values.blocker);
  writeMemory(root, "WePlaning.md", text);
}

function sessionPath(root, sessionId) {
  return memoryPath(root, path.join("sessions", `${sessionId}.md`));
}

function readSession(root, sessionId) {
  return readFile(sessionPath(root, sessionId));
}

function writeSession(root, sessionId, text) {
  const relativePath = path.join("sessions", `${sessionId}.md`);
  writeMemory(root, relativePath, text);
}

function runCheck(root, scriptDir) {
  const checker = path.join(scriptDir, "check-memory.cjs");
  const result = spawnSync(process.execPath, [checker, root], {
    cwd: root,
    encoding: "utf8",
  });
  if (result.stdout) process.stderr.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}

module.exports = {
  activeCount,
  appendTableRow,
  allowNoCheck,
  compactTimestamp,
  extractField,
  generateSessionId,
  memoryPath,
  normalizeNewlines,
  osToken,
  parseArgs,
  readMemory,
  readSession,
  readThreads,
  parseThreads,
  renderCurrentMd,
  renderSessionMd,
  replaceField,
  replaceOrAppendTableRow,
  required,
  runCheck,
  section,
  sessionPath,
  parseCurrentMd,
  parseSessionMd,
  toList,
  updateWePlaning,
  usage,
  utcNow,
  uniqueStamp,
  withMemoryLock,
  writeFile,
  writeMemory,
  writeSession,
  writeThreads,
};
