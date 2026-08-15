#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const { emitResult, parseArgs, usage } = require("./weplaning-utils.cjs");

const help = `
Usage:
  node check-dirty.cjs <project-root> [options]

Reports workspace paths that look changed outside .agent-memory.
Uses git when available. Without git (ops-doc projects) it falls back to
comparing file mtimes against CURRENT.md "Last updated", which is exactly the
handoff reminder those projects would otherwise never get.

Options:
  --json      Machine-readable JSON on stdout
  --strict    Exit 1 when dirty paths are found
  --limit <N> Maximum paths to list in mtime mode (default: 50)
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
} else {
  const currentPath = path.join(root, ".agent-memory", "CURRENT.md");
  if (fs.existsSync(currentPath)) {
    mode = "mtime";
    const marker = (fs.readFileSync(currentPath, "utf8").match(/^Last updated:\s*(.+)$/m) || [])[1];
    const since = marker ? Date.parse(marker.trim()) : NaN;
    if (Number.isNaN(since)) {
      mode = "none";
    } else {
      const limit = Math.max(1, Number(args.limit || 50) || 50);
      const skip = new Set([".agent-memory", ".git", "node_modules", ".stversions", "dist", "build", "__pycache__"]);
      (function walk(dir, depth) {
        if (depth > 6 || dirty.length >= limit) return;
        let entries;
        try {
          entries = fs.readdirSync(dir, { withFileTypes: true });
        } catch {
          return;
        }
        for (const entry of entries) {
          if (dirty.length >= limit) return;
          if (skip.has(entry.name)) continue;
          const full = path.join(dir, entry.name);
          if (entry.isDirectory()) walk(full, depth + 1);
          else if (entry.isFile()) {
            try {
              if (fs.statSync(full).mtimeMs > since) dirty.push(path.relative(root, full).replace(/\\/g, "/"));
            } catch {
              // Unreadable file: nothing useful to report.
            }
          }
        }
      })(root, 0);
    }
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
        ? "No git repo and no CURRENT.md timestamp; dirty check skipped."
        : "Workspace clean (outside .agent-memory)."
      : `Workspace dirty (${dirty.length} path(s) changed since the last memory update). Consider weplaning-note before handoff.`,
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
