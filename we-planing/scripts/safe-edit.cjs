#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");
const {
  extractField,
  parseArgs,
  readMemory,
  readSession,
  readThreads,
  required,
  usage,
  withMemoryLock,
  writeFile,
  writeSession,
} = require("./weplaning-utils.cjs");

const help = `
Usage:
  node safe-edit.cjs <project-root> --lite --session <id> [options]
  node safe-edit.cjs <project-root> --close --session <id> --changed <text> --file <path> --verification <text> [options]

Modes:
  --lite              Guard a lightweight session update with pre/post checks.
  --close             Append change, merge session, then run the consistency gate.

Options:
  --session <id>        Required session id.
  --changed <text>      Required with --close. Change description.
  --file <path>         Required with --close. Repeatable or ";;" separated.
  --verification <text> Required with --close. Repeatable or ";;" separated.
  --note <text>         Repeatable or ";;" separated. Notes for append-change.
  --dry-run             Print steps without executing.
`;

const args = parseArgs(process.argv.slice(2));
usage(!args.help, "", help);

const root = path.resolve(args._[0] || process.cwd());
const sessionId = required(args, "session", help);
const mode = args.close ? "close" : "lite";
usage(args.lite || args.close, "Choose exactly one mode: --lite or --close", help);
usage(!(args.lite && args.close), "Choose only one mode: --lite or --close", help);

if (mode === "close") {
  required(args, "changed", help);
  if (!(args.file || args.files)) usage(false, "Missing required argument: --file", help);
  if (!args.verification) usage(false, "Missing required argument: --verification", help);
} else {
  required(args, "changed", help);
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
  const newFiles = [];
  for (const filePath of listFiles(snapshot.memoryDir)) {
    const relativePath = path.relative(snapshot.memoryDir, filePath);
    if (!snapshot.contentByRelativePath.has(relativePath)) newFiles.push(relativePath);
  }
  for (const [relativePath, content] of snapshot.contentByRelativePath.entries()) {
    writeFile(path.join(snapshot.memoryDir, relativePath), content.toString("utf8"));
  }
  if (newFiles.length) {
    console.error("Left new files untouched after rollback:");
    for (const file of newFiles) console.error(`- .agent-memory/${file.replace(/\\/g, "/")}`);
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

function ensureFreshMainline() {
  const threads = readThreads(root);
  const currentMainline = extractField(readMemory(root, "CURRENT.md"), "Mainline session");
  if (currentMainline !== threads.mainline) {
    throw new Error(`Mainline mismatch before write: CURRENT.md=${currentMainline}, THREADS.md=${threads.mainline}`);
  }
  const sessionText = readSession(root, sessionId);
  const parent = extractField(sessionText, "Parent session");
  if (parent && parent !== threads.mainline && sessionId !== threads.mainline) {
    throw new Error(`Stale write blocked: parent=${parent}, current mainline=${threads.mainline}`);
  }
}

function appendToSection(text, heading, line) {
  const marker = `## ${heading}\n`;
  const start = text.indexOf(marker);
  if (start === -1) throw new Error(`Missing section: ${heading}`);
  const bodyStart = start + marker.length;
  const rest = text.slice(bodyStart);
  const nextIndex = rest.search(/\n## /);
  const body = nextIndex === -1 ? rest : rest.slice(0, nextIndex);
  const tail = nextIndex === -1 ? "" : rest.slice(nextIndex);
  return `${text.slice(0, bodyStart)}${body.replace(/\s*$/, "")}\n- ${line}\n${tail}`;
}

function updateLiteSession() {
  const sessionText = readSession(root, sessionId);
  writeSession(root, sessionId, appendToSection(sessionText, "Work Notes", args.changed));
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

  try {
    ensureFreshMainline();
  } catch (error) {
    abort(error.message);
  }

  const preCheckResult = runStep("check-memory (pre)", path.join(scriptDir, "check-memory.cjs"), [root]);
  if (!preCheckResult.ok) abort("Pipeline aborted: pre-check failed.");

  if (mode === "lite") {
    try {
      if (!args["dry-run"]) updateLiteSession();
      else console.log(`[DRY-RUN] append session Work Notes: ${args.changed}`);
    } catch (error) {
      abort(`Pipeline aborted: lite session update failed: ${error.message}`);
    }
  } else {
    const appendArgv = [root, "--session", sessionId, "--changed", args.changed, "--no-check"];
    for (const file of values(args.file || args.files)) appendArgv.push("--file", file);
    for (const item of values(args.verification)) appendArgv.push("--verification", item);
    if (args.note) for (const note of values(args.note)) appendArgv.push("--note", note);

    const appendResult = runStep("append-change", path.join(scriptDir, "append-change.cjs"), appendArgv);
    if (!appendResult.ok) abort("Pipeline aborted: append-change failed.");

    const mergeResult = runStep("merge-session", path.join(scriptDir, "merge-session.cjs"), [
      root,
      "--session", sessionId,
      "--no-check",
    ]);
    if (!mergeResult.ok) abort("Pipeline aborted: merge-session failed.");
  }

  const postCheckResult = runStep("check-memory (post)", path.join(scriptDir, "check-memory.cjs"), [root]);
  if (!postCheckResult.ok) abort("Pipeline aborted: post-check failed. Snapshot was restored.");
});

console.log(`safe-edit ${mode} pipeline completed successfully.`);
