#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { hasSupportedSchema, parseArgs, section, usage } = require("./weplaning-utils.cjs");

const help = `
Usage:
  node check-memory.cjs <project-root> [--audit] [--strict]

Checks WePlaning 3.0 structural consistency.
  --audit    Semantic warnings (mixed blockers). Exit 0 unless --strict.
  --strict   With --audit: exit 1 when warnings exist.
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

function hasHeading(text, heading) {
  return new RegExp(`^## ${heading}\\s*$`, "m").test(text);
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

for (const required of ["CURRENT.md", "CHANGES.md"]) {
  const filePath = path.join(memoryDir, required);
  if (!fs.existsSync(filePath)) fail(`Missing required file: .agent-memory/${required}`);
}

if (errors.length === 0) {
  const current = readText("CURRENT.md");
  const changes = readText("CHANGES.md");

  if (!hasSupportedSchema(current)) fail("CURRENT.md missing supported schema version 2.2, 2.3, or 3.0");
  if (!hasSupportedSchema(changes)) fail("CHANGES.md missing supported schema version 2.2, 2.3, or 3.0");
  hasConflictMarkers(current, "CURRENT.md");
  hasConflictMarkers(changes, "CHANGES.md");

  for (const heading of ["Active Goal", "Current State", "Accepted Next Steps", "Open Blockers"]) {
    if (!hasHeading(current, heading)) fail(`CURRENT.md missing section: ${heading}`);
  }

  const decisionsPath = path.join(memoryDir, "DECISIONS.md");
  if (fs.existsSync(decisionsPath)) {
    const decisions = readText("DECISIONS.md");
    if (!hasSupportedSchema(decisions)) fail("DECISIONS.md missing supported schema version 2.2, 2.3, or 3.0");
    hasConflictMarkers(decisions, "DECISIONS.md");
  }

  if (args.audit && errors.length === 0) {
    const openBlockers = section(current, "Open Blockers") || "";
    if (hasRealBlocker(openBlockers) && hasNoBlockerBullet(openBlockers)) {
      warn("CURRENT.md Open Blockers mixes a real blocker with a no-blocker bullet.");
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
