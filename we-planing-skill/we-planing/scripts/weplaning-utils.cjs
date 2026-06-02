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
  fs.writeFileSync(filePath, normalizeNewlines(text), "utf8");
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
  writeFile(memoryPath(root, relativePath), text);
  validateKnownMarkdown(relativePath, text);
}

function utcNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function compactTimestamp(iso) {
  return iso.replace(/[-:]/g, "").replace(".000", "");
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
        if (before[key] !== after[key]) console.warn(`Warning: CURRENT.md round-trip changed ${key}`);
      }
    } else if (relativePath.replace(/\\/g, "/").startsWith("sessions/")) {
      const before = parseSessionMd(text);
      const after = parseSessionMd(renderSessionMd(before));
      for (const key of ["sessionId", "agent", "role", "parentSession", "status"]) {
        if (before[key] !== after[key]) console.warn(`Warning: ${relativePath} round-trip changed ${key}`);
      }
    }
  } catch (error) {
    console.warn(`Warning: ${relativePath} round-trip validation failed: ${error.message}`);
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
  renderCurrentMd,
  renderSessionMd,
  replaceField,
  replaceOrAppendTableRow,
  required,
  runCheck,
  sessionPath,
  parseCurrentMd,
  parseSessionMd,
  toList,
  updateWePlaning,
  usage,
  utcNow,
  writeMemory,
  writeSession,
  writeThreads,
};
