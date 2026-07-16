#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const { emitResult, parseArgs, usage } = require("./weplaning-utils.cjs");

const help = `
Usage:
  node check-dirty.cjs <project-root> [options]

Reports workspace paths that look changed outside .agent-memory.
Uses git when available; otherwise exits cleanly with mode=none.

Options:
  --json      Machine-readable JSON on stdout
  --strict    Exit 1 when dirty paths are found
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const memPrefix = ".agent-memory";

function isMemoryPath(rel) {
  const normalized = rel.replace(/\\/g, "/").replace(/^\.\//, "");
  return normalized === memPrefix || normalized.startsWith(`${memPrefix}/`);
}

let mode = "none";
let dirty = [];

if (fs.existsSync(path.join(root, ".git"))) {
  mode = "git";
  const result = spawnSync("git", ["status", "--porcelain", "-uall"], {
    cwd: root,
    encoding: "utf8",
  });
  if (result.status === 0) {
    for (const line of (result.stdout || "").split(/\r?\n/)) {
      if (!line.trim()) continue;
      // porcelain: XY PATH or XY ORIG -> PATH
      const rel = line.slice(3).split(" -> ").pop().trim().replace(/^"|"$/g, "");
      if (!rel || isMemoryPath(rel)) continue;
      dirty.push(rel);
    }
  } else {
    mode = "git-error";
  }
}

const payload = {
  ok: true,
  mode,
  dirty,
  count: dirty.length,
  message:
    dirty.length === 0
      ? mode === "none"
        ? "No git repo; dirty check skipped."
        : "Workspace clean (outside .agent-memory)."
      : `Workspace dirty (${dirty.length} path(s) outside .agent-memory). Consider weplaning-note before handoff.`,
};

if (args.json) {
  console.log(JSON.stringify(payload));
} else {
  console.log(payload.message);
  if (dirty.length) {
    for (const item of dirty.slice(0, 30)) console.error(`- ${item}`);
    if (dirty.length > 30) console.error(`- … and ${dirty.length - 30} more`);
  }
}

if (args.strict && dirty.length > 0) process.exit(1);
process.exit(0);
