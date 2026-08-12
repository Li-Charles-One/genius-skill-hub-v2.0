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

const BACKUP_DIR_NAME = ".backups";
const LOCK_DIR_NAME = ".weplaning.lock";

/** Files that are themselves backups must never be backed up again — that is how .backups/.backups/ grows. */
function isTransientPath(filePath) {
  return path
    .resolve(filePath)
    .split(path.sep)
    .some((segment) => segment === BACKUP_DIR_NAME || segment === LOCK_DIR_NAME);
}

function writeFile(filePath, text) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const normalized = normalizeNewlines(text);
  const dir = path.dirname(filePath);
  const base = path.basename(filePath);
  const stamp = uniqueStamp();
  const tempPath = path.join(dir, `.${base}.${stamp}.tmp`);

  if (fs.existsSync(filePath) && !isTransientPath(filePath)) {
    const backupDir = path.join(dir, ".backups");
    fs.mkdirSync(backupDir, { recursive: true });
    fs.copyFileSync(filePath, path.join(backupDir, `${base}.${stamp}.bak`));
    cleanupBackups(backupDir, base, 10);
  }

  try {
    fs.writeFileSync(tempPath, normalized, "utf8");
    fs.renameSync(tempPath, filePath);
  } catch (error) {
    if (fs.existsSync(tempPath)) fs.rmSync(tempPath, { force: true });
    throw error;
  }
}

