#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const { parseArgs, required, usage, withMemoryLock, writeFile } = require("./weplaning-utils.cjs");

const help = `
Usage:
  node safe-edit.cjs <project-root> --session <id> --changed <text> --file <path> --verification <text> [options]

Runs the full closeout pipeline with a snapshot rollback guard:
  sync-before-write -> check-memory(pre) -> pre-close-check -> append-change -> merge-session -> check-memory(post)

Options:
  --session <id>        Required. Session to close and merge.
  --changed <text>      Required. Change description (same as append-change.cjs).
  --file <path>         Required. Repeatable or ";;" separated. Files touched.
  --verification <text> Required. Repeatable or ";;" separated. Verification steps.
  --note <text>         Repeatable or ";;" separated. Notes.
  --no-merge            Skip merge-session step (only append change, no mainline update).
  --dry-run             Print steps without executing.
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const sessionId = required(args, "session", help);
const changed = required(args, "changed", help);
const files = args.file || args.files;
const verification = args.verification;

if (!files) {
  console.error("Missing required argument: --file");
  process.exit(1);
}
if (!verification) {
  console.error("Missing required argument: --verification");
  process.exit(1);
}

function listFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  const result = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) result.push(...listFiles(fullPath));
    else result.push(fullPath);
  }
  return result;
}

function createSnapshot() {
  const memoryDir = path.join(root, ".agent-memory");
  const contentByRelativePath = new Map();
  for (const filePath of listFiles(memoryDir)) {
    contentByRelativePath.set(path.relative(memoryDir, filePath), fs.readFileSync(filePath));
  }
  return { memoryDir, contentByRelativePath };
}

function restoreSnapshot(snapshot) {
  if (args["dry-run"]) return;
  fs.mkdirSync(snapshot.memoryDir, { recursive: true });
  for (const filePath of listFiles(snapshot.memoryDir)) {
    const relativePath = path.relative(snapshot.memoryDir, filePath);
    if (!snapshot.contentByRelativePath.has(relativePath)) fs.rmSync(filePath, { force: true });
  }
  for (const [relativePath, content] of snapshot.contentByRelativePath.entries()) {
    const filePath = path.join(snapshot.memoryDir, relativePath);
    writeFile(filePath, content.toString("utf8"));
  }
}

function values(value) {
  return Array.isArray(value) ? value : [value];
}

function runStep(label, command, argv) {
  if (args["dry-run"]) {
    console.log(`[DRY-RUN] ${label}: ${command} ${argv.join(" ")}`);
    return { ok: true };
  }
  console.error(`\n> ${label}`);
  const result = spawnSync(process.execPath, [command, ...argv], {
    cwd: root,
    env: { ...process.env, WEPLANING_INTERNAL_NO_CHECK: "1" },
    encoding: "utf8",
    timeout: 30_000,
  });
  if (result.stdout) process.stderr.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  const ok = result.status === 0;
  console.log(`${ok ? "OK" : "FAILED"} ${label}`);
  return { ok, status: result.status };
}

const scriptDir = __dirname;
let snapshot = null;

function abort(message) {
  console.error(message);
  if (snapshot) restoreSnapshot(snapshot);
  const check = spawnSync(process.execPath, [path.join(scriptDir, "check-memory.cjs"), root], {
    cwd: root,
    encoding: "utf8",
  });
  if (check.stdout) process.stderr.write(check.stdout);
  if (check.stderr) process.stderr.write(check.stderr);
  process.exit(1);
}

withMemoryLock(root, () => {
  snapshot = createSnapshot();

  const syncResult = runStep("sync-before-write", path.join(scriptDir, "sync-before-write.cjs"), [
    root,
    "--session", sessionId,
    "--no-check",
  ]);
  if (!syncResult.ok) abort("Pipeline aborted: sync-before-write failed.");

  const preCheckResult = runStep("check-memory (pre)", path.join(scriptDir, "check-memory.cjs"), [root]);
  if (!preCheckResult.ok) abort("Pipeline aborted: pre-check failed.");

  const preCloseResult = runStep("pre-close-check", path.join(scriptDir, "pre-close-check.cjs"), [
    root,
    "--session", sessionId,
    "--no-check",
  ]);
  if (!preCloseResult.ok) abort("Pipeline aborted: pre-close-check reported issues.");

  const appendArgv = [root, "--session", sessionId, "--changed", changed, "--no-check"];
  for (const file of values(files)) appendArgv.push("--file", file);
  for (const item of values(verification)) appendArgv.push("--verification", item);
  if (args.note) {
    for (const note of values(args.note)) appendArgv.push("--note", note);
  }

  const appendResult = runStep("append-change", path.join(scriptDir, "append-change.cjs"), appendArgv);
  if (!appendResult.ok) abort("Pipeline aborted: append-change failed.");

  if (!args["no-merge"]) {
    const mergeResult = runStep("merge-session", path.join(scriptDir, "merge-session.cjs"), [
      root,
      "--session", sessionId,
      "--no-check",
    ]);
    if (!mergeResult.ok) abort("Pipeline aborted: merge-session failed.");
  } else {
    console.log("SKIPPED merge-session (--no-merge)");
  }

  const postCheckResult = runStep("check-memory (post)", path.join(scriptDir, "check-memory.cjs"), [root]);
  if (!postCheckResult.ok) abort("Pipeline aborted: post-check failed. Snapshot was restored.");
});

console.log("safe-edit pipeline completed successfully.");
