const fs = require("fs");
const path = require("path");

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

const BACKUP_DIR_NAME = ".backups";
const LOCK_DIR_NAME = ".weplaning.lock";

function writeFile(filePath, text) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const dir = path.dirname(filePath);
  const base = path.basename(filePath);
  const stamp = uniqueStamp();
  const tempPath = path.join(dir, `.${base}.${stamp}.tmp`);

  if (fs.existsSync(filePath)) {
    const backupDir = path.join(dir, BACKUP_DIR_NAME);
    fs.mkdirSync(backupDir, { recursive: true });
    fs.copyFileSync(filePath, path.join(backupDir, `${base}.${stamp}.bak`));
    cleanupBackups(backupDir, base, 10);
  }

  try {
    fs.writeFileSync(tempPath, normalizeNewlines(text), "utf8");
    fs.renameSync(tempPath, filePath);
  } catch (error) {
    if (fs.existsSync(tempPath)) fs.rmSync(tempPath, { force: true });
    throw error;
  }
}

function cleanupBackups(backupDir, base, keep) {
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

function readMemory(root, relativePath) {
  return fs.readFileSync(path.join(memoryDir(root), relativePath), "utf8");
}

function writeMemory(root, relativePath, text) {
  validateKnownMarkdown(relativePath, text);
  writeFile(path.join(memoryDir(root), relativePath), text);
}

function utcNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function uniqueStamp() {
  const compact = utcNow().replace(/[-:]/g, "");
  return `${compact}-${process.pid}-${Math.random().toString(36).slice(2, 8)}`;
}

function truncateSummary(text, max = 120) {
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

function section(text, heading) {
  const escaped = heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = normalizeNewlines(text).match(new RegExp(`^##[ \\t]+${escaped}[ \\t]*\\n([\\s\\S]*?)(?=\\n##[ \\t]+|$(?![\\s\\S]))`, "m"));
  return match ? match[1].trimEnd() : "";
}

/** Replace a `## heading` section body in place, or append the section when missing. */
function setSection(text, heading, value) {
  const pattern = new RegExp(`^##[ \\t]+${heading}[ \\t]*\\n[\\s\\S]*?(?=\\n##[ \\t]+|$(?![\\s\\S]))`, "m");
  if (pattern.test(text)) return text.replace(pattern, () => `## ${heading}\n${value}\n`);
  return `${text.trimEnd()}\n\n## ${heading}\n${value}\n`;
}

const SCHEMA_VERSION = "3.0";
const SCHEMA_PATTERN = /^(2\.(2|3)|3\.0)$/;

function hasSupportedSchema(text) {
  return SCHEMA_PATTERN.test(extractField(text, "Schema version") || "");
}

function markdownErrors(relativePath, text) {
  if (!["CURRENT.md", "CHANGES.md", "DECISIONS.md"].includes(relativePath)) return [];
  const errors = [];
  const normalized = normalizeNewlines(text);
  const schemas = normalized.match(/^Schema version:[^\n]*$/gm) || [];
  if (schemas.length !== 1 || !hasSupportedSchema(normalized)) {
    errors.push(`${relativePath} must have one supported schema version (2.2, 2.3, or 3.0)`);
  }
  if (/^<<<<<<<(?: |$)/m.test(normalized) || /^>>>>>>>(?: |$)/m.test(normalized) || /^=======[ \t]*$/m.test(normalized)) {
    errors.push(`${relativePath} contains merge conflict markers`);
  }
  if (relativePath === "CURRENT.md") {
    const required = ["Active Goal", "Current State", "Accepted Next Steps", "Open Blockers"];
    for (const heading of [...required, "Current Understanding", "Project Config", "Based On"]) {
      const count = (normalized.match(new RegExp(`^##[ \\t]+${heading}[ \\t]*$`, "gm")) || []).length;
      if (count > 1) errors.push(`CURRENT.md has duplicate section: ${heading}`);
      if (required.includes(heading) && (count !== 1 || !section(normalized, heading).trim())) {
        errors.push(`CURRENT.md missing or empty section: ${heading}`);
      }
    }
  }
  return errors;
}

function findMemoryConflicts(root) {
  const dir = memoryDir(root);
  const found = [];
  function walk(currentDir) {
    for (const entry of fs.readdirSync(currentDir, { withFileTypes: true })) {
      if (entry.name === BACKUP_DIR_NAME || entry.name === LOCK_DIR_NAME) continue;
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) walk(fullPath);
      else if (/\.sync-conflict-\d{8}-\d{6}/i.test(entry.name)) {
        found.push(path.relative(dir, fullPath).replace(/\\/g, "/"));
      }
    }
  }
  walk(dir);
  return found.sort();
}

const NO_BLOCKER = "none|no blockers?|unblocked|无阻塞|没有阻塞|暂无阻塞";

/** Structural consistency gate shared by check-memory.cjs and every write. */
function checkMemory(root, { audit = false } = {}) {
  const dir = memoryDir(root);
  const errors = [];
  const warnings = [];
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
    errors.push("Missing required directory: .agent-memory");
  } else {
    const conflicts = findMemoryConflicts(root);
    if (conflicts.length > 0) {
      const shown = conflicts.slice(0, 10).map((name) => `    .agent-memory/${name}`);
      if (conflicts.length > shown.length) shown.push(`    ... and ${conflicts.length - shown.length} more`);
      errors.push(
        `Sync conflict copies found in .agent-memory (${conflicts.length}). Memory diverged across devices.\n` +
          `${shown.join("\n")}\n` +
          `  Fix: compare each copy against the live file, merge anything worth keeping, then delete the copies.`,
      );
    }
  }
  for (const file of ["CURRENT.md", "CHANGES.md"]) {
    if (!fs.existsSync(path.join(dir, file))) errors.push(`Missing required file: .agent-memory/${file}`);
  }
  if (errors.length) return { errors, warnings };

  const current = readMemory(root, "CURRENT.md");
  errors.push(...markdownErrors("CURRENT.md", current), ...markdownErrors("CHANGES.md", readMemory(root, "CHANGES.md")));
  if (fs.existsSync(path.join(dir, "DECISIONS.md"))) {
    errors.push(...markdownErrors("DECISIONS.md", readMemory(root, "DECISIONS.md")));
  }
  if (audit && errors.length === 0) {
    const lines = section(current, "Open Blockers").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    const hasReal = lines.some((line) => !new RegExp(`^-?\\s*(${NO_BLOCKER}|unknown|unavailable)\\s*[。.]?$`, "i").test(line));
    const hasNone = lines.some((line) => new RegExp(`^-\\s*(${NO_BLOCKER})\\s*[。.]?$`, "i").test(line));
    if (hasReal && hasNone) warnings.push("CURRENT.md Open Blockers mixes a real blocker with a no-blocker bullet.");
    const longItems = current.split(/\r?\n/).filter((line) => /^\s*([-*]|\d+\.)\s/.test(line) && line.length > 300).length;
    if (longItems) warnings.push(`CURRENT.md has ${longItems} item(s) over 300 characters; keep one fact per item.`);
    const bytes = Buffer.byteLength(current);
    if (bytes > 8000) warnings.push(`CURRENT.md is ${bytes} bytes (over 8000); move history and snapshots to the ledger.`);
  }
  return { errors, warnings };
}