function cleanupBackups(backupDir, base, keep) {
  if (!fs.existsSync(backupDir)) return;
  const prefix = `${base}.`;
  const backups = fs
    .readdirSync(backupDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.startsWith(prefix) && entry.name.endsWith(".bak"))
    .map((entry) => {
      const fullPath = path.join(backupDir, entry.name);
      return { fullPath, mtimeMs: fs.statSync(fullPath).mtimeMs };
    })
    .sort((a, b) => b.mtimeMs - a.mtimeMs);
  for (const backup of backups.slice(keep)) {
    fs.rmSync(backup.fullPath, { force: true });
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

const SUMMARY_MAX_CHARS = 120;

function truncateSummary(text, max = SUMMARY_MAX_CHARS) {
  const oneLine = String(text || "").replace(/\s+/g, " ").trim();
  if (oneLine.length <= max) return oneLine;
  if (max <= 1) return "…";
  return `${oneLine.slice(0, max - 1).trimEnd()}…`;
}

function defaultAgent() {
  if (process.env.WEPLANING_AGENT) return process.env.WEPLANING_AGENT;
  if (process.env.CODEX_HOME || process.env.CODEX_CI) return "Codex";
  if (process.env.CLAUDE_CODE || process.env.CLAUDECODE) return "Claude";
  return "Agent";
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

function generateSessionId({ iso, agent, shortId }) {
  const timestamp = compactTimestamp(iso).replace(/(\d{8}T\d{4}).*/, "$1");
  return [timestamp, slug(agent) || "agent", slug(shortId) || randomShortId()].join("-");
}

function section(text, heading) {
  const escaped = heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = normalizeNewlines(text).match(new RegExp(`^## ${escaped}\\n([\\s\\S]*?)(?=\\n## |$(?![\\s\\S]))`, "m"));
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
    projectConfig: section(text, "Project Config") || "",
    basedOn: section(text, "Based On") || "- Session: unknown",
  };
}

function renderCurrentMd(state) {
  const projectConfigBlock = state.projectConfig
    ? `\n## Project Config\n${state.projectConfig}\n`
    : "";
  return `# Current Mainline
Schema version: 2.3
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
${projectConfigBlock}
## Based On
${state.basedOn}
`;
}

function detectProjectConfig(root, overrides = {}) {
  const codeExt = new Set([".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".rs", ".java", ".kt", ".cs", ".cpp", ".c", ".rb", ".php"]);
  const skip = new Set(["node_modules", ".git", ".agent-memory", "dist", "build", ".next", "vendor", "__pycache__"]);
  let hasCode = false;
  function walk(dir, depth) {
    if (hasCode || depth > 3) return;
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      if (entry.name.startsWith(".") && entry.name !== ".") continue;
      if (skip.has(entry.name)) continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full, depth + 1);
      else if (codeExt.has(path.extname(entry.name).toLowerCase())) {
        hasCode = true;
        return;
      }
    }
  }
  walk(root, 0);
  const hasGit = fs.existsSync(path.join(root, ".git"));
  const type = overrides.type || (hasCode ? "code" : "ops-doc");
  const codeVcs =
    overrides["code-vcs"] ||
    overrides.codeVcs ||
    (type === "code" ? (hasGit ? "git" : "none (recommend git)") : "n/a");
  const sync =
    overrides.sync ||
    (type === "code"
      ? "git for code; WePlaning owns .agent-memory state only"
      : "external sync optional (e.g. Syncthing); WePlaning standalone");
  return {
    type,
    codeVcs,
    sync,
    text: `- Type: ${type}\n- Code VCS: ${codeVcs}\n- Sync: ${sync}`,
  };
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

Schema version: 2.3
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
    } else if (relativePath === "THREADS.md") {
      const before = parseThreads(text);
      const after = parseThreads(renderThreads({ ...before, updated: "round-trip" }));
      if (before.mainline !== after.mainline) throw new Error("THREADS.md round-trip changed mainline");
      if (before.lastMerged !== after.lastMerged) throw new Error("THREADS.md round-trip changed lastMerged");
      if (before.rows.length !== after.rows.length) {
        throw new Error(`THREADS.md round-trip changed row count ${before.rows.length} -> ${after.rows.length}`);
      }
      for (let index = 0; index < before.rows.length; index += 1) {
        if (before.rows[index].id !== after.rows[index].id) {
          throw new Error(`THREADS.md round-trip changed row ${index} id`);
        }
        if (before.rows[index].status !== after.rows[index].status) {
          throw new Error(`THREADS.md round-trip changed status of ${before.rows[index].id}`);
        }
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

function isProcessAlive(pid) {
  if (!pid) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    // EPERM means the process exists but belongs to another user.
    return error.code === "EPERM";
  }
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
      const staleOwner = age > staleMs ? readJsonIfExists(ownerPath) : null;
      // Age alone is not enough: a slow but healthy pipeline would have its lock
      // stolen mid-write. Only reclaim when the recorded owner is really gone.
      if (age > staleMs && !isProcessAlive(staleOwner?.pid)) {
        try {
          fs.rmSync(dir, { recursive: true, force: true });
          console.error(`Removed stale WePlaning lock${staleOwner?.pid ? ` from dead pid ${staleOwner.pid}` : ""}.`);
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

  const releaseLock = () => {
    try {
      fs.rmSync(dir, { recursive: true, force: true });
    } catch {
      // Lock cleanup failure should not mask the original write result.
    }
  };
  // process.exit() skips finally blocks; the exit handler guarantees release.
  process.once("exit", releaseLock);

  const previousLock = process.env.WEPLANING_LOCK_HELD;
  process.env.WEPLANING_LOCK_HELD = lockKey;
  try {
    return callback();
  } finally {
    if (previousLock === undefined) delete process.env.WEPLANING_LOCK_HELD;
    else process.env.WEPLANING_LOCK_HELD = previousLock;
    process.removeListener("exit", releaseLock);
    releaseLock();
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
  const archived = extractField(text, "Archived rows");
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
      // A hand-edited or externally merged row may carry an unescaped "|", which splits
      // the summary into extra cells. Rejoin them so the tail is not dropped on re-render.
      summary: cells.slice(6).join(" | "),
    }));
  return { mainline, lastMerged, archived, rows };
}

function renderThreads({ updated, mainline, lastMerged, archived, rows }) {
  const lines = [
    "# Threads",
    "Schema version: 2.3",
    `Last updated: ${updated}`,
    "",
    `Mainline session: ${mainline}`,
    `Last merged session: ${lastMerged}`,
    ...(archived ? [`Archived rows: ${archived}`] : []),
    "",
    "## Session Tree",
    "",
    "| Session ID | Parent | Agent | OS | Role | Status | Summary |",
    "|:--|:--|:--|:--|:--|:--|:--|",
  ];
  for (const row of rows) {
    lines.push(
      `| ${sanitizeCell(row.id)} | ${sanitizeCell(row.parent)} | ${sanitizeCell(row.agent)} | ${sanitizeCell(row.os)} | ${sanitizeCell(row.role)} | ${sanitizeCell(row.status)} | ${sanitizeCell(truncateSummary(row.summary))} |`,
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
  // Keep machine-readable primary output on stdout; checks go to stderr.
  if (result.stdout) process.stderr.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.status !== 0) {
    process.exit(result.status || 1);
  }
}

/** Print a stable result: JSON when --json, otherwise a single primary line on stdout. */
function emitResult(args, primaryLine, payload = {}) {
  if (args && args.json) {
    console.log(JSON.stringify({ ok: true, ...payload }));
    return;
  }
  console.log(primaryLine);
}

module.exports = {
  activeCount,
  appendTableRow,
  allowNoCheck,
  BACKUP_DIR_NAME,
  compactTimestamp,
  defaultAgent,
  detectProjectConfig,
  emitResult,
  extractField,
  isTransientPath,
  LOCK_DIR_NAME,
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
  SUMMARY_MAX_CHARS,
  toList,
  truncateSummary,
  usage,
  utcNow,
  uniqueStamp,
  withMemoryLock,
  writeFile,
  writeMemory,
  writeSession,
  writeThreads,
};
