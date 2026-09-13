#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { findMemoryConflicts, markdownErrors, parseArgs, section, usage } = require("./weplaning-utils.cjs");

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
} else {
  const conflicts = findMemoryConflicts(root);
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

  errors.push(...markdownErrors("CURRENT.md", current), ...markdownErrors("CHANGES.md", changes));

  const decisionsPath = path.join(memoryDir, "DECISIONS.md");
  if (fs.existsSync(decisionsPath)) {
    const decisions = readText("DECISIONS.md");
    errors.push(...markdownErrors("DECISIONS.md", decisions));
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