/** Run the gate in-process; on failure print the errors and exit 1. */
function runCheck(root, { quiet = false } = {}) {
  const { errors } = checkMemory(root);
  if (errors.length) {
    console.error("WePlaning memory check failed:");
    for (const error of errors) console.error(`- ${error}`);
    process.exit(1);
  }
  // Keep machine-readable primary output on stdout; check chatter goes to stderr.
  if (!quiet) console.error("WePlaning memory check passed.");
}

function isTrivialNote(text) {
  return /^(完成了|done|搞定|ok|okay|finished|complete)$/i.test(String(text || "").trim());
}

function formatSectionItems(value, { numbered = false, fallback = "- none" } = {}) {
  const items = toList(value);
  if (!items.length) return fallback;
  return items
    .map((item, index) => {
      const trimmed = String(item).trim();
      if (numbered) return `${index + 1}. ${trimmed.replace(/^(\d+\.|[-*])\s+/, "")}`;
      if (trimmed.startsWith("- ") || /^\d+\.\s/.test(trimmed)) return trimmed;
      return `- ${trimmed}`;
    })
    .join("\n");
}

function parseCurrentMd(text) {
  return {
    schemaVersion: extractField(text, "Schema version") || SCHEMA_VERSION,
    lastUpdated: extractField(text, "Last updated") || "unknown",
    activeGoal: section(text, "Active Goal") || "unknown",
    currentUnderstanding: section(text, "Current Understanding") || "unknown",
    currentState: section(text, "Current State") || "- unknown",
    acceptedNextSteps: section(text, "Accepted Next Steps") || "1. unknown",
    openBlockers: section(text, "Open Blockers") || "unknown",
    projectConfig: section(text, "Project Config") || "",
    basedOn: section(text, "Based On") || "- Last change: unknown",
  };
}

function renderCurrentMd(state) {
  const projectConfigBlock = state.projectConfig
    ? `\n## Project Config\n${state.projectConfig}\n`
    : "";
  return `# Current Mainline
Schema version: ${SCHEMA_VERSION}
Last updated: ${state.lastUpdated}

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

function validateKnownMarkdown(relativePath, text) {
  try {
    const errors = markdownErrors(relativePath, text);
    if (errors.length) throw new Error(errors.join("; "));
    if (relativePath === "CURRENT.md") {
      const before = parseCurrentMd(text);
      const after = parseCurrentMd(renderCurrentMd(before));
      for (const key of ["lastUpdated", "activeGoal", "currentUnderstanding", "currentState", "acceptedNextSteps", "openBlockers", "projectConfig", "basedOn"]) {
        if (before[key] !== after[key]) throw new Error(`CURRENT.md round-trip changed ${key}`);
      }
    }
  } catch (error) {
    throw new Error(`${relativePath} round-trip validation failed: ${error.message}`);
  }
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
  const dir = path.join(memoryDir(root), LOCK_DIR_NAME);
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
  try {
    return callback();
  } finally {
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

/** Print a stable result: JSON when --json, otherwise a single primary line on stdout. */
function emitResult(args, primaryLine, payload = {}) {
  if (args && args.json) {
    console.log(JSON.stringify({ ok: true, ...payload }));
    return;
  }
  console.log(primaryLine);
}

module.exports = {
  checkMemory,
  defaultAgent,
  detectProjectConfig,
  emitResult,
  findMemoryConflicts,
  formatSectionItems,
  hasSupportedSchema,
  isTrivialNote,
  parseArgs,
  parseCurrentMd,
  readMemory,
  renderCurrentMd,
  replaceField,
  required,
  runCheck,
  SCHEMA_VERSION,
  section,
  setSection,
  toList,
  truncateSummary,
  uniqueStamp,
  usage,
  utcNow,
  validateKnownMarkdown,
  withMemoryLock,
  writeMemory,
};
