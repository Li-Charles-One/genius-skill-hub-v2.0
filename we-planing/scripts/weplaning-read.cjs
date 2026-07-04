#!/usr/bin/env node
/**
 * weplaning-read.cjs — One-command session briefing
 *
 * Reads CURRENT.md + THREADS.md + CHANGES.md and outputs a concise
 * context briefing. Use at the start of every session instead of
 * reading three files manually.
 *
 * Usage:
 *   node weplaning-read.cjs <project-root>
 */

"use strict";

const fs = require("fs");
const path = require("path");
const {
  parseArgs,
  parseCurrentMd,
  parseThreads,
  readMemory,
  usage,
  utcNow,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node weplaning-read.cjs <project-root>
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const memDir = path.join(root, ".agent-memory");

// ── Read files ────────────────────────────────────────────────────────────────

const currentText = readMemory(root, "CURRENT.md");
const current = parseCurrentMd(currentText);

const threadsText = readMemory(root, "THREADS.md");
const threads = parseThreads(threadsText);

// CHANGES.md tail: last 25 non-empty lines
const changesPath = path.join(memDir, "CHANGES.md");
let changesTail = "(no changes yet)";
if (fs.existsSync(changesPath)) {
  const lines = fs.readFileSync(changesPath, "utf8").split("\n");
  const meaningful = lines.filter((l) => l.trim().length > 0).slice(-25);
  changesTail = meaningful.join("\n").trim() || "(empty)";
}

// ── Recent unmerged sessions (lite/closed, not merged) ────────────────────────
const unmerged = threads.rows
  .filter((r) => r.status !== "merged")
  .slice(-8)
  .reverse();

// ── Format output ─────────────────────────────────────────────────────────────
const D = "─".repeat(52);

let out = `\n${D}\n WePlaning · ${utcNow()}\n${D}\n`;

out += `\n📌 Goal:\n${current.activeGoal}\n`;
out += `\n📊 Current State:\n${current.currentState}\n`;
out += `\n✅ Next Steps:\n${current.acceptedNextSteps}\n`;

if (current.openBlockers && current.openBlockers.toLowerCase() !== "none") {
  out += `\n🚧 Blockers:\n${current.openBlockers}\n`;
}

if (unmerged.length > 0) {
  out += `\n🗒  Recent Unmerged Notes (${unmerged.length}):\n`;
  for (const row of unmerged) {
    out += `  [${row.status}] ${row.id}  ${row.summary}\n`;
  }
}

out += `\n📋 Recent Changes:\n${changesTail}\n`;
out += `\n${D}\n`;

process.stdout.write(out);
