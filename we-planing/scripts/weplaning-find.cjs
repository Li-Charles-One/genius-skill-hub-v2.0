#!/usr/bin/env node
/**
 * weplaning-find.cjs — search the whole memory, including archived history
 *
 * Without this, anything rolled into archive/ is unreachable for an agent that
 * only reads CURRENT/THREADS/CHANGES.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const { parseArgs, usage } = require("./weplaning-utils.cjs");

const help = `
Usage:
  node weplaning-find.cjs <project-root> <query> [options]

Searches CURRENT.md, THREADS.md, CHANGES.md, DECISIONS.md, session files and
everything under archive/. Case-insensitive substring by default.

Options:
  --regex        Treat <query> as a regular expression
  --case         Case-sensitive match
  --limit <N>    Maximum matches to print (default: 40)
  --scope <s>    Restrict to: current|threads|changes|decisions|sessions|archive
  --json         Machine-readable JSON on stdout
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const query = args._[1];
usage(query !== undefined && query !== "", "Missing required positional argument: <query>", help);

const memDir = path.join(root, ".agent-memory");
if (!fs.existsSync(memDir)) {
  console.error(`No .agent-memory in ${root}`);
  process.exit(1);
}

const limit = Math.max(1, Number(args.limit || 40) || 40);
const scope = args.scope ? String(args.scope).toLowerCase() : null;

let matcher;
try {
  matcher = args.regex
    ? new RegExp(query, args.case ? "" : "i")
    : new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), args.case ? "" : "i");
} catch (error) {
  console.error(`Invalid pattern: ${error.message}`);
  process.exit(1);
}

function scopeOf(relativePath) {
  const normalized = relativePath.replace(/\\/g, "/");
  if (normalized.startsWith("archive/")) return "archive";
  if (normalized.startsWith("sessions/")) return "sessions";
  if (normalized === "CURRENT.md") return "current";
  if (normalized === "THREADS.md") return "threads";
  if (normalized === "CHANGES.md") return "changes";
  if (normalized === "DECISIONS.md") return "decisions";
  return "other";
}

function collectFiles(dir, found = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === ".backups" || entry.name === ".weplaning.lock") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) collectFiles(full, found);
    else if (entry.name.endsWith(".md")) found.push(full);
  }
  return found;
}

const matches = [];
let truncated = false;

for (const file of collectFiles(memDir).sort()) {
  const relativePath = path.relative(memDir, file).replace(/\\/g, "/");
  if (scope && scopeOf(relativePath) !== scope) continue;
  const lines = fs.readFileSync(file, "utf8").split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    if (!matcher.test(lines[index])) continue;
    if (matches.length >= limit) {
      truncated = true;
      break;
    }
    matches.push({
      file: relativePath,
      scope: scopeOf(relativePath),
      line: index + 1,
      text: lines[index].trim().slice(0, 400),
    });
  }
  if (truncated) break;
}

if (args.json) {
  console.log(JSON.stringify({ ok: true, query, count: matches.length, truncated, matches }));
  process.exit(0);
}

if (matches.length === 0) {
  console.log(`No match for ${JSON.stringify(query)} in .agent-memory${scope ? ` (scope ${scope})` : ""}.`);
  process.exit(0);
}

let lastFile = null;
for (const match of matches) {
  if (match.file !== lastFile) {
    console.log(`\n${match.file}`);
    lastFile = match.file;
  }
  console.log(`  ${String(match.line).padStart(4)}: ${match.text}`);
}
console.log(`\n${matches.length} match(es)${truncated ? ` (stopped at --limit ${limit})` : ""}.`);
