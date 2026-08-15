#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const {
  allowNoCheck,
  emitResult,
  memoryPath,
  parseArgs,
  readThreads,
  runCheck,
  sessionPath,
  usage,
  utcNow,
  withMemoryLock,
  writeThreads,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node archive-threads.cjs <project-root> [options]

Moves finished session rows out of THREADS.md into .agent-memory/archive/,
together with their session files, keeping the newest N rows in the live tree.

Never archives the mainline row or anything still active/paused, so the
consistency gate keeps passing. Archived ids stay valid as parents because
check-memory also reads archive/THREADS-*.md.

Options:
  --keep <N>     Number of newest rows to keep in THREADS.md (default: 40)
  --dry-run      Print plan without writing
  --json         Machine-readable JSON on stdout
  --no-check     Internal use only; external callers must run consistency checks
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);
allowNoCheck(args, "archive-threads.cjs");

const root = path.resolve(args._[0] || process.cwd());
const keep = Math.max(1, Number(args.keep || 40) || 40);
const now = utcNow();

let archivedRows = [];
let archivePath = null;
let movedSessions = 0;

function archiveDir() {
  return memoryPath(root, "archive");
}

function totalArchivedRows() {
  if (!fs.existsSync(archiveDir())) return 0;
  return fs
    .readdirSync(archiveDir())
    .filter((name) => name.startsWith("THREADS-") && name.endsWith(".md"))
    .reduce((sum, name) => {
      const text = fs.readFileSync(path.join(archiveDir(), name), "utf8");
      return sum + (text.match(/^\| \S+ \|/gm) || []).length;
    }, 0);
}

withMemoryLock(root, () => {
  const threads = readThreads(root);
  const protectedIds = new Set([threads.mainline, threads.lastMerged].filter(Boolean));
  for (const row of threads.rows) {
    if (row.status === "active" || row.status === "paused") protectedIds.add(row.id);
  }

  const newest = new Set(threads.rows.slice(-keep).map((row) => row.id));
  archivedRows = threads.rows.filter((row) => !newest.has(row.id) && !protectedIds.has(row.id));
  if (archivedRows.length === 0) return;

  const stamp = now.replace(/[:.]/g, "").slice(0, 15);
  archivePath = path.join(archiveDir(), `THREADS-${stamp}.md`);
  if (args["dry-run"]) return;

  const table = [
    "| Session ID | Parent | Agent | OS | Role | Status | Summary |",
    "|:--|:--|:--|:--|:--|:--|:--|",
    ...archivedRows.map(
      (row) => `| ${row.id} | ${row.parent} | ${row.agent} | ${row.os} | ${row.role} | ${row.status} | ${row.summary} |`,
    ),
  ].join("\n");
  fs.mkdirSync(archiveDir(), { recursive: true });
  fs.writeFileSync(
    archivePath,
    `# Archived Threads\nSchema version: 2.3\nArchived at: ${now}\nSource: THREADS.md\nRows: ${archivedRows.length}\n\n## Session Tree\n\n${table}\n`,
    "utf8",
  );

  const sessionArchive = path.join(archiveDir(), "sessions");
  for (const row of archivedRows) {
    const from = sessionPath(root, row.id);
    if (!fs.existsSync(from)) continue;
    fs.mkdirSync(sessionArchive, { recursive: true });
    fs.renameSync(from, path.join(sessionArchive, `${row.id}.md`));
    movedSessions += 1;
  }

  const archivedIds = new Set(archivedRows.map((row) => row.id));
  threads.rows = threads.rows.filter((row) => !archivedIds.has(row.id));
  threads.archived = `${totalArchivedRows()} row(s) in archive/ (latest ${path.basename(archivePath)})`;
  writeThreads(root, threads, now);
});

if (!args["dry-run"] && archivedRows.length > 0 && !args["no-check"]) runCheck(root, __dirname);

const summary = archivedRows.length
  ? `${args["dry-run"] ? "Would archive" : "Archived"} ${archivedRows.length} row(s), moved ${movedSessions} session file(s)`
  : "Nothing to archive";

emitResult(args, summary, {
  dryRun: Boolean(args["dry-run"]),
  archived: archivedRows.length,
  movedSessions,
  archivePath: archivePath ? `archive/${path.basename(archivePath)}` : null,
});
